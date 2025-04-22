import os
import logging
from pymilvus import connections, utility
from pymilvus.exceptions import MilvusException
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger(__name__)

class MilvusService:
    def __init__(self):
        # self._host = os.getenv("MILVUS_HOST", "localhost") # Default to localhost if not set
        self._host = "localhost" # Force connection via localhost
        self._port = os.getenv("MILVUS_PORT", "19530")
        self._alias = "default" # Default alias for Milvus connection

    def connect(self):
        try:
            logger.info(f"Attempting to connect to Milvus at {self._host}:{self._port}")
            connections.connect(
                alias=self._alias,
                host=self._host,
                port=self._port
            )
            # Check connection status
            if self.is_connected():
                logger.info(f"Successfully connected to Milvus ({self._alias}) at {self._host}:{self._port}")
            else:
                 logger.error(f"Milvus connection reported as not healthy after connect call.")
                 # Optionally raise an exception here if connection failure should halt startup
                 # raise ConnectionError("Failed to establish a healthy connection to Milvus")
        except MilvusException as e:
            logger.error(f"Milvus connection error: {e}", exc_info=True)
            # Handle connection failure (e.g., raise exception, set a flag)
            # Depending on requirements, you might want to prevent startup if Milvus connection fails
        except Exception as e:
            logger.error(f"An unexpected error occurred during Milvus connection: {e}", exc_info=True)

    def close(self):
        try:
            if self.is_connected():
                connections.disconnect(self._alias)
                logger.info(f"Disconnected from Milvus ({self._alias}).")
            else:
                 logger.info(f"Milvus ({self._alias}) already disconnected or connection was not established.")
        except MilvusException as e:
            logger.error(f"Error disconnecting from Milvus: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred during Milvus disconnection: {e}", exc_info=True)

    def is_connected(self) -> bool:
        """Checks if the connection to Milvus is established and healthy."""
        try:
            # Check connection state using a basic utility command
            # utility.get_server_version() or utility.get_connection_addr(self._alias) can work
            # Let's use a simple check if connection exists for the alias
            conn_addr = utility.get_connection_addr(self._alias)
            # get_connection_addr returns a dict like {'address': 'host:port'}, returns None if not connected
            # Adjust connection check logic if needed when forcing localhost
            # If the connection internally resolves to the container IP when connected from within Docker,
            # this check might need adjustment. However, for external connections, this should be okay.
            return conn_addr is not None and conn_addr.get('address') == f"{self._host}:{self._port}"
        except MilvusException as e:
            # Specific Milvus exceptions might indicate connection issues
            logger.warning(f"Milvus connection check failed with MilvusException: {e}")
            return False
        except Exception as e:
            # Other exceptions likely mean no connection
            logger.error(f"Unexpected error during Milvus connection check: {e}", exc_info=True)
            return False

# Create a singleton instance of the service
milvus_service = MilvusService() 