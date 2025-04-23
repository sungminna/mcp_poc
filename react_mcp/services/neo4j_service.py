import os
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from dotenv import load_dotenv
import logging
from typing import List, Any, Dict, Tuple
import asyncio
from functools import partial
from openai import AsyncOpenAI, OpenAIError
from datetime import datetime
import json # Added import for JSON serialization
import redis.asyncio as aioredis  # Added async Redis client import

# Import Milvus service - Remove unused fields if applicable
# Updated import to remove non-existent names
from .milvus_service import milvus_service, EMBEDDING_DIMENSION, OPENAI_EMBEDDING_MODEL
# ... potentially remove MILVUS_NEO4J_NODE_ID_FIELD, MILVUS_NEO4J_REFS_FIELD if not used elsewhere

load_dotenv()

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

aclient = AsyncOpenAI()

# Initialize Redis client singleton for embedding cache
_redis_client: aioredis.Redis | None = None

def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client

# --- Async Neo4j Helper Functions ---
async def _async_run_write_query(driver: AsyncDriver, query: str, params: Dict[str, Any] = None):
    """Runs a write query within a session and returns the result summary asynchronously."""
    try:
        async with driver.session(database="neo4j") as session:
            result = await session.run(query, params)
            summary = await result.consume()
            return summary
    except Exception as e:
        logger.error(f"Async write query failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

async def _async_fetch_single(driver: AsyncDriver, query: str, params: Dict[str, Any] = None):
    """Runs a query and fetches a single record asynchronously."""
    try:
        async with driver.session(database="neo4j") as session:
            result = await session.run(query, params)
            record = await result.single()
            return record
    except Exception as e:
        logger.error(f"Async fetch single failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

async def _async_fetch_list(driver: AsyncDriver, query: str, params: Dict[str, Any] = None):
    """Runs a query and fetches a list of records asynchronously."""
    try:
        async with driver.session(database="neo4j") as session:
            result = await session.run(query, params)
            records = [record async for record in result]
            return records
    except Exception as e:
        logger.error(f"Async fetch list failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

async def _async_create_node_get_id(driver: AsyncDriver, query: str, params: Dict[str, Any] = None) -> int | None:
    """Runs a query to create/merge a node and returns its internal Neo4j ID asynchronously."""
    try:
        async with driver.session(database="neo4j") as session:
            result = await session.run(query, params)
            record = await result.single()
            return record[0] if record else None
    except Exception as e:
        logger.error(f"Async create node get ID failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

async def _async_create_relationship_get_id(driver: AsyncDriver, query: str, params: Dict[str, Any] = None) -> int | None:
    """Runs a query to create/merge a relationship and returns its internal Neo4j ID asynchronously."""
    try:
        async with driver.session(database="neo4j") as session:
            result = await session.run(query, params)
            record = await result.single()
            return record[0] if record else None
    except Exception as e:
        logger.error(f"Async create relationship get ID failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

# --- Neo4jService Class --- 

class Neo4jService:
    _driver: AsyncDriver | None = None
    # Added asyncio Lock for Milvus check/insert logic
    _milvus_insert_lock = asyncio.Lock()

    async def connect(self):
        if self._driver is None:
            try:
                logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}")
                self._driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
                await self._driver.verify_connectivity()
                logger.info("Neo4j connection successful.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j or verify connectivity: {e}", exc_info=True)
                self._driver = None
                raise

    async def close(self):
        if self._driver is not None:
            await self._driver.close()
            logger.info("Neo4j connection closed.")
            self._driver = None

    def get_driver(self) -> AsyncDriver:
        if self._driver is None:
            raise ConnectionError("Neo4j driver is not initialized. Call connect() first.")
        return self._driver

    async def generate_embedding(self, text: str) -> list[float]:
        """Generates embedding for the given text using OpenAI API with Redis caching."""
        if not text:
            logger.warning("generate_embedding called with empty text.")
            return [0.0] * EMBEDDING_DIMENSION

        text_key = text.replace("\n", " ").strip()
        cache_key = f"kw_embedding:{text_key}"
        redis_client = get_redis_client()
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug(f"Embedding cache hit for text: '{text_key[:50]}...'")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis cache get error for key {cache_key}: {e}", exc_info=True)

        try:
            response = await aclient.embeddings.create(
                input=[text_key],
                model=OPENAI_EMBEDDING_MODEL
            )
            embedding = response.data[0].embedding
            try:
                await redis_client.set(cache_key, json.dumps(embedding), ex=86400)  # cache for 1 day
            except Exception as e:
                logger.error(f"Redis cache set error for key {cache_key}: {e}", exc_info=True)
            return embedding
        except OpenAIError as e:
            logger.error(f"OpenAI API error generating embedding for text '{text_key[:50]}...': {e}")
            return [0.0] * EMBEDDING_DIMENSION
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
            return [0.0] * EMBEDDING_DIMENSION

    async def create_indexes(self):
        """Creates necessary constraints (vector indexes are now in Milvus)."""
        driver = self.get_driver()
        
        constraint_queries = [
            "CREATE CONSTRAINT user_username IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
            "CREATE CONSTRAINT information_value IF NOT EXISTS FOR (i:Information) REQUIRE i.value IS UNIQUE", # Reverted to value only constraint
            # "CREATE CONSTRAINT information_key_value IF NOT EXISTS FOR (i:Information) REQUIRE (i.key, i.value) IS UNIQUE" # Removed composite constraint
        ]
        # Removed Neo4j vector index creation queries
        
        try:
            # Run both constraint creations
            tasks = [_async_run_write_query(driver, query) for query in constraint_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            for query, result in zip(constraint_queries, results):
                constraint_name = query.split(" ")[2] # Extract name for logging
                if isinstance(result, Exception):
                     logger.warning(f"Constraint '{constraint_name}' creation failed or thread execution error: {result}")
                else:
                     logger.info(f"Constraint '{constraint_name}' creation attempted (run in thread).")

            # Original logging kept for reference, can be removed if above is sufficient
            # await asyncio.to_thread(_sync_run_write_query, driver, constraint_query)
            # logger.info("Constraint 'user_username' creation attempted (run in thread).")
        except Exception as e:
            # This catch might be redundant now with gather handling exceptions, but kept for safety
            logger.warning(f"Error during constraint creation process: {e}")
            # Continue if constraint fails?

        logger.info("Neo4j index creation step skipped (vector indexes moved to Milvus).")

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
            record = await _async_fetch_single(driver, query, params={"username": username, "props": props})
            if record:
                logger.info(f"User node '{username}' created or updated in Neo4j (run in thread).")
                return record[0] # Return the node object/dict from the record
            else:
                logger.warning(f"User node '{username}' could not be created/updated.")
                return None
        except Exception as e:
            logger.error(f"Error adding user '{username}' via thread: {e}", exc_info=True)
            return None

    async def save_personal_information(self, username: str, info_list: list[dict]):
        """Saves info to Neo4j, checks Milvus for existing text vectors, 
           saves new vectors to Milvus, and links Neo4j elements to Milvus IDs."""
        driver = self.get_driver()
        
        # 1. Check if user exists (remains the same)
        user_check_query = "MATCH (u:User {username: $username}) RETURN u.username"
        try:
            user_record = await _async_fetch_single(driver, user_check_query, params={"username": username})
            if not user_record:
                logger.error(f"User '{username}' not found in Neo4j. Cannot save info.")
                return False
        except Exception as e:
            logger.error(f"Error checking user '{username}': {e}", exc_info=True)
            return False

        # --- Refactored Processing Logic --- 
        neo4j_update_tasks = [] # Tasks to update Neo4j with Milvus IDs later
        milvus_insertion_data = [] # Data for new vectors to insert into Milvus
        embedding_cache = {} # Cache generated embeddings for reuse within this request
        milvus_id_cache = {} # Cache Milvus IDs found for existing texts
        processed_neo4j_ids = {} # Track Neo4j IDs created: {('node', text): id, ('rel', text): id}

        # --- Pass 1: Check Milvus, generate embeddings for new texts, create Neo4j elements --- 
        logger.debug(f"Starting Pass 1 for user '{username}': Check Milvus, Embed new, Create Neo4j")
        
        # Collect all unique texts that might need checking/embedding first
        texts_to_potentially_process = set()
        valid_info_list = []
        for info in info_list:
            key_str = info.get("key")
            value = info.get("value")
            relationship_verb = info.get("relationship")
            if not all([key_str, value, relationship_verb]):
                logger.warning(f"Skipping incomplete item for user '{username}': {info}")
                continue
            valid_info_list.append(info) # Keep track of valid items
            texts_to_potentially_process.add(value) # Node text
            texts_to_potentially_process.add(relationship_verb) # Relationship text
            texts_to_potentially_process.add(key_str) # Key/Category text

        # Determine which texts actually need embedding (check Milvus within lock)
        embeddings_needed = {} # {text: type}
        async with self._milvus_insert_lock: # Acquire lock
            logger.debug(f"Acquired lock to check Milvus for {len(texts_to_potentially_process)} potential texts.")
            # Check local cache first (in case texts repeat within the batch)
            texts_to_check_in_milvus = {t for t in texts_to_potentially_process if t not in milvus_id_cache}
            
            if texts_to_check_in_milvus:
                # Batch check would be ideal, doing sequential for now
                check_tasks = {text: milvus_service.get_vector_id_by_text(text) for text in texts_to_check_in_milvus}
                results = await asyncio.gather(*check_tasks.values(), return_exceptions=True)
                
                for i, text in enumerate(check_tasks.keys()):
                    result = results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Error checking Milvus for text '{text}': {result}")
                        # Decide how to handle - skip text? Assume not present?
                        # Assuming not present for now to allow potential insertion
                        embeddings_needed[text] = None # Mark as needing embedding, type resolved later
                    elif result is not None:
                        milvus_id_cache[text] = result # Cache existing ID
                        logger.debug(f"Milvus check found existing ID for text: '{text}'")
                    else:
                        # Text is new according to Milvus
                        embeddings_needed[text] = None # Mark as needing embedding, type resolved later
                        logger.debug(f"Milvus check found no vector for text: '{text}'")
            logger.debug(f"Releasing lock. {len(embeddings_needed)} texts marked for potential embedding.")

        # --- Generate Embeddings (Outside Lock) --- 
        if embeddings_needed:
            embedding_tasks = {}
            for text in embeddings_needed.keys():
                if text not in embedding_cache: # Avoid re-generating
                    embedding_tasks[text] = self.generate_embedding(text)
            
            if embedding_tasks:
                logger.debug(f"Generating embeddings for {len(embedding_tasks)} texts.")
                embedding_results = await asyncio.gather(*embedding_tasks.values(), return_exceptions=True)
                for i, text in enumerate(embedding_tasks.keys()):
                    result = embedding_results[i]
                    if isinstance(result, Exception) or not any(result):
                        logger.error(f"Failed to generate embedding for text '{text}': {result}. Will not add to Milvus.")
                        # Remove from embeddings_needed if failed?
                        if text in embeddings_needed:
                             del embeddings_needed[text] 
                    else:
                        embedding_cache[text] = result
                        logger.debug(f"Successfully generated embedding for text: '{text}'")
            else:
                logger.debug("No new embeddings needed (all texts needing embedding were already cached).")
        else:
            logger.debug("No texts needed embedding generation.")

        # --- Process each valid info item: Create Neo4j & Prepare Milvus Insert Data --- 
        for info in valid_info_list:
            key_str = info.get("key")
            value = info.get("value")
            relationship_verb = info.get("relationship")
            lifetime = info.get("lifetime", "permanent")
            node_text = value
            rel_text = relationship_verb
            
            # --- Create/Merge Neo4j Elements --- 
            neo4j_node_id = None
            neo4j_rel_id = None
            neo4j_key_node_id = None
            try:
                # Step 2a: Node
                create_node_query = (
                    "MERGE (i:Information {key: $key, value: $value}) "
                    "ON CREATE SET i.createdAt = timestamp(), i.children = [] "
                    "ON MATCH SET i.updatedAt = timestamp() "
                    "RETURN elementId(i)"
                )
                node_params = {"key": key_str, "value": value}
                neo4j_node_id = await _async_create_node_get_id(driver, create_node_query, node_params)
                if neo4j_node_id is None: raise ValueError(f"Failed to create/get node ID for {value}")

                # Step 2b: Relationship
                create_rel_query = (
                    "MATCH (u:User {username: $username}) "
                    "MATCH (i:Information) WHERE elementId(i) = $node_id " 
                    "MERGE (u)-[r:RELATES_TO {value: $relationship_verb}]->(i) "
                    "ON CREATE SET r.lifetime = $lifetime, r.createdAt = timestamp() "
                    "ON MATCH SET r.lifetime = $lifetime, r.updatedAt = timestamp() " 
                    "RETURN elementId(r)"
                )
                rel_params = {"username": username, "node_id": neo4j_node_id, "relationship_verb": relationship_verb, "lifetime": lifetime}
                neo4j_rel_id = await _async_create_relationship_get_id(driver, create_rel_query, rel_params)
                if neo4j_rel_id is None: logger.error(f"Failed to create/get relationship ID for {rel_text} -> {node_text}") # Log error but continue

                # Step 2c: Key Node & Hierarchy
                key_node_key_prop = "Category"
                create_key_node_query = (
                    "MERGE (k:Information {key: $key_node_key, value: $key_value}) "
                    "ON CREATE SET k.createdAt = timestamp(), k.children = [] "
                    "ON MATCH SET k.updatedAt = timestamp() "
                    "RETURN elementId(k)"
                )
                key_node_params = {"key_node_key": key_node_key_prop, "key_value": key_str}
                neo4j_key_node_id = await _async_create_node_get_id(driver, create_key_node_query, key_node_params)
                if neo4j_key_node_id is None: raise ValueError(f"Failed to create/get key node ID for {key_str}")
                
                create_hierarchy_rel_query = (
                    "MATCH (i:Information) WHERE elementId(i) = $node_id "
                    "MATCH (k:Information) WHERE elementId(k) = $key_node_id "
                    "MERGE (i)-[h:HAS_CATEGORY]->(k) "
                    "ON CREATE SET h.createdAt = timestamp() "
                    "ON MATCH SET h.updatedAt = timestamp()"
                )
                hierarchy_rel_params = {"node_id": neo4j_node_id, "key_node_id": neo4j_key_node_id}
                await _async_run_write_query(driver, create_hierarchy_rel_query, hierarchy_rel_params)

            except Exception as e:
                logger.error(f"Error during Neo4j element creation/linking for info key='{key_str}', value='{value}': {e}. Skipping Milvus prep for this item.", exc_info=True)
                continue # Skip Milvus prep for this item if Neo4j failed

            # --- Prepare Milvus Insertion Data (Add if new & embedding succeeded) ---
            if node_text in embeddings_needed and node_text in embedding_cache:
                 milvus_insertion_data.append({
                     "embedding": embedding_cache[node_text],
                     "element_type": "Node",
                     "original_text": node_text.lower()
                 })
                 del embeddings_needed[node_text] # Mark as processed for insertion
                 
            if rel_text in embeddings_needed and rel_text in embedding_cache and neo4j_rel_id is not None: # Check rel was created
                 milvus_insertion_data.append({
                     "embedding": embedding_cache[rel_text],
                     "element_type": "Relationship",
                     "original_text": rel_text.lower()
                 })
                 del embeddings_needed[rel_text] # Mark as processed
                 
            if key_str in embeddings_needed and key_str in embedding_cache:
                 milvus_insertion_data.append({
                     "embedding": embedding_cache[key_str],
                     "element_type": "Node", 
                     "original_text": key_str.lower()
                 })
                 del embeddings_needed[key_str] # Mark as processed

        # --- Pass 2: Batch Insert New Vectors into Milvus, filtering out duplicates ---
        if milvus_insertion_data:
            # Deduplicate insertion data by original_text
            deduped_items = {item["original_text"].lower(): item for item in milvus_insertion_data}.values()
            logger.debug(f"Attempting to insert {len(deduped_items)} unique new vectors into Milvus.")
            # Filter out items that already exist in Milvus by exact text match
            filtered_items = []
            for item in deduped_items:
                text = item["original_text"].lower()
                item["original_text"] = text
                try:
                    existing_id = await milvus_service.get_vector_id_by_text(text)
                    if existing_id is not None:
                        logger.debug(f"Skipping insertion for '{text}' because it already exists in Milvus.")
                        continue
                except Exception as e:
                    logger.error(f"Error checking Milvus for existing text '{text}': {e}", exc_info=True)
                filtered_items.append(item)
            if filtered_items:
                logger.debug(f"{len(filtered_items)} vectors remain after filtering existing duplicates.")
                try:
                    inserted_ids = await milvus_service.insert_vectors(filtered_items)
                    # Logging success/failure based on count
                    if inserted_ids and len(inserted_ids) == len(filtered_items):
                        logger.info(f"Successfully inserted {len(inserted_ids)} new vectors into Milvus.")
                    else:
                        logger.error(f"Milvus insertion failed or returned incorrect ID count. Expected {len(filtered_items)}, got {len(inserted_ids) if inserted_ids else 0}.")
                except Exception as e:
                    logger.error(f"Failed during Milvus batch insertion: {e}", exc_info=True)
            else:
                logger.debug("No new vectors to insert after filtering existing duplicates.")
        else:
            logger.debug("Pass 2 Skipped: No new vectors needed insertion.")

        logger.info(f"Finished saving personal information for user '{username}'.")
        return True # Indicate overall process completion

    async def find_similar_information(self, username: str, keywords: List[str], top_k: int = 3, similarity_threshold: float = 0.75) -> List[str]:
        """Finds info via Milvus, queries Neo4j for user nodes, expands via children, returns context."""
        if not keywords:
            return []

        driver = self.get_driver()
        logger.info(f"Finding similar info for '{username}' via keywords: {keywords}, using 1-hop children expansion.")

        # 1. Generate embeddings for keywords (remains same)
        embedding_tasks = [self.generate_embedding(kw) for kw in keywords]
        keyword_embeddings = await asyncio.gather(*embedding_tasks)
        valid_embeddings = [emb for emb in keyword_embeddings if any(emb)]
        if not valid_embeddings:
            logger.warning(f"No valid keyword embeddings for '{username}'. Keywords: {keywords}")
            return []

        # 2. Search Milvus for relevant text concepts (remains same)
        relevant_texts = []
        try:
            milvus_results = await milvus_service.search_vectors(
                valid_embeddings, top_k=top_k * 3, # Fetch more concepts initially
                similarity_threshold=similarity_threshold
            )
            if not milvus_results:
                logger.info(f"No similar text concepts found in Milvus.")
                return []
            relevant_texts = list(set([hit['original_text'] for hit in milvus_results if hit.get('original_text')]))
            logger.info(f"Milvus found {len(relevant_texts)} relevant text concepts: {relevant_texts}")
        except Exception as e:
            logger.error(f"Error searching Milvus concepts: {e}", exc_info=True)
            return []

        # 3. Neo4j Query 1: Find initial nodes and their children based on Milvus texts
        child_keywords = set() 
        initial_neo4j_data = []
        if relevant_texts:
            try:
                # Query to find initial nodes connected to the user matching Milvus texts
                # AND retrieve their children property
                query1 = """
                MATCH (u:User {username: $username})-[r:RELATES_TO]->(i:Information)
                WHERE r.value IN $texts OR i.value IN $texts
                RETURN 
                    elementId(r) AS rel_id, 
                    r.value AS relationship, 
                    i.key AS node_key, 
                    i.value AS node_value, 
                    i.createdAt AS created_at, 
                    r.lifetime AS lifetime,
                    i.children AS children // Get children list
                ORDER BY i.createdAt DESC
                LIMIT $limit
                """
                query1_results = await _async_fetch_list(driver, query1,
                    params={"username": username, "texts": relevant_texts, "limit": top_k * 5} # Fetch more initially
                )
                
                if query1_results:
                    initial_neo4j_data.extend(query1_results)
                    # Extract child keywords from results
                    for record in query1_results:
                        children_list = record.get("children")
                        if children_list and isinstance(children_list, list):
                            for child in children_list:
                                if isinstance(child, str) and child.strip():
                                    child_keywords.add(child.strip())
                    logger.info(f"Query 1 found {len(initial_neo4j_data)} initial nodes/rels. Extracted children: {child_keywords}")
                else:
                    logger.info(f"Query 1 found no initial nodes/rels matching Milvus texts for user '{username}'.")

            except Exception as e:
                logger.error(f"Error in Neo4j Query 1 for user '{username}': {e}", exc_info=True)
                # Continue without initial results if query fails?

        # 4. Neo4j Query 2: Find nodes based on child keywords
        child_neo4j_data = []
        if child_keywords:
            try:
                # Query to find nodes connected to the user matching child keywords
                query2 = """
                MATCH (u:User {username: $username})-[r:RELATES_TO]->(i:Information)
                WHERE i.value IN $child_keywords // Match node value against children
                RETURN 
                    elementId(r) AS rel_id, 
                    r.value AS relationship, 
                    i.key AS node_key, 
                    i.value AS node_value, 
                    i.createdAt AS created_at, 
                    r.lifetime AS lifetime
                    // No need to return i.children here
                ORDER BY i.createdAt DESC
                LIMIT $limit
                """
                query2_results = await _async_fetch_list(driver, query2,
                    params={"username": username, "child_keywords": list(child_keywords), "limit": top_k * 3}
                )
                if query2_results:
                    child_neo4j_data.extend(query2_results)
                    logger.info(f"Query 2 found {len(child_neo4j_data)} nodes/rels matching child keywords.")
                else:
                     logger.info(f"Query 2 found no nodes/rels matching child keywords for user '{username}'.")
            except Exception as e:
                logger.error(f"Error in Neo4j Query 2 (children) for user '{username}': {e}", exc_info=True)

        # 5. Neo4j Query 3: Find edges that contain similar information
        edge_neo4j_data = []
        try:
            # Query to find edges that have properties similar to the keywords or relevant texts
            query3 = """
            MATCH (u:User {username: $username})-[r:RELATES_TO]->(i:Information)
            WHERE any(text IN $texts WHERE r.value CONTAINS text) 
               OR any(text IN $texts WHERE toLower(r.value) CONTAINS toLower(text))
            RETURN 
                elementId(r) AS rel_id, 
                r.value AS relationship, 
                i.key AS node_key, 
                i.value AS node_value, 
                i.createdAt AS created_at, 
                r.lifetime AS lifetime
            ORDER BY i.createdAt DESC
            LIMIT $limit
            """
            query3_results = await _async_fetch_list(driver, query3,
                params={
                    "username": username, 
                    "texts": relevant_texts + keywords,  # Search in both relevant texts and original keywords
                    "limit": top_k * 3
                }
            )
            if query3_results:
                edge_neo4j_data.extend(query3_results)
                logger.info(f"Query 3 found {len(edge_neo4j_data)} edges/relationships with similar information.")
            else:
                logger.info(f"Query 3 found no edges with similar information for user '{username}'.")
        except Exception as e:
            logger.error(f"Error in Neo4j Query 3 (edges) for user '{username}': {e}", exc_info=True)

        # 6. Combine, Deduplicate, and Format Results
        final_results_map = {}
        # Process initial results first
        for record in initial_neo4j_data:
            rel_id = record["rel_id"]
            if rel_id not in final_results_map: # Use relationship ID as unique key for now
                final_results_map[rel_id] = dict(record)
        # Add results from child keyword search
        for record in child_neo4j_data:
             rel_id = record["rel_id"]
             if rel_id not in final_results_map:
                 final_results_map[rel_id] = dict(record)
        # Add results from edge similarity search
        for record in edge_neo4j_data:
             rel_id = record["rel_id"]
             if rel_id not in final_results_map:
                 final_results_map[rel_id] = dict(record)

        # Sort combined results (optional, using node creation time as primary sort key from queries)
        # sorted_results = sorted(final_results_map.values(), key=lambda x: x.get("created_at", 0), reverse=True)
        # Or just use the map directly as order might be good enough from individual queries
        sorted_results = list(final_results_map.values())

        output_sentences = []
        seen_tuples = set() # Deduplicate based on core info
        for record_dict in sorted_results:
            if len(output_sentences) >= top_k:
                break

            rel_verb = record_dict.get('relationship', '').lower()
            node_val = record_dict.get('node_value', '').lower()
            node_key = record_dict.get('node_key', '').lower()
            info_tuple = (rel_verb, node_val, node_key)

            if not all([rel_verb, node_val]) or info_tuple in seen_tuples:
                continue 
            seen_tuples.add(info_tuple)

            created_at = record_dict.get("created_at")
            if isinstance(created_at, (int, float)):
                try: created_iso = datetime.fromtimestamp(created_at / 1000).isoformat()
                except Exception: created_iso = str(created_at)
            else: created_iso = str(created_at)
            lifetime = record_dict.get("lifetime", "")

            sentence = (
                f"You {rel_verb} {node_val}, "
                f"recorded around {created_iso}, lifetime {lifetime}."
            )
            sentence = sentence[0].upper() + sentence[1:]
            output_sentences.append(sentence)

        logger.info(f"Formatted {len(output_sentences)} unique context sentences after keywords, children, and edge expansion for user '{username}'.")
        return output_sentences

# Global instance
neo4j_service = Neo4jService()
