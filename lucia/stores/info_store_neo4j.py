from typing import List, Dict, Any
from .info_store import InfoStore
from neo4j import AsyncGraphDatabase
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

class Neo4jInfoStore(InfoStore):
    def __init__(self, database: str = "neo4j"):
        """
        Initialize the Neo4j driver using environment variables.
        NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD를 사용합니다.
        """
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        # Ensure Information.value uniqueness constraint at startup
        asyncio.create_task(self._ensure_value_uniqueness_constraint())

    async def _ensure_value_uniqueness_constraint(self):
        """Ensure Information.value has a unique constraint in Neo4j"""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """CREATE CONSTRAINT IF NOT EXISTS FOR (i:Information) REQUIRE i.value IS UNIQUE"""
            )

    async def close(self):
        """Close the Neo4j driver connection."""
        await self.driver.close()

    async def save_personal_information(self, username: str, info_list: List[Dict[str, Any]]):
        """
        Save personal information as relationships in the graph.
        Each info dict must contain: key, value, relationship, lifetime.
        """
        async with self.driver.session(database=self.database) as session:
            # Ensure user node exists
            await session.run(
                "MERGE (u:User {username: $username})",
                {"username": username}
            )
            for info in info_list:
                # Support both dicts and objects with attributes (e.g., ExtractedInfo)
                key = getattr(info, "key", None)
                value = getattr(info, "value", None)
                rel = getattr(info, "relationship", None)
                lifetime = getattr(info, "lifetime", "permanent")
                await session.run(
                    """
                    MERGE (i:Information {value: $value})
                    // Update or set the key property on the Information node
                    SET i.key = $key
                    MERGE (u:User {username: $username})
                    MERGE (u)-[r:RELATES_TO {relationship: $rel}]->(i)
                    SET r.lifetime = $lifetime
                    """,
                    {
                        "username": username,
                        "key": key,
                        "value": value,
                        "rel": rel,
                        "lifetime": lifetime,
                    }
                )
                # Also create an Attribute node for the key and connect it to the Information node
                await session.run(
                    """
                    MERGE (k:Information {key: "Attribute", value: $key})
                    MERGE (i:Information {key: $key, value: $value})
                    MERGE (i)-[h:HAS_ATTRIBUTE {relationship: $rel}]->(k)
                    SET h.lifetome = $lifetime
                    """,
                    {
                        "key": key,
                        "value": value,
                        "rel": "HAS_ATTRIBUTE",
                        "lifetime": "permanent"
                    }
                )

    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[str]:
        """
        Retrieve related information values for the user's keywords.
        Matches Information nodes where key or value in keywords.
        Returns phrases like "relationship value".
        """
        if not keywords:
            return []
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (u:User {username: $username})-[r:RELATES_TO]->(i:Information)
                WHERE i.value IN $keywords OR i.key IN $keywords
                RETURN i.value AS value, r.relationship AS rel
                LIMIT $top_k
                """,
                {"username": username, "keywords": keywords, "top_k": top_k}
            )
            records = [rec async for rec in result]
            return [f"{rec['rel']} {rec['value']}" for rec in records] 