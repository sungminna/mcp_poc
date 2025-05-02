from typing import List, Dict, Any
from .info_store import InfoStore
from neo4j import AsyncGraphDatabase
import asyncio
import logging
from ..config import settings
from ..extractors.models import ExtractedInfo
from datetime import datetime

logger = logging.getLogger(__name__)

class Neo4jInfoStore(InfoStore):
    def __init__(self, database: str = None):
        """
        Initialize the Neo4j driver using centralized settings.
        """
        uri = settings.neo4j_uri
        user = settings.neo4j_user
        password = settings.neo4j_password
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database or settings.neo4j_database
        # track whether uniqueness constraint has been ensured
        self._constraint_ensured: bool = False

    async def _ensure_value_uniqueness_constraint(self):
        """Ensure Information.value has a unique constraint in Neo4j"""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """CREATE CONSTRAINT IF NOT EXISTS FOR (i:Information) REQUIRE i.value IS UNIQUE"""
            )

    async def close(self):
        """Close the Neo4j driver connection."""
        await self.driver.close()

    async def save_personal_information(self, username: str, info_list: List[ExtractedInfo]):
        """
        Save personal information as relationships in the graph.
        Each info dict must contain: key, value, relationship, lifetime.
        """
        # ensure constraint only once before saving
        if not self._constraint_ensured:
            await self._ensure_value_uniqueness_constraint()
            self._constraint_ensured = True
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
                    SET r.lifetime = $lifetime, r.inserted_at = datetime()
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
                    SET h.lifetome = $lifetime, h.inserted_at = datetime()
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
    ) -> List[ExtractedInfo]:
        """
        Retrieve related information values for the user's keywords.
        Matches Information nodes where key or value in keywords.
        Returns full records: username, key, value, relationship, lifetime.
        """
        if not keywords:
            return []
        async with self.driver.session(database=self.database) as session:
            # Check for user existence
            user_count_res = await session.run(
                "MATCH (u:User {username: $username}) RETURN count(u) AS cnt",
                {"username": username}
            )
            user_record = await user_count_res.single()
            if not user_record or user_record["cnt"] == 0:
                logger.warning(f"Neo4jInfoStore: User '{username}' not found in Neo4j")
                return []
            # Proceed with relationship search
            result = await session.run(
                """
                MATCH (u:User {username: $username})-[r:RELATES_TO]->(i:Information)
                WHERE i.value IN $keywords OR i.key IN $keywords OR r.relationship IN $keywords
                RETURN u.username AS username, i.key AS key, i.value AS value, r.relationship AS relationship, r.lifetime AS lifetime, r.inserted_at AS inserted_at
                LIMIT $top_k
                """,
                {"username": username, "keywords": keywords, "top_k": top_k}
            )
            records = [rec async for rec in result]
            # Map each record to ExtractedInfo model including inserted_at
            return [
                ExtractedInfo(
                    username=rec["username"],
                    key=rec["key"],
                    value=rec["value"],
                    relationship=rec["relationship"],
                    lifetime=rec["lifetime"],
                    inserted_at=rec.get("inserted_at")
                )
                for rec in records
            ] 