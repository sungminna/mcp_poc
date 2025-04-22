import os
from neo4j import GraphDatabase, Driver, Session, Transaction
from dotenv import load_dotenv
import logging
from typing import List, Any, Dict, Tuple
import asyncio
from functools import partial
from openai import AsyncOpenAI, OpenAIError
from datetime import datetime
import json # Added import for JSON serialization

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
            # Convert Neo4j Node/Relationship to dictionary if needed, or return the object
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

def _sync_create_node_get_id(driver: Driver, query: str, params: Dict[str, Any] = None) -> int | None:
    """Runs a query to create/merge a node and returns its internal Neo4j ID."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            record = result.single()
            # Return elementId (string) or node id (int)? Neo4j internal IDs are ints.
            # elementId() returns string. Let's stick to internal int ID for now for consistency
            # with potential relationship IDs, though elementId is preferred for external refs.
            # If issues arise, switch to elementId() and adjust Milvus schema if needed.
            return record[0] if record else None 
    except Exception as e:
        logger.error(f"Sync create node get ID failed: {query} | Params: {params} | Error: {e}", exc_info=True)
        raise

def _sync_create_relationship_get_id(driver: Driver, query: str, params: Dict[str, Any] = None) -> int | None:
    """Runs a query to create/merge a relationship and returns its internal Neo4j ID."""
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            record = result.single()
            # Use internal ID (int) for consistency for now.
            return record[0] if record else None
    except Exception as e:
        logger.error(f"Sync create relationship get ID failed: {query} | Params: {params} | Error: {e}", exc_info=True)
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
            logger.warning("generate_embedding called with empty text.")
            return [0.0] * EMBEDDING_DIMENSION
        
        text = text.replace("\n", " ")
        try:
            response = await aclient.embeddings.create(
                input=[text],
                model=OPENAI_EMBEDDING_MODEL
            )
            embedding = response.data[0].embedding
            return embedding
        except OpenAIError as e:
            logger.error(f"OpenAI API error generating embedding for text '{text[:50]}...': {e}")
            return [0.0] * EMBEDDING_DIMENSION # Fallback
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
            return [0.0] * EMBEDDING_DIMENSION # Fallback

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
            tasks = [asyncio.to_thread(_sync_run_write_query, driver, query) for query in constraint_queries]
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
            record = await asyncio.to_thread(
                _sync_fetch_single, driver, query, params={"username": username, "props": props}
            )
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
            user_record = await asyncio.to_thread(
                _sync_fetch_single, driver, user_check_query, params={"username": username}
            )
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
        for info in info_list:
            key_str = info.get("key") # Get the original key string
            value = info.get("value")
            relationship_verb = info.get("relationship")
            lifetime = info.get("lifetime", "permanent")

            if not all([key_str, value, relationship_verb]):
                logger.warning(f"Skipping incomplete item for user '{username}': {info}")
                continue

            node_text = value # Use only the value for node embedding text
            rel_text = relationship_verb

            # --- Handle Node Text (Value) ---
            node_milvus_id = milvus_id_cache.get(node_text)
            if node_milvus_id is None: # Not cached yet
                try:
                    node_milvus_id = await milvus_service.get_vector_id_by_text(node_text)
                    if node_milvus_id is not None:
                        milvus_id_cache[node_text] = node_milvus_id # Cache existing ID
                        logger.info(f"[SAVE_INFO] Found existing Milvus ID {node_milvus_id} for NODE text: '{node_text}'")
                    else:
                        logger.info(f"[SAVE_INFO] No existing Milvus vector for NODE text '{node_text}'. Will generate/insert.")
                        # Text not in Milvus, generate embedding if not cached
                        if node_text not in embedding_cache:
                            node_embedding = await self.generate_embedding(node_text)
                            if not any(node_embedding):
                                logger.error(f"Failed to generate embedding for node '{node_text}'. Skipping item.")
                                continue
                            embedding_cache[node_text] = node_embedding
                        # else: embedding already cached
                except Exception as e:
                    logger.error(f"Error checking/embedding node text '{node_text}': {e}. Skipping item.")
                    continue
            
            # --- Handle Relationship Text ---
            rel_milvus_id = milvus_id_cache.get(rel_text)
            if rel_milvus_id is None: # Not cached yet
                try:
                    rel_milvus_id = await milvus_service.get_vector_id_by_text(rel_text)
                    if rel_milvus_id is not None:
                        milvus_id_cache[rel_text] = rel_milvus_id # Cache existing ID
                        logger.info(f"[SAVE_INFO] Found existing Milvus ID {rel_milvus_id} for REL text: '{rel_text}'")
                    else:
                        logger.info(f"[SAVE_INFO] No existing Milvus vector for REL text '{rel_text}'. Will generate/insert.")
                        # Text not in Milvus, generate embedding if not cached
                        if rel_text not in embedding_cache:
                            rel_embedding = await self.generate_embedding(rel_text)
                            if not any(rel_embedding):
                                logger.error(f"Failed to generate embedding for rel '{rel_text}'. Skipping item.")
                                continue
                            embedding_cache[rel_text] = rel_embedding
                        # else: embedding already cached
                except Exception as e:
                    logger.error(f"Error checking/embedding rel text '{rel_text}': {e}. Skipping item.")
                    continue

            # --- Handle Key Text (for Hierarchy/Category Node) ---
            key_milvus_id = milvus_id_cache.get(key_str)
            key_node_neo4j_id_needed_for_milvus = False # Flag to add key embedding later
            if key_milvus_id is None: # Key text not cached yet
                try:
                    key_milvus_id = await milvus_service.get_vector_id_by_text(key_str)
                    if key_milvus_id is not None:
                        milvus_id_cache[key_str] = key_milvus_id # Cache existing ID
                        logger.info(f"[SAVE_INFO] Found existing Milvus ID {key_milvus_id} for KEY text: '{key_str}'")
                    else:
                        logger.info(f"[SAVE_INFO] No existing Milvus vector for KEY text '{key_str}'. Will generate/insert if Neo4j node created.")
                        # Key text not in Milvus, generate embedding if not cached
                        if key_str not in embedding_cache:
                            key_embedding = await self.generate_embedding(key_str)
                            if not any(key_embedding):
                                logger.warning(f"Failed to generate embedding for key '{key_str}'. Will not add to Milvus.")
                            else:
                                embedding_cache[key_str] = key_embedding
                                key_node_neo4j_id_needed_for_milvus = True # Mark for Milvus insert later
                        elif key_str in embedding_cache: # Already cached (e.g. duplicate key in batch)
                             key_node_neo4j_id_needed_for_milvus = True # Mark for Milvus insert later
                        # else: embedding failed, do nothing for Milvus

                except Exception as e:
                    logger.error(f"Error checking/embedding key text '{key_str}': {e}. Skipping Milvus add for key.")
            
            # --- Create/Merge Neo4j Node and Relationships (Get IDs) --- 
            try:
                # --- Step 2a: Create/Merge Main Information Node and Get ID --- 
                create_node_query = (
                    "MERGE (i:Information {key: $key, value: $value}) " # Use original key parameter
                    "ON CREATE SET i.createdAt = timestamp(), i.children = [] " # Initialize children on create
                    "ON MATCH SET i.updatedAt = timestamp() " # Update timestamp on match too
                    "RETURN id(i)" # Use internal id()
                )
                node_params = {"key": key_str, "value": value} # Pass the original string key
                neo4j_node_id = await asyncio.to_thread(_sync_create_node_get_id, driver, create_node_query, node_params)
                if neo4j_node_id is None:
                    logger.error(f"Failed to create/get Neo4j node ID for '{value}' (key: '{key_str}'). Skipping item.")
                    continue
                processed_neo4j_ids[('node', node_text)] = neo4j_node_id
                
                # --- Step 2b: Create/Merge User Relationship --- 
                create_rel_query = (
                    "MATCH (u:User {username: $username}) "
                    "MATCH (i:Information) WHERE id(i) = $node_id " # Match main node by ID
                    "MERGE (u)-[r:RELATES_TO {value: $relationship_verb}]->(i) "
                    "ON CREATE SET r.lifetime = $lifetime, r.createdAt = timestamp() "
                    "ON MATCH SET r.lifetime = $lifetime, r.updatedAt = timestamp() " # Update timestamp on match too
                    "RETURN id(r)" # Use internal id()
                )
                rel_params = {
                    "username": username,
                    "node_id": neo4j_node_id, # Use ID instead of key/value match
                    "relationship_verb": relationship_verb,
                    "lifetime": lifetime
                }
                neo4j_rel_id = await asyncio.to_thread(_sync_create_relationship_get_id, driver, create_rel_query, rel_params)
                if neo4j_rel_id is None:
                     logger.error(f"Failed to create/get Neo4j user relationship ID for '{rel_text}' -> '{node_text}'. Skipping relationship part.")
                     # Continue processing node and hierarchy if needed
                else:
                     processed_neo4j_ids[('rel', rel_text)] = neo4j_rel_id

                # --- Step 2c: Create/Merge Key Node (Category) and Hierarchy Link ---
                key_node_key_prop = "Category" # Define the 'key' property for the category node itself
                create_key_node_query = (
                    "MERGE (k:Information {key: $key_node_key, value: $key_value}) "
                    "ON CREATE SET k.createdAt = timestamp(), k.children = [] " # Initialize children here too
                    "ON MATCH SET k.updatedAt = timestamp() " # Update timestamp on match too
                    "RETURN id(k)"
                )
                key_node_params = {"key_node_key": key_node_key_prop, "key_value": key_str}
                neo4j_key_node_id = await asyncio.to_thread(_sync_create_node_get_id, driver, create_key_node_query, key_node_params)

                if neo4j_key_node_id is None:
                    logger.error(f"Failed to create/get Neo4j key node ID for category '{key_str}'. Skipping hierarchy link and Milvus key add.")
                else:
                    processed_neo4j_ids[('key_node', key_str)] = neo4j_key_node_id # Track for Milvus update if needed

                    # Create hierarchy link
                    create_hierarchy_rel_query = (
                        "MATCH (i:Information) WHERE id(i) = $node_id "
                        "MATCH (k:Information) WHERE id(k) = $key_node_id "
                        "MERGE (i)-[h:HAS_CATEGORY]->(k) "
                        "ON CREATE SET h.createdAt = timestamp() "
                        "ON MATCH SET h.updatedAt = timestamp()"
                    )
                    hierarchy_rel_params = {"node_id": neo4j_node_id, "key_node_id": neo4j_key_node_id}
                    await asyncio.to_thread(_sync_run_write_query, driver, create_hierarchy_rel_query, hierarchy_rel_params)
                    logger.debug(f"Ensured HAS_CATEGORY link between node {neo4j_node_id} ('{value}') and key node {neo4j_key_node_id} ('{key_str}')")

                    # --- Prepare Milvus Insertion Data (Add key node if needed) ---
                    if key_node_neo4j_id_needed_for_milvus and key_str in embedding_cache:
                        milvus_insertion_data.append({
                            "embedding": embedding_cache[key_str],
                            # No longer adding neo4j_id
                            "element_type": "Node", # Changed type from CategoryNode to Node
                            "original_text": key_str,
                            "text_key": key_str # Keep for mapping insert results if needed, though maybe less critical now
                        })
                        key_node_neo4j_id_needed_for_milvus = False # Reset flag

                # --- Prepare Milvus Insertion Data (Add main node and relationship if new) ---
                if node_milvus_id is None and node_text in embedding_cache: # Needs insertion
                    milvus_insertion_data.append({
                        "embedding": embedding_cache[node_text],
                         # No longer adding neo4j_id
                        "element_type": "Node",
                        "original_text": node_text,
                        "text_key": node_text # Add key to map result IDs back
                    })

                if rel_milvus_id is None and neo4j_rel_id is not None and rel_text in embedding_cache: # Needs insertion (and rel was created)
                     # Create JSON string for relationship references - REMOVED
                     # refs_payload = json.dumps([{"user": username, "rel_id": neo4j_rel_id}])
                     milvus_insertion_data.append({
                        "embedding": embedding_cache[rel_text],
                         # No longer adding neo4j_refs
                        "element_type": "Relationship", # Storing the verb itself
                        "original_text": rel_text,
                        "text_key": rel_text # Add key to map result IDs back
                    })

            except Exception as e:
                logger.error(f"Error during Neo4j element creation/linking for info key='{key_str}', value='{value}': {e}. Skipping item.", exc_info=True)
                continue
        
        logger.debug(f"Pass 1 Complete. Found {len(milvus_id_cache)} existing vectors. Prepared {len(milvus_insertion_data)} new vectors for insertion.")

        # --- Pass 2: Batch Insert New Vectors into Milvus --- 
        newly_inserted_milvus_ids = {}
        if milvus_insertion_data:
            logger.debug(f"Starting Pass 2: Inserting {len(milvus_insertion_data)} new vectors into Milvus.")
            try:
                # Prepare payload without Neo4j IDs/Refs, only core fields
                insert_payload = [
                    { 
                        "embedding": item["embedding"], 
                        "element_type": item["element_type"],
                        "original_text": item["original_text"]
                    }
                     for item in milvus_insertion_data
                ]
                inserted_ids = await milvus_service.insert_vectors(insert_payload)
                
                # Mapping back IDs might be less useful now, but kept for potential debugging
                if inserted_ids and len(inserted_ids) == len(milvus_insertion_data):
                    logger.info(f"Successfully inserted {len(inserted_ids)} new vectors into Milvus.")
                    for i, item in enumerate(milvus_insertion_data):
                        text_key = item['text_key']
                        newly_inserted_milvus_ids[text_key] = inserted_ids[i]
                        milvus_id_cache[text_key] = inserted_ids[i] 
                else:
                     logger.error(f"Milvus insertion failed or returned incorrect ID count. Expected {len(milvus_insertion_data)}, got {len(inserted_ids) if inserted_ids else 0}.")
            except Exception as e:
                logger.error(f"Failed during Milvus batch insertion: {e}", exc_info=True)
        else:
            logger.debug("Pass 2 Skipped: No new vectors to insert.")

        # --- Pass 3: Update Neo4j elements with respective Milvus IDs --- REMOVED
        logger.debug("Pass 3 Skipped: No longer updating Neo4j elements with Milvus IDs.")
        # update_tasks = []
        # # Iterate through the successfully processed Neo4j elements
        # for (elem_type, text_key), neo4j_id in processed_neo4j_ids.items():
        #     final_milvus_id = milvus_id_cache.get(text_key) # Get ID from cache (existing or new)
        #     if final_milvus_id is not None:
        #         update_tasks.append(asyncio.to_thread(_sync_set_milvus_id, driver, neo4j_id, final_milvus_id))
        #     else:
        #          # This case should ideally not happen if logic above is correct, but log if it does
        #          logger.warning(f"Could not find a Milvus ID (existing or new) for {elem_type} text '{text_key}' (Neo4j ID: {neo4j_id}). Skipping update.")
        
        # if update_tasks:
        #     try:
        #         update_results = await asyncio.gather(*update_tasks, return_exceptions=True)
        #         failed_updates = [res for res in update_results if isinstance(res, Exception)]
        #         if failed_updates:
        #             logger.error(f"{len(failed_updates)} errors occurred while setting Milvus IDs in Neo4j. Example: {failed_updates[0]}")
        #         else:
        #             logger.info(f"Successfully initiated updates for {len(update_tasks)} Neo4j elements with Milvus IDs.")
        #     except Exception as e:
        #          logger.error(f"Unexpected error during batch updating Neo4j with Milvus IDs: {e}", exc_info=True)
        # else:
        #      logger.debug("Pass 3 Skipped: No Neo4j elements to update.")

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
                    id(r) AS rel_id, 
                    r.value AS relationship, 
                    i.key AS node_key, 
                    i.value AS node_value, 
                    i.createdAt AS created_at, 
                    r.lifetime AS lifetime,
                    i.children AS children // Get children list
                ORDER BY i.createdAt DESC
                LIMIT $limit
                """
                query1_results = await asyncio.to_thread(
                    _sync_fetch_list, driver, query1,
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
                    id(r) AS rel_id, 
                    r.value AS relationship, 
                    i.key AS node_key, 
                    i.value AS node_value, 
                    i.createdAt AS created_at, 
                    r.lifetime AS lifetime
                    // No need to return i.children here
                ORDER BY i.createdAt DESC
                LIMIT $limit
                """
                query2_results = await asyncio.to_thread(
                    _sync_fetch_list, driver, query2,
                    params={"username": username, "child_keywords": list(child_keywords), "limit": top_k * 3}
                )
                if query2_results:
                    child_neo4j_data.extend(query2_results)
                    logger.info(f"Query 2 found {len(child_neo4j_data)} nodes/rels matching child keywords.")
                else:
                     logger.info(f"Query 2 found no nodes/rels matching child keywords for user '{username}'.")
            except Exception as e:
                logger.error(f"Error in Neo4j Query 2 (children) for user '{username}': {e}", exc_info=True)

        # 5. Combine, Deduplicate, and Format Results
        final_results_map = {}
        # Process initial results first
        for record in initial_neo4j_data:
            rel_id = record["rel_id"]
            if rel_id not in final_results_map: # Use relationship ID as unique key for now
                final_results_map[rel_id] = dict(record)
        # Add results from child keyword search, potentially overwriting if rel_id collided (unlikely but possible)
        for record in child_neo4j_data:
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
            node_val = record_dict.get('node_value', '')
            node_key = record_dict.get('node_key', '')
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

        logger.info(f"Formatted {len(output_sentences)} unique context sentences after children expansion for user '{username}'.")
        return output_sentences

# Global instance
neo4j_service = Neo4jService()
