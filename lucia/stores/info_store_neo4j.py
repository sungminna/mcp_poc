"""
Neo4jInfoStore module.

Implements the InfoStore interface using Neo4j for graph-based storage
and retrieval of user personal information as nodes and relationships.
"""
from typing import List, Dict, Any
from .info_store import InfoStore
from neo4j import AsyncGraphDatabase
import asyncio
import logging
from ..config import settings
from ..extractors.models import ExtractedInfoDBList, ExtractedInfoDB
from datetime import datetime
from neo4j.time import DateTime as Neo4jDateTime

logger = logging.getLogger(__name__)

class Neo4jInfoStore(InfoStore):
    _instance = None
    _initialized = False

    def __new__(cls, database: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, database: str = None):
        if type(self)._initialized:
            return
        type(self)._initialized = True
        """
        Initialize the Neo4j driver and select the target database.

        Args:
            database (str, optional): Database name override; defaults to configured setting.
        """
        uri = settings.neo4j_uri
        user = settings.neo4j_user
        password = settings.neo4j_password
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.database = database or settings.neo4j_database
        # track whether uniqueness constraint has been ensured
        self._constraint_ensured: bool = False

    async def _ensure_value_uniqueness_constraint(self):
        """Ensure a uniqueness constraint on Information.value node property."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """CREATE CONSTRAINT IF NOT EXISTS FOR (i:Information) REQUIRE i.value IS UNIQUE"""
            )

    async def close(self):
        """Close the Neo4j driver connection gracefully."""
        await self.driver.close()

    async def save_personal_information(self, username: str, info_list: ExtractedInfoDBList):
        """
        Persist personal information entries as graph relationships in Neo4j.

        Args:
            username (str): Unique identifier for the user node.
            info_list (ExtractedInfoDBList): List of user info entries to save.
        """
        # Apply uniqueness constraint once per instance
        if not self._constraint_ensured:
            await self._ensure_value_uniqueness_constraint()
            self._constraint_ensured = True
        async with self.driver.session(database=self.database) as session:
            # Ensure user node exists
            await session.run(
                "MERGE (u:User {username: $username})",
                {"username": username}
            )
            if info_list:
                # Batch save all personal info using UNWIND to reduce network round trips
                infos = [
                    {
                        "key": getattr(info, "key", None),
                        "value": getattr(info, "value", None),
                        "relationship": getattr(info, "relationship", None),
                        "lifetime": getattr(info, "lifetime", "permanent")
                    }
                    for info in info_list
                ]
                await session.run(
                    """
                    UNWIND $infos AS info
                    MERGE (u:User {username: $username})
                    MERGE (i:Information {value: info.value})
                    SET i.key = info.key
                    MERGE (u)-[r:RELATES_TO {relationship: info.relationship}]->(i)
                    SET r.lifetime = info.lifetime, r.inserted_at = datetime()
                    MERGE (k:Information {key: "Attribute", value: info.key})
                    MERGE (i)-[h:HAS_ATTRIBUTE {relationship: "HAS_ATTRIBUTE"}]->(k)
                    SET h.lifetime = "permanent", h.inserted_at = datetime()
                    """,
                    {"username": username, "infos": infos}
                )

    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[ExtractedInfoDB]:
        """
        Retrieve information relationships for a user matching given keywords.

        Args:
            username (str): User identifier to filter relationships.
            keywords (List[str]): Keywords matching node values, keys, or relationship types.
            top_k (int): Maximum number of results to return.
            similarity_threshold (float): Threshold parameter for compatibility (unused).

        Returns:
            List[ExtractedInfoDB]: List of matching info records with metadata.
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
            items: List[ExtractedInfoDB] = []
            for rec in records:
                ts = rec.get("inserted_at")
                if isinstance(ts, Neo4jDateTime):
                    inserted_str = ts.to_native().isoformat()
                else:
                    inserted_str = str(ts) if ts is not None else None
                items.append(ExtractedInfoDB(
                    username=rec.get("username"),
                    key=rec.get("key"),
                    value=rec.get("value"),
                    relationship=rec.get("relationship"),
                    lifetime=rec.get("lifetime"),
                    inserted_at=inserted_str
                ))
            return items 