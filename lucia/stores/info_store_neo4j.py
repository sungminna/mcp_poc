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

    async def save_personal_information(self, username: str, info_list: ExtractedInfoDBList):
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