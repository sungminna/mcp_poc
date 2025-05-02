from typing import List
from .info_store import InfoStore
import asyncio
import logging
from urllib.parse import urlparse
from datetime import datetime
import clickhouse_connect
from ..config import settings
from ..extractors.models import ExtractedInfo

logger = logging.getLogger(__name__)

class ClickHouseInfoStore(InfoStore):
    def __init__(self, database: str = None):
        """
        Initialize the ClickHouse client using centralized settings and ensure tables exist.
        """
        # Parse the ClickHouse URI for host, port, and scheme
        parsed = urlparse(settings.clickhouse_uri)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 8123
        secure = parsed.scheme == 'https'
        # Initialize the ClickHouse client
        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=database or settings.clickhouse_database,
            secure=secure,
        )
        # Ensure the users table exists
        self.client.command("""
            CREATE TABLE IF NOT EXISTS users (
                username String,
                created_at DateTime
            ) ENGINE = ReplacingMergeTree(created_at)
            ORDER BY (username)
        """ )
        # Ensure the personal_information table exists
        self.client.command("""
            CREATE TABLE IF NOT EXISTS personal_information (
                username String,
                key String,
                value String,
                relationship String,
                lifetime String,
                inserted_at DateTime
            ) ENGINE = MergeTree()
            ORDER BY (username, inserted_at)
        """ )

    async def save_personal_information(self, username: str, info_list: List[ExtractedInfo]):
        """
        Save personal information items for a user into ClickHouse.
        """
        if not info_list:
            return

        loop = asyncio.get_event_loop()
        # Insert user record (allows duplicates for simplicity)
        try:
            await loop.run_in_executor(
                None,
                self.client.insert,
                'users',
                ['username', 'created_at'],
                [(username, datetime.utcnow())]
            )
        except Exception as e:
            logger.debug(f"ClickHouseInfoStore: error inserting user: {e}")

        # Prepare batch records for personal information
        records = []
        for info in info_list:
            # info is ExtractedInfo
            key = info.key
            value = info.value
            rel = info.relationship
            lifetime = info.lifetime or "permanent"
            records.append((username, key, value, rel, lifetime, datetime.utcnow()))

        # Insert personal information records
        try:
            await loop.run_in_executor(
                None,
                self.client.insert,
                'personal_information',
                ['username', 'key', 'value', 'relationship', 'lifetime', 'inserted_at'],
                records
            )
        except Exception as e:
            logger.error(f"ClickHouseInfoStore: error inserting personal information: {e}")

    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> List[ExtractedInfo]:
        """
        Retrieve related information items for a user based on keywords.
        Returns full records as ExtractedInfo models.
        """
        if not keywords:
            return []

        loop = asyncio.get_event_loop()
        # Check for user existence
        try:
            count = await loop.run_in_executor(
                None,
                self.client.query_scalar,
                f"SELECT count() FROM users WHERE username = '{username}'"
            )
        except Exception as e:
            logger.error(f"ClickHouseInfoStore: error checking user existence: {e}")
            return []

        if not count:
            logger.warning(f"ClickHouseInfoStore: User '{username}' not found in ClickHouse")
            return []

        # Build SQL for keyword matching
        kw_list = ','.join(f"'{kw}'" for kw in keywords)
        query = f"""
            SELECT username, key, value, relationship, lifetime, inserted_at
            FROM personal_information
            WHERE username = '{username}'
              AND (value IN ({kw_list}) OR key IN ({kw_list}) OR relationship IN ({kw_list}))
            ORDER BY inserted_at DESC
            LIMIT {top_k}
        """

        # Execute query and fetch full records
        try:
            rows = await loop.run_in_executor(
                None,
                self.client.query,
                query
            )
        except Exception as e:
            logger.error(f"ClickHouseInfoStore: error querying similar information: {e}")
            return []

        # Map rows to ExtractedInfo models
        return [
            ExtractedInfo(username=u, key=k, value=v, relationship=rel, lifetime=lt, inserted_at=ins)
            for u, k, v, rel, lt, ins in rows
        ]
