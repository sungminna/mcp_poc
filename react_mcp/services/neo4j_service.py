import os
from neo4j import GraphDatabase, Driver, Session, Transaction
from dotenv import load_dotenv
import logging
from typing import List, Any, Dict
import asyncio
from functools import partial
from openai import AsyncOpenAI, OpenAIError
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# --- OpenAI Embedding Configuration ---
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

VECTOR_INDEX_NAME = "information_embeddings"
REL_VECTOR_INDEX_NAME = "relationship_embeddings" # Optional

aclient = AsyncOpenAI()

# --- Synchronous Neo4j Helper Functions (to be run in threads) ---

def _sync_run_write_query(driver: Driver, query: str, params: Dict[str, Any] = None):
    """Runs a write query within a session and returns the result summary."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            summary = result.consume() # Consume result to get summary
            return summary
    except Exception as e:
        logger.error(f"Sync write query failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise # Re-raise exception to be caught by asyncio.gather

def _sync_fetch_single(driver: Driver, query: str, params: Dict[str, Any] = None):
    """Runs a query and fetches a single record."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            record = result.single()
            return record
    except Exception as e:
        logger.error(f"Sync fetch single failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

def _sync_fetch_list(driver: Driver, query: str, params: Dict[str, Any] = None):
    """Runs a query and fetches a list of records."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            # Correct way to get all records as a list from sync Result object
            records = list(result) 
            return records
    except Exception as e:
        logger.error(f"Sync fetch list failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

# --- Neo4jService Class --- 

class Neo4jService:
    _driver: Driver | None = None

    def connect(self):
        if self._driver is None:
            try:
                logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}")
                self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
                self._driver.verify_connectivity()
                logger.info("Neo4j connection successful.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j or verify connectivity: {e}", exc_info=True)
                self._driver = None
                raise

    def close(self):
        if self._driver is not None:
            self._driver.close()
            logger.info("Neo4j connection closed.")
            self._driver = None

    def get_driver(self) -> Driver:
        if self._driver is None:
            raise ConnectionError("Neo4j driver is not initialized. Call connect() first.")
        return self._driver

    async def generate_embedding(self, text: str) -> list[float]:
        """Generates embedding for the given text using OpenAI API."""
        if not text:
            # Return zero vector for empty input
            logger.warning("generate_embedding called with empty text.")
            return [0.0] * EMBEDDING_DIMENSION
        
        # OpenAI API recommendation: replace newlines with spaces
        text = text.replace("\n", " ")
        
        try:
            response = await aclient.embeddings.create(
                input=[text], # API expects a list of strings
                model=OPENAI_EMBEDDING_MODEL
            )
            embedding = response.data[0].embedding
            # logger.debug(f"Generated OpenAI embedding for text: '{text[:50]}...'")
            return embedding
        except OpenAIError as e:
            logger.error(f"OpenAI API error generating embedding for text '{text[:50]}...': {e}")
            # Decide how to handle API errors - raise, return zero vector, etc.
            # Returning zero vector might hide issues but allows processing to continue.
            # raise  # Or re-raise a custom exception
            return [0.0] * EMBEDDING_DIMENSION # Fallback to zero vector
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
            return [0.0] * EMBEDDING_DIMENSION # Fallback

    async def create_indexes(self):
        """Creates necessary constraints and vector indexes using sync calls in threads."""
        driver = self.get_driver()
        
        constraint_query = "CREATE CONSTRAINT user_username IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE"
        index_query = f"""
            CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
            FOR (i:Information) ON (i.embedding)
            OPTIONS {{ indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSION},
                `vector.similarity_function`: 'cosine'
            }} }}
        """
        
        try:
            # Run constraint creation in a separate thread
            await asyncio.to_thread(_sync_run_write_query, driver, constraint_query)
            logger.info("Constraint 'user_username' creation attempted (run in thread).")
        except Exception as e:
            # Error is already logged in _sync_run_write_query
            logger.warning(f"Constraint creation failed or thread execution error: {e}")

        try:
            # Run index creation in a separate thread
            await asyncio.to_thread(_sync_run_write_query, driver, index_query)
            logger.info(f"Vector index '{VECTOR_INDEX_NAME}' creation attempted (run in thread).")
        except Exception as e:
            logger.error(f"Vector index creation failed or thread execution error: {e}")

        # Create relationship vector index
        rel_index_query = f"""
            CREATE VECTOR INDEX {REL_VECTOR_INDEX_NAME} IF NOT EXISTS
            FOR ()-[r:RELATES_TO]-() ON (r.embedding)
            OPTIONS {{ indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSION},
                `vector.similarity_function`: 'cosine'
            }} }}
        """
        try:
            await asyncio.to_thread(_sync_run_write_query, driver, rel_index_query)
            logger.info(f"Vector index '{REL_VECTOR_INDEX_NAME}' creation attempted (run in thread).")
        except Exception as e:
            logger.error(f"Relationship vector index creation failed: {e}")

    async def add_user(self, username: str, user_info: dict):
        """Creates or updates a User node using sync calls in threads."""
        driver = self.get_driver()
        query = (
            "MERGE (u:User {username: $username}) "
            "ON CREATE SET u += $props, u.createdAt = timestamp() "
            "ON MATCH SET u += $props, u.updatedAt = timestamp() "
            "RETURN u"
        )
        props = {"email": user_info.get("email")}
        props = {k: v for k, v in props.items() if v is not None}
        try:
            # Run the fetch single operation in a thread
            record = await asyncio.to_thread(
                _sync_fetch_single, driver, query, params={"username": username, "props": props}
            )
            if record:
                logger.info(f"User node '{username}' created or updated in Neo4j (run in thread).")
                return record[0] # Return the node from the record
            else:
                logger.warning(f"User node '{username}' could not be created/updated (query returned no records).")
                return None
        except Exception as e:
            logger.error(f"Error adding user '{username}' via thread: {e}", exc_info=True)
            return None

    async def save_personal_information(self, username: str, info_list: list[dict]):
        """Saves extracted personal information using sync calls in threads."""
        driver = self.get_driver()
        user_check_query = "MATCH (u:User {username: $username}) RETURN u.username"
        create_info_query = (
            "MATCH (u:User {username: $username}) "
            "MERGE (i:Information {key: $key, value: $value}) "
            "ON CREATE SET i.embedding = $embedding, i.createdAt = timestamp() "
            "ON MATCH SET i.embedding = $embedding, i.updatedAt = timestamp() "
            "MERGE (u)-[r:RELATES_TO {value: $relationship_verb}]->(i) "
            "ON CREATE SET r.lifetime = $lifetime, r.embedding = $rel_embedding, r.createdAt = timestamp() "
            "ON MATCH SET r.lifetime = $lifetime, r.embedding = $rel_embedding, r.updatedAt = timestamp() "
            # No RETURN needed for run_write_query if only summary is checked
        )

        try:
            # Verify user exists first in a thread
            user_record = await asyncio.to_thread(
                _sync_fetch_single, driver, user_check_query, params={"username": username}
            )
            if not user_record:
                logger.error(f"User '{username}' not found in Neo4j. Cannot save personal information.")
                return False
        except Exception as e:
            logger.error(f"Error checking user '{username}' existence via thread: {e}", exc_info=True)
            return False

        # --- Generate embeddings (remains async) --- 
        embedding_coroutines = []
        valid_info_list = []
        for info in info_list:
            key = info.get("key")
            value = info.get("value")
            relationship_verb = info.get("relationship")
            if not all([key, value, relationship_verb]):
                logger.warning(f"Skipping incomplete information item for user '{username}': {info}")
                continue
            valid_info_list.append(info)
            embedding_coroutines.append(self.generate_embedding(f"{key}: {value}"))
            embedding_coroutines.append(self.generate_embedding(relationship_verb))
        
        if not valid_info_list:
            return True # No valid items to save

        try:
            embeddings = await asyncio.gather(*embedding_coroutines)
        except Exception as e:
             logger.error(f"Error generating embeddings for user '{username}': {e}", exc_info=True)
             return False # Fail if embedding generation fails
        # --- End Embedding Generation ---

        # --- Prepare and run save tasks in threads --- 
        save_tasks = []
        embedding_idx = 0
        for info in valid_info_list:
            node_embedding = embeddings[embedding_idx]
            rel_embedding = embeddings[embedding_idx + 1]
            embedding_idx += 2

            if not any(node_embedding) or not any(rel_embedding):
                 logger.error(f"Failed to generate embeddings for info '{info.get("key")}=' '{info.get("value")}' for user '{username}'. Skipping save.")
                 continue # Skip if embedding failed for this item

            params = {
                "username": username,
                "key": info.get("key"),
                "value": info.get("value"),
                "embedding": node_embedding,
                "relationship_verb": info.get("relationship"),
                "rel_embedding": rel_embedding,
                "lifetime": info.get("lifetime", "permanent")
            }
            # Create a task to run the sync write query in a thread
            save_tasks.append(
                asyncio.to_thread(_sync_run_write_query, driver, create_info_query, params=params)
            )

        if not save_tasks:
             logger.info(f"No valid information items with successful embeddings to save for user '{username}'.")
             return True # Nothing to save

        success_count = 0
        try:
            # Run all save tasks concurrently in threads
            results = await asyncio.gather(*save_tasks, return_exceptions=True)
            
            # Check results for success/failure
            for i, result_or_exception in enumerate(results):
                info_item = valid_info_list[i]
                if isinstance(result_or_exception, Exception):
                    # Error already logged in helper
                    logger.error(f"Thread execution failed for save task '{info_item.get("key")}=' '{info_item.get("value")}': {result_or_exception}")
                elif result_or_exception: # Check if summary object was returned
                     # Check summary counters if needed (e.g., result_or_exception.counters)
                     # If no exception, assume success for now
                     success_count += 1
                     # logger.info(f"Successfully saved info '{info_item.get("key")}=' '{info_item.get("value")}' (thread)")
                else:
                     logger.warning(f"Save task for '{info_item.get("key")}=' '{info_item.get("value")}' returned None unexpectedly.")

        except Exception as e:
            logger.error(f"Unexpected error during batch saving via threads for user '{username}': {e}", exc_info=True)
        
        logger.info(f"Attempted to save {len(valid_info_list)} items for user '{username}' via threads. Succeeded: {success_count}")
        return success_count == len(valid_info_list)

    async def find_similar_information(self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75) -> List[str]:
        """Finds information related to keywords using sync calls in threads."""
        if not keywords:
            return []

        driver = self.get_driver()

        # First, check if the User node exists and has any relationships at all
        user_check_query = """
            MATCH (u:User {username: $username})
            OPTIONAL MATCH (u)-[r]->(i:Information)
            RETURN u.username AS username, count(r) AS rel_count
        """
        
        try:
            # Check if user has any information nodes connected
            user_record = await asyncio.to_thread(
                _sync_fetch_single, driver, user_check_query, params={"username": username}
            )
            
            if not user_record:
                logger.warning(f"User '{username}' not found in Neo4j database. Cannot search for similar information.")
                return []
                
            rel_count = user_record["rel_count"]
            if rel_count == 0:
                logger.info(f"User '{username}' has no personal information stored yet. Skipping vector search.")
                return []
                
            logger.info(f"User '{username}' has {rel_count} information relationships. Proceeding with search.")
        except Exception as e:
            logger.error(f"Error checking user and relationships for '{username}': {e}", exc_info=True)
            # Continue execution - attempt to search anyway
        
        # Generate embeddings (async)
        embedding_tasks = [self.generate_embedding(kw) for kw in keywords]
        keyword_embeddings = await asyncio.gather(*embedding_tasks)

        valid_embeddings = [emb for emb in keyword_embeddings if any(emb)]
        if not valid_embeddings:
            logger.warning(f"No valid keyword embeddings generated for user '{username}'. Keywords: {keywords}")
            return []

        query = f"""
            MATCH (u:User {{username: $username}})
            CALL db.index.vector.queryNodes('{VECTOR_INDEX_NAME}', $top_k, $embedding) YIELD node AS i, score
            WHERE score >= $similarity_threshold
            MATCH (u)-[r:RELATES_TO]->(i)
            WITH DISTINCT u.username AS username, r.value AS relationship, i.key AS key, i.value AS value, i.createdAt AS created_at, r.lifetime AS lifetime, score
            RETURN username, relationship, key, value, created_at, lifetime, score
            ORDER BY score DESC
            LIMIT $top_k
        """

        # Also search over relationships vector index
        rel_query = f"""
            MATCH (u:User {{username: $username}})
            CALL db.index.vector.queryRelationships('{REL_VECTOR_INDEX_NAME}', $top_k, $embedding) YIELD relationship AS r, score
            WHERE score >= $similarity_threshold
            MATCH (u)-[r]->(i:Information)
            WITH DISTINCT u.username AS username, r.value AS relationship, i.key AS key, i.value AS value, i.createdAt AS created_at, r.lifetime AS lifetime, score
            RETURN username, relationship, key, value, created_at, lifetime, score
            ORDER BY score DESC
            LIMIT $top_k
        """

        all_results_list = []
        search_tasks = []
        for embedding in valid_embeddings:
            params = {
                "username": username,
                "embedding": embedding,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
            # Node-based vector search
            search_tasks.append(
                asyncio.to_thread(_sync_fetch_list, driver, query, params=params)
            )
            # Relationship-based vector search
            search_tasks.append(
                asyncio.to_thread(_sync_fetch_list, driver, rel_query, params=params)
            )
        
        try:
            # Run all search tasks concurrently in threads
            task_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            for i, result_or_exception in enumerate(task_results):
                if isinstance(result_or_exception, Exception):
                    # Error logged in helper, but don't treat it as fatal
                    logger.warning(f"Thread execution failed for vector search {i}: {result_or_exception}")
                    continue
                elif result_or_exception is not None: # Check if list of records was returned
                    all_results_list.extend(result_or_exception)
                else:
                     logger.debug(f"Vector search task {i} returned None unexpectedly.")
        except Exception as e:
            logger.error(f"Unexpected error during batched vector search via threads for user '{username}': {e}", exc_info=True)
            # Continue to process any results we got

        # Process and format results (remains the same)
        processed_results = {}
        for record in all_results_list:
            rel_key = (record["relationship"], record["key"], record["value"])
            if rel_key not in processed_results or record["score"] > processed_results[rel_key]["score"]:
                processed_results[rel_key] = record

        sentences = []
        for record in processed_results.values():
            created_at = record.get("created_at")
            # convert timestamp in ms to ISO string
            if isinstance(created_at, (int, float)):
                try:
                    created_iso = datetime.fromtimestamp(created_at / 1000).isoformat()
                except Exception:
                    created_iso = str(created_at)
            else:
                created_iso = str(created_at)
            lifetime = record.get("lifetime", "")
            sentence = (
                f"You {record['relationship'].lower()} {record['value']} ({record['key']}), "
                f"recorded at {created_iso}, lifetime {lifetime}."
            )
            sentence = sentence[0].upper() + sentence[1:]
            sentences.append(sentence)

        return sentences[:top_k]

# Global instance
neo4j_service = Neo4jService()
