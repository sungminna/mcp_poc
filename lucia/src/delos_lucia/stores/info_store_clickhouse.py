"""
ClickHouseInfoStore module.

Implements the InfoStore interface for persisting user information in ClickHouse.
Supports saving personal info and retrieving records based on keyword queries.
"""
from typing import List
from .info_store import InfoStore
import asyncio
import logging
from urllib.parse import urlparse
from datetime import datetime
import clickhouse_connect
from ..config import settings
from ..extractors.models import ExtractedInfoDBList, ExtractedInfoDB

logger = logging.getLogger(__name__)

class ClickHouseInfoStore(InfoStore):
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
        Initialize the ClickHouse client and ensure required tables exist.

        Args:
            database (str, optional): ClickHouse database name (overrides default).
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

    async def save_personal_information(self, username: str, info_list: ExtractedInfoDBList):
        """
        Persist personal information records for a user.

        Args:
            username (str): Unique identifier of the user.
            info_list (ExtractedInfoDBList): Collection of ExtractedInfoDB entries.
        """
        if not info_list:
            return

        # loop = asyncio.get_event_loop() # No longer using run_in_executor for debugging
        now = datetime.utcnow()
        # Build batch records
        user_record = (username, now)
        info_records = [
            (username, info.key, info.value, info.relationship, info.lifetime or "permanent", now)
            for info in info_list
        ]

        # Perform insertions synchronously for debugging
        try:
            logger.debug(f"Attempting to insert user: {username}")
            # Correct order: table, data, column_names
            self.client.insert(
                'users',
                [user_record],
                column_names=['username', 'created_at']
            )
            logger.debug(f"Successfully inserted user: {username}")
        except Exception as e:
            # Log with traceback and stop if user insert fails
            logger.error(f"ClickHouseInfoStore: error inserting user: {e}", exc_info=True)
            return

        # Only proceed if user insert was successful
        try:
            logger.debug(f"Attempting to insert {len(info_records)} info records for user: {username}")
            # Correct order: table, data, column_names
            self.client.insert(
                'personal_information',
                info_records,
                column_names=['username', 'key', 'value', 'relationship', 'lifetime', 'inserted_at']
            )
            logger.debug(f"Successfully inserted {len(info_records)} info records for user: {username}")
        except Exception as e:
            # Log with traceback
            logger.error(f"ClickHouseInfoStore: error inserting personal information: {e}", exc_info=True)

        # loop.run_in_executor(None, _insert_batch) # Original async call commented out

    async def find_similar_information(
        self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75
    ) -> ExtractedInfoDBList:
        """
        Query ClickHouse for records matching user keywords.

        Args:
            username (str): User identifier to filter records.
            keywords (List[str]): Keywords to match against key, value, or relationship.
            top_k (int): Maximum number of records to return.
            similarity_threshold (float): Unused threshold parameter (for interface compatibility).

        Returns:
            ExtractedInfoDBList: List of matching info records, empty if none found.
        """
        if not keywords:
            return []

        loop = asyncio.get_event_loop()
        # Check for user existence
        try:
            count = await loop.run_in_executor(
                None,
                self.client.command,
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
            ExtractedInfoDB(
                username=u,
                key=k,
                value=v,
                relationship=rel,
                lifetime=lt,
                inserted_at=ins.isoformat()
            )
            for u, k, v, rel, lt, ins in rows.result_rows
        ]
