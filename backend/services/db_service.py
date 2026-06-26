import os
import copy
import json
import logging
import asyncio
import asyncpg
import uuid
from datetime import datetime
from typing import List, Any, Tuple, Dict, Optional
from dotenv import load_dotenv
from utils.db_queries import (
    normalized_funding_query,
    normalized_hiring_query,
    normalized_events_query,
    normalized_master_query,
    fetch_link_query,
    company_query,
    people_query
)
from utils.set_conversion import convert_sets
from utils.icp import icp, weights
from utils.locations import locations

load_dotenv()  # Never override env vars already set by Docker Compose / the OS


DB_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_PRIMARY_TARGETS = {"united kingdom", "ireland", "netherlands", "germany"}

_EASTERN_EU_WEDGE = {
    "albania", "bulgaria", "romania", "poland",
    "croatia", "czech republic", "hungary", "slovakia",
    "slovenia", "estonia", "latvia", "lithuania",
    "bosnia and herzegovina", "kosovo", "montenegro",
    "north macedonia", "serbia", "ukraine", "denmark",
    "norway", "finland", "sweeden"
}

_WESTERN_EU_REST = {
    c for c in locations.get("european countries")
    if c not in _PRIMARY_TARGETS and c not in _EASTERN_EU_WEDGE
}

_NORTH_AMERICA = locations.get("north american countries")

async def add_company_note(company_id: int, note_text: str) -> Dict[str, Any]:
    """Adds a new note for a company."""
    logger.info(f"Adding note for company ID {company_id}")
    query = """
    INSERT INTO company_notes (id, company_id, note)
    VALUES ($1, $2, $3)
    RETURNING id, company_id, note, created_at
    """
    note_id = str(uuid.uuid4())
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        result = await conn.fetchrow(query, note_id, company_id, note_text)
        await conn.close()
        if result:
            return dict(result)
        return {}
    except Exception as e:
        logger.error(f"Failed to add note: {str(e)}")
        if conn:
            await conn.close()
        return {}

async def delete_company_note(note_id: str) -> bool:
    """Deletes a note by its ID."""
    logger.info(f"Deleting note {note_id}")
    query = "DELETE FROM company_notes WHERE id = $1"
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.execute(query, note_id)
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to delete note {note_id}: {str(e)}")
        if conn:
            await conn.close()
        return False

async def initialize_db():
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        if conn:
            logger.info("Connection Made")
    except Exception as e:
        logger.error("Connection not made!")

#Fetches all companies from the database

async def fetch_companies_temporary() -> List[Dict[str, Any]]:
    logger.info("Fetch companies from DB temporary")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        company_query = """
        SELECT 
            c.*, 
            p.full_name, p.title, p.email, p.linkedin_url,
            i.top_matches, i.interpretation
        FROM 
            companies c 
        LEFT JOIN 
            people p ON c.apollo_id = p.organization_id
        LEFT JOIN
            icp_scores i ON c.id = i.company_id
        WHERE 
            c.name <> 'ICARUS Sports' 
        AND EXISTS (
            SELECT 1
            FROM emails_sent es
            JOIN people p2 ON es.recipient_id = p2.id
            WHERE p2.organization_id = c.apollo_id
        );
        
        """
        results = await conn.fetch(company_query)
        
        # 3. Close connection immediately after fetching data
        await conn.close()
        
        # 4. CONSOLIDATION LOGIC: Re-structure the flat 99 rows into 62 nested objects
        companies_map: Dict[str, Dict[str, Any]] = {}

        for record in results:
            # Convert asyncpg.Record to dict for easier manipulation
            record_dict = dict(record)
            company_apollo_id = record_dict.get("apollo_id")

            if company_apollo_id is None:
                # Skip records if the primary company ID is somehow missing
                continue

            # --- CONSOLIDATE COMPANY DATA ---
            if company_apollo_id not in companies_map:
                # A. First time seeing this company: Initialize the master object
                company_data = record_dict.copy()
                company_data["people"] = []

                # Also, add the companies alignment to our services.
                company_data["top_matches"] = record_dict.get('top_matches')
                company_data["interpretation"] = record_dict.get('interpretation')
                
                # Clean up the root object by removing the scattered people data
                del company_data["full_name"]
                del company_data["title"]
                del company_data["email"]
                del company_data["linkedin_url"]
                
                companies_map[company_apollo_id] = company_data
            
            # Get the reference to the master company object
            master_company = companies_map[company_apollo_id]

            # --- CONSOLIDATE PEOPLE DATA ---
            # The 'full_name' field is NULL if the LEFT JOIN found no matching person.
            if record_dict["full_name"]:
                person = {
                    "full_name": record_dict["full_name"],
                    "title": record_dict["title"],
                    "email": record_dict["email"],
                    "linkedin_url": record_dict["linkedin_url"]
                }
                if person not in master_company.get('people', []):
                    master_company["people"].append(person)

        # Convert the dictionary values (the 62 unique company objects) back to a list
        final_all_companies = list(companies_map.values())
        logger.info(f"Done fetching and consolidating {len(final_all_companies)} companies.")
        return final_all_companies

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []
    finally:
        if conn:
            # Ensure connection is closed even if an error occurs during fetch
            try:
                await conn.close()
            except Exception:
                pass # Ignore close errors


async def fetch_companies(auth0_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all companies and their associated people in a single query (Eager Loading)
    and correctly consolidates the denormalized join results into a nested structure.
    """
    """
    Fetch all companies with associated people and notes in a single, scalable query.
    Uses JSON aggregation in Postgres to return one row per company.
    """
    logger.info(f"Fetching companies from DB for user: {auth0_id}...")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)

        company_query = """
        SELECT 
            c.*,
            i.total_score AS user_icp_score,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'full_name', p.full_name,
                    'title', p.title,
                    'email', p.email,
                    'linkedin_url', p.linkedin_url
                )) FILTER (WHERE p.id IS NOT NULL), '[]'::json
            ) AS people,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'id', n.id,
                    'note', n.note,
                    'created_at', n.created_at
                )) FILTER (WHERE n.id IS NOT NULL), '[]'::json
            ) AS notes,
            i.top_matches,
            i.interpretation
        FROM companies c
        LEFT JOIN people p ON c.apollo_id = p.organization_id
        LEFT JOIN icp_scores i ON c.id = i.company_id AND (i.auth0_id = $1 OR $1 IS NULL)
        LEFT JOIN company_notes n ON c.id = n.company_id
        GROUP BY c.id, i.total_score, i.top_matches, i.interpretation;
        """

        results = await conn.fetch(company_query, auth0_id)

        # Convert asyncpg.Record -> dict for each company
        companies = []
        for r in results:
            d = dict(r)
            if d.get('user_icp_score') is not None:
                d['icp_score'] = d['user_icp_score']
            # Ensure JSON fields are parsed if they come back as strings
            for field in ['people', 'notes']:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except json.JSONDecodeError:
                        d[field] = []
            companies.append(d)

        logger.info(f"Done fetching and consolidating {len(companies)} companies.")
        return companies

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch companies: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []
    finally:
        if conn:
            try:
                await conn.close()
            except Exception as close_err:
                logger.debug("Failed to close DB connection: %s", close_err)
        
async def fetch_people_from_company(organization_id: str)->List[Dict[str, str]]:
    logger.info(f"Fetching people from org id {organization_id}...")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        people_query = "SELECT full_name, title, email, linkedin_url FROM people WHERE organization_id = $1"
        people_results = await conn.fetch(people_query, organization_id)
        logger.info(f"Done fetching people from org id {organization_id}")
        return [dict(record) for record in people_results]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching people from org {organization_id}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching people from org {organization_id}: {str(e)}")
        return []
    finally:
        if conn:
            await conn.close()


async def store_email(
        pool: asyncpg.Pool,
        recipient_id: int,
        company_id: int,
        subject: str,
        body: str,
        sequence_number: int
):
    logger.info("Storing email...")
    try:
        query_insert_email = """
            INSERT INTO emails_sent 
            (recipient_id, company_id, subject, body, sequence_number)
            VALUES ($1, $2, $3, $4, $5)
            """

        query_update_company = """
                UPDATE companies
                SET contacted_status = 'pending'
                WHERE id = $1
            """

        query_update_person = """
                UPDATE people
                SET contacted_status = 'pending',
                    last_contacted_at = NOW()
                WHERE id = $1
            """
        async with pool.acquire(timeout=10.0) as conn:
            async with conn.transaction():
                await conn.execute(query_insert_email, recipient_id, company_id, subject, body, sequence_number)
                await conn.execute(query_update_company, company_id)
                await conn.execute(query_update_person, recipient_id)
        logger.info("Done storing email")
    except Exception as e:
        logger.exception("Failed to store email: %r", str(e))

#Fetch people from database

async def fetch_people()->List[Dict[str, Any]]:
    logger.info("Fetching people from DB...")
    try:
        conn = await asyncpg.connect(dsn=DB_URL) 
        query = "SELECT * FROM people"
        results = await conn.fetch(query)
        await conn.close()
        json_serializable_results = [dict(record) for record in results]
        logger.info("Done fetching people from DB...")
        return json_serializable_results

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch people: {str(e)}")
        return []

    except Exception as e:
        logger.error(f"An unexpected error occured: {str(e)}")
        return []


async def fetch_uncontacted_people(pool: asyncpg.Pool)->List:
    logger.info("Fetching uncontacted people from DB...")
    query = "SELECT id, first_name, organization_id, email FROM people WHERE contacted_status = 'uncontacted' AND email IS NOT NULL AND email <> '' ORDER BY id LIMIT 10"

    try: 
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            uncontacted_people_organization_ids = [dict(result) for result in results]

        return uncontacted_people_organization_ids

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch uncontacted people", str(e))
        return []
    except Exception as e:
        logger.error(f"An unexpected error occured")
        return []

#Fetch company by ID
async def fetch_company_details(id: int, auth0_id: str) -> Dict[str, Any]:
    """
    Fetch a single company by ID with its associated people and notes,
    using JSON aggregation to return one row per company.
    """
    logger.info(f"Fetching company with ID: {id} for user: {auth0_id}")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)

        query = """
        SELECT 
            c.*,
            i.total_score AS user_icp_score,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'full_name', p.full_name,
                    'title', p.title,
                    'email', p.email,
                    'linkedin_url', p.linkedin_url
                )) FILTER (WHERE p.id IS NOT NULL), '[]'::json
            ) AS people,
            COALESCE(
                json_agg(DISTINCT jsonb_build_object(
                    'id', n.id,
                    'note', n.note,
                    'created_at', n.created_at
                )) FILTER (WHERE n.id IS NOT NULL), '[]'::json
            ) AS notes,
            i.top_matches,
            i.interpretation
        FROM companies c
        LEFT JOIN people p ON c.apollo_id = p.organization_id
        LEFT JOIN icp_scores i ON c.id = i.company_id AND (i.auth0_id = $2 OR $2 IS NULL)
        LEFT JOIN company_notes n ON c.id = n.company_id
        WHERE c.id = $1
        GROUP BY c.id, i.total_score, i.top_matches, i.interpretation;
        """

        result = await conn.fetchrow(query, id, auth0_id)

        await conn.close()

        if result:
            # Convert asyncpg.Record to dict
            d = dict(result)
            if d.get('user_icp_score') is not None:
                d['icp_score'] = d['user_icp_score']
            # Ensure JSON fields are parsed if they come back as strings
            for field in ['people', 'notes']:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except:
                        d[field] = []
            return d
        else:
            logger.warning(f"No company found with ID {id}")
            return {}

    except asyncpg.PostgresError as e:
        logger.error(f"Database error occurred: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch company details for company ID {id}: {str(e)}")
        return {}
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                pass

#Fetch company by apollo id

async def fetch_company_by_apollo_id(apollo_id: str)->Dict:
    logger.info(f"Fetching company with apollo ID {apollo_id}")
    query = "SELECT * FROM companies WHERE apollo_id = $1 LIMIT 1"

    try:
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, apollo_id)
                if results:
                    logger.info("Company found")
                    json_serializable_results = dict(results)
                    return json_serializable_results 
                else:
                    logger.error("No company found")
                    return {}
    except Exception as e:
        logger.error(f"Failed to find company via ID: {str(e)}")
        return {}

#Store company data to database
async def store_to_db(
        data_to_store: List[Tuple[Any]],
        query: str,
        company_or_people: str
    )->bool: #True = it worked. False = it failed
    
    logger.info(f"Storing {company_or_people} data...")
    
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        await conn.executemany(query, data_to_store)               
        await conn.close()

        logger.info(f"Completed storing {company_or_people} data")
        return True

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while storing {company_or_people} data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to store {company_or_people} data: {str(e)}")
        return False

#Check if company exists in db based on name

async def is_company_in_db(company_name: str)->bool:
    logger.info(f"Checking if {company_name} is in DB")
    query = f"SELECT 1 FROM companies WHERE LOWER(name) = LOWER($1) LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, company_name)

            if results:
                logger.warning(f"{company_name} found")
                return True
            else: 
                logger.info(f"{company_name} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {company_name} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {company_name} from DB: {str(e)}")

    return False

#Check if company exists in db based on ID

async def is_company_id_in_db(company_apollo_id: str)->bool:
    logger.info(f"Checking if {company_apollo_id} is in DB")
    query = f"SELECT 1 FROM companies WHERE apollo_id = $1 LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, company_apollo_id)

            if results:
                logger.warning(f"{company_apollo_id} found")
                return True
            else: 
                logger.info(f"{company_apollo_id} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {company_apollo_id} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {company_apollo_id} from DB: {str(e)}")

    return False

#Check if person exists in db based on apollo id

async def is_person_in_db(apollo_id: str)->bool:
    logger.info(f"Checking if {apollo_id} is in DB")
    query = f"SELECT 1 FROM people WHERE apollo_id = $1 LIMIT 1"

    try:
        #Create a connection pool to avoid creating repeated tcp connections
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            async with pool.acquire() as conn:
                results = await conn.fetchrow(query, apollo_id)

            if results:
                logger.warning(f"{apollo_id} found")
                return True
            else: 
                logger.info(f"{apollo_id} not found")
                return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching {apollo_id} from DB: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch {apollo_id} from DB: {str(e)}")

    return False

#Store normalized funding data in normalized_funding table
async def store_in_normalized_funding(funding_data_to_store: List[Any], pool: asyncpg.Pool)->bool:
    logger.info("Storing normalized funding data")
    query = normalized_funding_query

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, *funding_data_to_store)

        logger.info("Funding data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing funding data: {str(e)}")
        return False

#Store normalized hiring data in normalized_hiring table
async def store_in_normalized_hiring(hiring_data_to_store: List[Any], pool: asyncpg.Pool)->bool:
    logger.info("Storing normalized hiring data")
    query = normalized_hiring_query

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, *hiring_data_to_store)

        logger.info("Hiring data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing hiring data: {str(e)}")
        return False

#Store normalized events data in normalized_events table
async def store_in_normalized_events(events_data_to_store: List[Any], pool: asyncpg.Pool)->bool:
    logger.info("Storing normalized events data")
    query = normalized_events_query

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, *events_data_to_store)

        logger.info("Events data stored")
        return True

    except Exception as e: 
        logger.error(f"Error storing events data: {str(e)}")
        return False

#Store normalized data in normalized_master table and return ID
async def store_in_normalized_master(normalized_master_data_to_store: List[Any], pool: asyncpg.Pool)->int:
    logger.info("Storing normalized master data")
    query = normalized_master_query

    try:
        async with pool.acquire() as conn:
            master_id = await conn.fetchval(query, *normalized_master_data_to_store)

        logger.info("Normalization master data stored")
        return master_id

    except Exception as e: 
        logger.error(f"Error storing normalization master data: {str(e)}")
        return 0

#Check if data already exists in normalization table

async def is_data_in_db(pool: asyncpg.Pool, company_or_event_link: Optional[str] = None)->bool:

    logger.info(f"Checking if {company_or_event_link} exists in normalized_master table")
    query = f"SELECT 1 FROM normalized_master WHERE link = $1 LIMIT 1"

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query, company_or_event_link)
        
        if results:
            logger.warning(f"{company_or_event_link} exists in normalized_master")
            return True
        else: 
            logger.info(f"{company_or_event_link} not found.")
            return False

    except asyncpg.PostgresError as e:
        logger.error(f"Database error while checking if {company_or_event_link} is in normalization_master: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"Error while chekcing if {company_or_event_link} is in normalization_master: {str(e)}")
        return True

#Change person contacted_status from uncontacted to contacted
async def change_person_contacted_status(apollo_id: str, pool):
    logger.info(f"Changing {apollo_id}'s contacted status...")
    query = "UPDATE people SET contacted_status = 'contacted' WHERE apollo_id = $1 RETURNING organization_id"

    try:
        async with pool.acquire() as conn:
            organization_id = await conn.fetch(query, apollo_id)
            org_id_json_list = [dict(org_id) for org_id in organization_id]
            org_id = org_id_json_list[0].get("organization_id")

            #Change contacted_status for person's company
            await change_company_contacted_status(apollo_id=str(org_id), pool=pool)

            logger.info(f"Contacted_status update done for person {apollo_id}")
            return 
    except Exception as e:
        logger.info(f"Failed to update contacted_status: {str(e)}")
        return 

#Change company contacted_status from uncontacted to contacted
async def change_company_contacted_status(apollo_id: str, pool):
    logger.info(f"Changing company {apollo_id}'s contacted status...")
    query = "UPDATE companies SET contacted_status = 'contacted' WHERE apollo_id = $1"

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, apollo_id)
            logger.info(f"Contacted_status update done for company {apollo_id}")
            return 
    except Exception as e:
        logger.info(f"Failed to update contacted_status: {str(e)}")
        return 

async def check_master_normalization(pool: asyncpg.pool):
    try:
        async with pool.acquire() as conn:
            query = "SELECT * FROM normalized_master"
            results = await conn.fetch(query)
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"Failed to check master normalization: {str(e)}")
        return []

#Get company from normalization_hiring table and return hiring area
async def get_hiring_area(company_name: str, pool) -> str:
    logger.info(f"Get hiring area for {company_name}")

    try:
        query = """
        SELECT job_roles
        FROM normalized_hiring
        WHERE LOWER(company_name) = $1
        LIMIT 1
        """

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_name.lower())

            if not row:
                logger.warning(f"No hiring data found for {company_name}. Returning 'various areas'")
                return "various areas"

            job_roles = row["job_roles"]

            if not job_roles:
                return "various areas"

            return job_roles[0]

    except Exception as e:
        logger.exception(f"Couldn't get hiring area for {company_name}")
        return "various areas"

async def get_painpoints(company_name: str, pool, data_source: str) -> List[str]:
    """Retrieves pain points for a company from the specified data source table."""
    logger.info(f"Fetching painpoints for {company_name} from {data_source}")
    
    table = "normalized_hiring" if data_source == "hiring" else "normalized_funding"
    query = f"SELECT painpoints FROM {table} WHERE LOWER(company_name) = $1 LIMIT 1"
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_name.lower())
            if row and row["painpoints"]:
                # Painpoints are stored as List[str] in the database
                return row["painpoints"]
    except Exception as e:
        logger.error(f"Error fetching painpoints for {company_name}: {str(e)}")
    
    return []

    
#Get company funding details from normalized_funding

async def fetch_funding_details(pool: asyncpg.Pool, company_name: str)->Dict:
    logger.info(f"Fetching funding details for {company_name}")
    query = "SELECT funding_round, amount_raised, currency FROM normalized_funding WHERE LOWER(company_name) = $1"

    try:
        async with pool.acquire() as conn:
            response = await conn.fetch(query, company_name.lower())
            response_list = [dict(result) for result in response]

            if not response_list:
                logger.warning(f"No funding data found for {company_name}")
                return {}

            response_dict = response_list[0]
            logger.info("Funding data found")
            return response_dict
    except Exception as e:
        logger.error(f"Failed to fetch funding details for {company_name}: {str(e)}")
        return {}

#Get companies with no funding details
async def return_companies_with_no_funding_details(pool: asyncpg.Pool)->List:
    logger.info("Fetching companies with null funding details")
    query = "SELECT name FROM companies WHERE latest_funding_round IS NULL AND latest_funding_amount IS NULL AND latest_funding_currency IS NULL"
    companies = []

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            for each_dict in results_list:
                name = each_dict.get("name", "")
                companies.append(name)
        logger.info("Done fetching companies")
        return companies
    except Exception as e:
        logger.error(f"Failed fetching companies: {str(e)}")
        return []

#Get link for funding, hiring, events source

async def fetch_source_link(pool: asyncpg.Pool, company_name: str)->Dict:
    logger.info(f"Fetching link for {company_name}...")
    query = fetch_link_query

    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query, company_name.lower())
            result_list = [dict(result) for result in results]
            if not result_list:
                logger.warning(f"No source link found for {company_name}")
                return {}

            final_result = result_list[0]
            logger.info("Done fetching link")
            return final_result
    except Exception as e:
        logger.error(f"Failed to fetch link for {company_name}: {str(e)}")
        return {}

#Fetch events from db
async def fetch_events(pool: asyncpg.Pool)->List[Dict[str, str]]:
    logger.info("Fetching events from database")
    query = """
            SELECT m.id, m.source, m.link, e.event_summary
            FROM normalized_master m
            LEFT JOIN normalized_events e ON m.id = e.master_id
            WHERE m.type = 'event';
            """
    try: 
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            results_list = [dict(result) for result in results]
            if not results_list:
                logger.warning("No events found")
                return []
            
            logger.info("Events found")
            logger.info(results_list)
            return results_list
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        return []

#Fetch company keywords
async def fetch_keywords(pool):
    query = "SELECT keywords FROM companies"
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query)
            result_list = [dict(result) for result in results]
            logger.info(result_list)
            return result_list
    except Exception as e:
        logger.error(f"Failed to fetch keywords: {str(e)}")
        return []

#Select all unscored companies

async def company_is_unscored(pool, auth0_id: str)->List[Dict[str, int]]:
    logger.info(f"Fetching all unscored companies for user {auth0_id}...")
    
    if auth0_id:
        query = """
        SELECT c.id 
        FROM companies c 
        WHERE NOT EXISTS (
            SELECT 1 
            FROM icp_scores s 
            WHERE s.company_id = c.id AND s.auth0_id = $1
        )
        """
    else:
        query = "SELECT id FROM companies WHERE icp_score IS NULL"

    try:
        async with pool.acquire() as conn:
            if auth0_id:
                results = await conn.fetch(query, auth0_id)
            else:
                results = await conn.fetch(query)
            if results:
                results_list = [dict(result) for result in results]
                logger.info("Done fetching unscored companies")
                return results_list
            else:
                logger.warning("No unscored companies found")
                return []

    except Exception as e:
        logger.error(f"Failed to fetch unscored companies: {str(e)}")
        return []


#Store icp score in icp_scores table
async def store_icp_score(pool, company_id, age_score, employee_count_score,
                        funding_stage_score, keyword_score, contactability_score,
                        geography_score, industry_score, total_score, category_breakdown,
                        top_matches, interpretation, auth0_id):
    category_breakdown = convert_sets(category_breakdown)
    category_breakdown_json = json.dumps(category_breakdown, indent=2)
    top_matches_json = json.dumps(top_matches, indent=2)
    logger.info(f"Storing ICP scores for company_id {company_id}...")
    
    query = """
    INSERT INTO icp_scores (
        company_id, age_score, employee_count_score, funding_stage_score, keyword_score,
        contactability_score, geography_score, industry_score, total_score, category_breakdown,
        top_matches, interpretation, auth0_id
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
    )
    ON CONFLICT (company_id)
    DO UPDATE SET
        age_score = EXCLUDED.age_score,
        employee_count_score = EXCLUDED.employee_count_score,
        funding_stage_score = EXCLUDED.funding_stage_score,
        keyword_score = EXCLUDED.keyword_score,
        contactability_score = EXCLUDED.contactability_score,
        geography_score = EXCLUDED.geography_score,
        industry_score = EXCLUDED.industry_score,
        total_score = EXCLUDED.total_score,
        category_breakdown = EXCLUDED.category_breakdown,
        top_matches = EXCLUDED.top_matches,
        interpretation = EXCLUDED.interpretation,
        auth0_id = EXCLUDED.auth0_id
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(query, company_id, age_score, employee_count_score,
                            funding_stage_score, keyword_score, contactability_score,
                            geography_score, industry_score, total_score,
                            category_breakdown_json, top_matches_json, interpretation, auth0_id)
        logger.info("ICP score stored for company_id %s", company_id)
    except asyncpg.PostgresError as e:
        logger.error(f"Database error storing ICP score for company_id {company_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to store ICP score for company_id {company_id}: {str(e)}")
    return

#Store icp score in icp_score column in companies table. Changes status to mcp if score >= 70

async def update_company_icp_score(pool, company_id: int, total_score: float):
    logger.info(f"Updating icp_score for company_id {company_id} to {total_score}")

    # Update both icp_score and status (conditionally)
    query = """
        UPDATE companies
        SET icp_score = CAST($1 AS numeric(4,1)),
            status = CASE
                        WHEN $1 > 69 THEN 'mql'
                        ELSE status
                     END
        WHERE id = $2
    """

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, float(total_score), company_id)
        logger.info("Company icp_score and status updated for company_id %s", company_id)
    except asyncpg.PostgresError as e:
        logger.error(f"Database error updating ICP score for company_id {company_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update ICP score for company_id {company_id}: {str(e)}")


async def fetch_people_by_ids(pool, ids: List[int]):
    if not ids:
        return []

    logger.info("Fetching people by ids...")
    query = "SELECT id, first_name, organization_id, email FROM people WHERE id = ANY($1::int[])"
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(query, ids)
        return [dict(row) for row in results]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching people by ids: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch people by ids: {str(e)}")
        return []


async def fetch_emails_sent(pool, company_id):
    logger.info("Fetching emails sent...")
    query = """
        SELECT
            e.subject, e.body, e.status, e.sent_at, 
            p.first_name,
            p.last_name
        FROM emails_sent e
        JOIN people p
            ON p.id = e.recipient_id
        WHERE e.company_id = $1; 
    """
    try:
        async with pool.acquire() as conn:
            emails = await conn.fetch(query, company_id)
        return [dict(email) for email in emails]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching sent emails for company {company_id}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch sent emails for company {company_id}: {str(e)}")
        return []

async def fetch_eligible_people(pool: asyncpg.Pool, organization_ids: Optional[List[str]] = None, limit: Optional[int] = None)->List:
    if organization_ids == []:
        return []

    query = """
        SELECT 
            p.*
        FROM 
            people p
        INNER JOIN
            companies c ON p.organization_id = c.apollo_id
        WHERE
            p.subscribed = TRUE
        AND p.has_replied = FALSE
        AND p.times_contacted < 4
        AND (
            p.times_contacted = 0
            OR p.last_contacted_at <= now() - interval '7 days'
        )
    """
    
    params: List[Any] = []
    param_idx = 1
    if organization_ids:
        query += f" AND p.organization_id = ANY(${param_idx})"
        params.append(organization_ids)
        param_idx += 1
        
    query += " ORDER BY c.icp_score DESC NULLS LAST"

    if limit is not None:
        query += f" LIMIT ${param_idx}"
        params.append(limit)

    query += ";"
    
    try:
        async with pool.acquire() as conn:
            people = await conn.fetch(query, *params)
            return [dict(person) for person in people]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch uncontacted people: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []

async def get_user_by_token(pool: asyncpg.Pool, token: str) -> Dict:
    """
    Fetch user details by unsubscribe token.
    Returns user dict or empty dict if not found.
    """
    logger.info(f"Fetching user by unsubscribe token...")
    query = """
        SELECT id, first_name, email, subscribed, unsubscribe_token
        FROM people
        WHERE unsubscribe_token = $1
        LIMIT 1
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(query, token)
            
            if result:
                logger.info("User found by token")
                return dict(result)
            else:
                logger.warning("No user found with provided token")
                return {}
                
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while fetching user by token: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error while fetching user by token: {str(e)}")
        return {}

async def unsubscribe_user(pool: asyncpg.Pool, token: str) -> bool:
    """
    Unsubscribe user by token. Returns True if successful, False otherwise.
    """
    logger.info(f"Attempting to unsubscribe user with token...")
    
    query = """
        UPDATE people
        SET subscribed = FALSE,
            unsubscribed_at = NOW()
        WHERE unsubscribe_token = $1
        AND subscribed = TRUE
        RETURNING id, email
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow(query, token)
            
            if result:
                logger.info(f"Successfully unsubscribed user: {result['email']} (ID: {result['id']})")
                return True
            else:
                logger.warning("No user found with provided token or user already unsubscribed")
                return False
                
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while unsubscribing user: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while unsubscribing user: {str(e)}")
        return False

async def mark_lead_replied(company_id: int, is_replied: bool) -> bool:
    """Updates the contacted_status of a company to 'replied' or its previous state."""
    logger.info(f"Marking company {company_id} replied: {is_replied}")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        if is_replied:
            query = "UPDATE companies SET contacted_status = 'replied', updated_at = NOW() WHERE id = $1"
        else:
            # Fallback to 'engaged' if unmarking replied, or whoever the highest status person says.
            # For simplicity, we'll set it to 'engaged' if it was replied.
            query = "UPDATE companies SET contacted_status = 'engaged', updated_at = NOW() WHERE id = $1"
        
        await conn.execute(query, company_id)
        
        # Also update the people in that company
        # We find the organization_id first
        org_id_query = "SELECT apollo_id FROM companies WHERE id = $1"
        org_id = await conn.fetchval(org_id_query, company_id)
        if org_id:
            if is_replied:
                await conn.execute("UPDATE people SET contacted_status = 'replied', updated_at = NOW() WHERE organization_id = $1", org_id)
            else:
                await conn.execute("UPDATE people SET contacted_status = 'engaged', updated_at = NOW() WHERE organization_id = $1", org_id)

        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to mark lead replied: {str(e)}")
        if conn: await conn.close()
        return False

async def mark_lead_positive(company_id: int, is_positive: bool) -> bool:
    """Updates the positive_reply flag for a company. If positive is true, also marks as replied."""
    logger.info(f"Marking company {company_id} positive: {is_positive}")
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
        if is_positive:
            query = "UPDATE companies SET positive_reply = $1, contacted_status = 'replied', updated_at = NOW() WHERE id = $2"
        else:
            query = "UPDATE companies SET positive_reply = $1, updated_at = NOW() WHERE id = $2"
        
        await conn.execute(query, is_positive, company_id)

        # If positive, also update people
        if is_positive:
            org_id = await conn.fetchval("SELECT apollo_id FROM companies WHERE id = $1", company_id)
            if org_id:
                await conn.execute("UPDATE people SET contacted_status = 'replied', updated_at = NOW() WHERE organization_id = $1", org_id)

        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to mark lead positive: {str(e)}")
        if conn: await conn.close()
        return False

async def fetch_engagement_metrics(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Fetches all aggregated metrics for the engagement dashboard.
    
    Args:
        start_date: ISO date string (YYYY-MM-DD) for the start of the date range filter.
        end_date:   ISO date string (YYYY-MM-DD) for the end of the date range filter.
    
    Returns a comprehensive dict with pipeline, outreach, ICP, people, geographic,
    and temporal metrics. All metrics are global (not filtered by auth0_id).
    """
    logger.info("Fetching engagement metrics (start=%s, end=%s)...", start_date, end_date)
    conn = None
    try:
        conn = await asyncpg.connect(dsn=DB_URL)

        # Parse ISO date strings to datetime.date objects for Postgres compatibility
        start_date_parsed = None
        end_date_parsed = None
        if start_date:
            try:
                start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Build a reusable date-range WHERE clause for companies.created_at
        date_params: List[Any] = []
        date_clause = ""
        if start_date_parsed and end_date_parsed:
            date_clause = "WHERE created_at >= $1 AND created_at < ($2::date + interval '1 day')"
            date_params = [start_date_parsed, end_date_parsed]
        elif start_date_parsed:
            date_clause = "WHERE created_at >= $1"
            date_params = [start_date_parsed]
        elif end_date_parsed:
            date_clause = "WHERE created_at < ($1::date + interval '1 day')"
            date_params = [end_date_parsed]

        # Helper: apply date clause to an existing WHERE
        def with_date(base_where: str, param_offset: int = 0) -> tuple:
            """Returns (amended_query_fragment, amended_params)."""
            if not date_params:
                return base_where, []
            shifted = []
            fragment = base_where
            for i, p in enumerate(date_params):
                old = f"${i + 1}"
                new = f"${i + 1 + param_offset}"
                fragment = fragment.replace(old, new)
                shifted.append(p)
            return fragment, shifted

        # -------------------------------------------------------------------
        # 0. Summary counts (global totals)
        # -------------------------------------------------------------------
        summary_row = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM companies) AS total_companies,
                (SELECT COUNT(*) FROM people)    AS total_people,
                (SELECT COUNT(*) FROM emails_sent) AS total_emails_sent,
                (SELECT COUNT(*) FROM companies WHERE positive_reply = TRUE)         AS total_positive_replies,
                (SELECT COUNT(*) FROM people WHERE subscribed = FALSE)               AS total_unsubscribed,
                (SELECT COUNT(*) FROM companies WHERE contacted_status = 'failed')   AS total_bounced
        """)
        summary = dict(summary_row) if summary_row else {}

        # -------------------------------------------------------------------
        # 1. ICP Score Distribution (bucketed for readability)
        # -------------------------------------------------------------------
        icp_dist_query = f"""
            SELECT
                CASE
                    WHEN icp_score < 20  THEN '0-20'
                    WHEN icp_score < 40  THEN '20-40'
                    WHEN icp_score < 60  THEN '40-60'
                    WHEN icp_score < 80  THEN '60-80'
                    ELSE                      '80-100'
                END AS bucket,
                COUNT(*) AS count
            FROM companies
            {date_clause}
            {'AND' if date_clause else 'WHERE'} icp_score IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        icp_rows = await conn.fetch(icp_dist_query, *date_params)
        icp_dist = [dict(r) for r in icp_rows]

        # -------------------------------------------------------------------
        # 2. Outreach KPIs (companies that have been contacted)
        # -------------------------------------------------------------------
        outreach_cond = "AND" if date_clause else "WHERE"
        outreach_query = f"""
            SELECT
                COUNT(*) AS total_sent,
                COUNT(*) FILTER (WHERE contacted_status IN ('opened', 'engaged', 'replied')) AS opened,
                COUNT(*) FILTER (WHERE contacted_status IN ('engaged', 'replied'))           AS clicked,
                COUNT(*) FILTER (WHERE contacted_status = 'replied')                         AS replied,
                COUNT(*) FILTER (WHERE positive_reply = TRUE)                                AS positive_replies,
                COUNT(*) FILTER (WHERE contacted_status = 'opted_out')                       AS unsubscribed,
                COUNT(*) FILTER (WHERE contacted_status = 'failed')                          AS bounced
            FROM companies
            {date_clause}
            {outreach_cond} contacted_status NOT IN ('uncontacted', 'pending', 'requested')
        """
        outreach_row = await conn.fetchrow(outreach_query, *date_params)
        outreach_kpis = dict(outreach_row) if outreach_row else {}

        # -------------------------------------------------------------------
        # 3. Lead Lifecycle Funnel
        # -------------------------------------------------------------------
        lifecycle_query = f"""
            SELECT contacted_status AS stage, COUNT(*) AS count
            FROM companies
            {date_clause}
            GROUP BY contacted_status
        """
        lifecycle_rows = await conn.fetch(lifecycle_query, *date_params)
        lifecycle = {r['stage']: r['count'] for r in lifecycle_rows}

        # -------------------------------------------------------------------
        # 4. Service Traction
        # -------------------------------------------------------------------
        svc_cond = "AND" if date_clause else "WHERE"
        service_query = f"""
            SELECT service,
                   COUNT(*) AS count,
                   COUNT(*) FILTER (WHERE contacted_status = 'replied') AS replies
            FROM companies
            {date_clause}
            {svc_cond} service IS NOT NULL
            GROUP BY service
        """
        service_rows = await conn.fetch(service_query, *date_params)
        service_traction = [dict(r) for r in service_rows]

        # -------------------------------------------------------------------
        # 5. Response Rate by Company Size
        # -------------------------------------------------------------------
        size_cond = "AND" if date_clause else "WHERE"
        size_query = f"""
            SELECT
                CASE
                    WHEN estimated_num_employees < 10  THEN '1-10'
                    WHEN estimated_num_employees < 50  THEN '11-50'
                    WHEN estimated_num_employees < 200 THEN '51-200'
                    ELSE '200+'
                END AS size_range,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE contacted_status = 'replied') AS replies
            FROM companies
            {date_clause}
            {size_cond} estimated_num_employees IS NOT NULL
            GROUP BY size_range
            ORDER BY size_range
        """
        size_rows = await conn.fetch(size_query, *date_params)
        size_metrics = [dict(r) for r in size_rows]

        # -------------------------------------------------------------------
        # 6. Geographic Breakdown (top 15 countries)
        # -------------------------------------------------------------------
        geo_cond = "AND" if date_clause else "WHERE"
        geo_query = f"""
            SELECT country,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE contacted_status = 'replied') AS replies
            FROM companies
            {date_clause}
            {geo_cond} country IS NOT NULL AND country <> ''
            GROUP BY country
            ORDER BY total DESC
            LIMIT 15
        """
        geo_rows = await conn.fetch(geo_query, *date_params)
        geo_breakdown = [dict(r) for r in geo_rows]

        # -------------------------------------------------------------------
        # 7. Industry Breakdown (unnested, top 15)
        # -------------------------------------------------------------------
        industry_cond = "AND" if date_clause else "WHERE"
        industry_query = f"""
            SELECT unnest(industries) AS industry,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE contacted_status = 'replied') AS replies
            FROM companies
            {date_clause}
            {industry_cond} industries IS NOT NULL
            GROUP BY industry
            ORDER BY total DESC
            LIMIT 15
        """
        industry_rows = await conn.fetch(industry_query, *date_params)
        industry_breakdown = [dict(r) for r in industry_rows]

        # -------------------------------------------------------------------
        # 8. Funding Stage Analysis
        # -------------------------------------------------------------------
        funding_cond = "AND" if date_clause else "WHERE"
        funding_query = f"""
            SELECT latest_funding_round AS stage,
                   COUNT(*) AS total,
                   ROUND(AVG(icp_score)::numeric, 1) AS avg_icp,
                   COUNT(*) FILTER (WHERE contacted_status = 'replied') AS replies
            FROM companies
            {date_clause}
            {funding_cond} latest_funding_round IS NOT NULL
            GROUP BY stage
            ORDER BY total DESC
        """
        funding_rows = await conn.fetch(funding_query, *date_params)
        funding_breakdown = [dict(r) for r in funding_rows]

        # -------------------------------------------------------------------
        # 9. People Intelligence
        # -------------------------------------------------------------------
        people_summary_row = await conn.fetchrow("""
            SELECT
                COUNT(*) AS total_people,
                COUNT(*) FILTER (WHERE subscribed = TRUE)      AS subscribed,
                COUNT(*) FILTER (WHERE subscribed = FALSE)     AS unsubscribed,
                COUNT(*) FILTER (WHERE has_replied = TRUE)     AS replied,
                COUNT(*) FILTER (WHERE times_contacted > 0)   AS contacted
            FROM people
        """)
        people_summary = dict(people_summary_row) if people_summary_row else {}

        seniority_rows = await conn.fetch("""
            SELECT seniority, COUNT(*) AS count
            FROM people
            WHERE seniority IS NOT NULL AND seniority <> ''
            GROUP BY seniority
            ORDER BY count DESC
        """)
        people_seniority = [dict(r) for r in seniority_rows]

        dept_rows = await conn.fetch("""
            SELECT unnest(departments) AS department, COUNT(*) AS count
            FROM people
            WHERE departments IS NOT NULL
            GROUP BY department
            ORDER BY count DESC
            LIMIT 10
        """)
        people_departments = [dict(r) for r in dept_rows]

        # -------------------------------------------------------------------
        # 10. Email Sequence Performance (reply rate per sequence step)
        # -------------------------------------------------------------------
        seq_date_join = ""
        seq_params: List[Any] = []
        if date_params:
            if start_date_parsed and end_date_parsed:
                seq_date_join = "AND e.sent_at >= $1 AND e.sent_at < ($2::date + interval '1 day')"
                seq_params = [start_date_parsed, end_date_parsed]
            elif start_date_parsed:
                seq_date_join = "AND e.sent_at >= $1"
                seq_params = [start_date_parsed]
            elif end_date_parsed:
                seq_date_join = "AND e.sent_at < ($1::date + interval '1 day')"
                seq_params = [end_date_parsed]

        sequence_query = f"""
            SELECT
                e.sequence_number,
                COUNT(*) AS total_sent,
                COUNT(*) FILTER (WHERE c.contacted_status = 'replied') AS replies
            FROM emails_sent e
            JOIN companies c ON c.id = e.company_id
            WHERE e.sequence_number IS NOT NULL
            {seq_date_join}
            GROUP BY e.sequence_number
            ORDER BY e.sequence_number
        """
        seq_rows = await conn.fetch(sequence_query, *seq_params)
        sequence_performance = [dict(r) for r in seq_rows]

        # -------------------------------------------------------------------
        # 11. ICP Sub-Score Averages (for radar chart)
        # -------------------------------------------------------------------
        icp_subscores_row = await conn.fetchrow("""
            SELECT
                ROUND(AVG(age_score)::numeric, 1)            AS avg_age,
                ROUND(AVG(employee_count_score)::numeric, 1) AS avg_employee,
                ROUND(AVG(funding_stage_score)::numeric, 1)  AS avg_funding,
                ROUND(AVG(keyword_score)::numeric, 1)        AS avg_keyword,
                ROUND(AVG(contactability_score)::numeric, 1) AS avg_contactability,
                ROUND(AVG(geography_score)::numeric, 1)      AS avg_geography,
                ROUND(AVG(industry_score)::numeric, 1)       AS avg_industry,
                ROUND(AVG(total_score)::numeric, 1)          AS avg_total
            FROM icp_scores
        """)
        icp_subscores = dict(icp_subscores_row) if icp_subscores_row else {}

        # -------------------------------------------------------------------
        # 12. Pipeline Over Time (monthly, last 12 months)
        # -------------------------------------------------------------------
        pipeline_time_query = f"""
            SELECT
                TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS month,
                COUNT(*) AS new_leads
            FROM companies
            {date_clause if date_clause else "WHERE created_at >= NOW() - interval '12 months'"}
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY DATE_TRUNC('month', created_at) ASC
        """
        pipeline_params = date_params if date_params else []
        pipeline_rows = await conn.fetch(pipeline_time_query, *pipeline_params)
        pipeline_over_time = [dict(r) for r in pipeline_rows]

        await conn.close()
        return {
            # Summary
            "summary": summary,
            # Existing
            "icp_score_distribution": icp_dist,
            "outreach_kpis": outreach_kpis,
            "lifecycle": lifecycle,
            "service_traction": service_traction,
            "size_metrics": size_metrics,
            # New
            "geo_breakdown": geo_breakdown,
            "industry_breakdown": industry_breakdown,
            "funding_breakdown": funding_breakdown,
            "people_summary": people_summary,
            "people_seniority": people_seniority,
            "people_departments": people_departments,
            "sequence_performance": sequence_performance,
            "icp_subscores": icp_subscores,
            "pipeline_over_time": pipeline_over_time,
        }
    except Exception as e:
        logger.error(f"Failed to fetch engagement metrics: {str(e)}")
        if conn: await conn.close()
        return {}

async def fetch_icp_settings(pool, auth0_id: str, setting_id: Optional[int] = None) -> dict:
    if setting_id:
        query = "SELECT settings FROM icp_settings WHERE auth0_id = $1 AND id = $2 LIMIT 1"
        args = [auth0_id, setting_id]
    else:
        query = "SELECT settings FROM icp_settings WHERE auth0_id = $1 AND is_active = TRUE LIMIT 1"
        args = [auth0_id]

    conn = None
    try:
        async with pool.acquire(timeout=10.0) as conn:
            row = await conn.fetchrow(query, *args)
        if row and 'settings' in row and row['settings'] is not None:
            return json.loads(row['settings'])
        return {}
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while trying to fetch icp settings: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occured while fetching icp settings: {str(e)}")
        return {}


async def fetch_all_icp_settings(pool, auth0_id: str) -> list:
    query = "SELECT id, name, is_active FROM icp_settings WHERE auth0_id = $1 ORDER BY created_at ASC"
    try:
        async with pool.acquire(timeout=10.0) as conn:
            rows = await conn.fetch(query, auth0_id)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch all icp settings for user {auth0_id}: {str(e)}")
        return []


async def delete_icp_setting(pool, auth0_id: str, setting_id: int) -> bool:
    try:
        async with pool.acquire(timeout=10.0) as conn:
            async with conn.transaction():
                # Check if the setting exists and get its active status
                setting_row = await conn.fetchrow(
                    "SELECT is_active FROM icp_settings WHERE auth0_id = $1 AND id = $2",
                    auth0_id, setting_id
                )
                if not setting_row:
                    return False
                
                # Delete the setting
                await conn.execute(
                    "DELETE FROM icp_settings WHERE auth0_id = $1 AND id = $2",
                    auth0_id, setting_id
                )
                
                # If deleted setting was active, activate another setting if available
                if setting_row['is_active']:
                    next_setting = await conn.fetchrow(
                        "SELECT id FROM icp_settings WHERE auth0_id = $1 ORDER BY created_at ASC LIMIT 1",
                        auth0_id
                    )
                    if next_setting:
                        await conn.execute(
                            "UPDATE icp_settings SET is_active = TRUE WHERE id = $1",
                            next_setting['id']
                        )
                return True
    except Exception as e:
        logger.error(f"Failed to delete icp setting {setting_id} for user {auth0_id}: {str(e)}")
        return False


async def set_active_icp_setting(pool, auth0_id: str, setting_id: int) -> bool:
    try:
        async with pool.acquire(timeout=10.0) as conn:
            async with conn.transaction():
                # Verify that this setting belongs to this user
                exists = await conn.fetchval(
                    "SELECT 1 FROM icp_settings WHERE auth0_id = $1 AND id = $2",
                    auth0_id, setting_id
                )
                if not exists:
                    return False
                
                # Deactivate all and activate target
                await conn.execute(
                    "UPDATE icp_settings SET is_active = (id = $2) WHERE auth0_id = $1",
                    auth0_id, setting_id
                )
                return True
    except Exception as e:
        logger.error(f"Failed to set active icp setting {setting_id} for user {auth0_id}: {str(e)}")
        return False


# TO DO => fix the format of geography
async def upsert_icp_settings(pool, auth0_id: str, settings: dict, name: str = 'Default', setting_id: Optional[int] = None) -> Optional[dict]:
    resolved = {
        "age": [tuple(entry) for entry in settings.get("age", icp["age"])],
        "employee_count": [tuple(entry) for entry in settings.get("employee_count", icp["employee_count"])],
        "funding_stage": settings.get("funding_stage", icp["funding_stage"]),
        "industry": [tuple(entry) for entry in settings.get("industry", icp["industry"])],
        "geography": {
            "primary": (
                settings["geography"]["primary"][0], 
                settings["geography"]["primary"][1]
                ),
            "eastern_eu_wedge": (
                list(_EASTERN_EU_WEDGE),
                settings["geography"]["eastern_eu_wedge"]
                ),
            "north_america": (
                list(_NORTH_AMERICA), 
                settings["geography"]["north_america"]
                ),
            "western_eu_rest": (
                list(_WESTERN_EU_REST), 
                settings["geography"]["western_eu_rest"]
                ),
        },
        "keywords": settings.get("keywords", icp["keywords"]),
        "weights": settings.get("weights", weights),
    }

    conn = None
    try:
        async with pool.acquire(timeout=10.0) as conn:
            async with conn.transaction():
                # If setting_id is provided, check if it exists and belongs to this user.
                # If setting_id is not provided, check if we already have a setting with the same name.
                # If so, we'll update it. Otherwise, insert new.
                if setting_id:
                    # Update existing by id
                    # First deactivate all others if this one is active, or we can just make it active
                    await conn.execute("UPDATE icp_settings SET is_active = FALSE WHERE auth0_id = $1", auth0_id)
                    row = await conn.fetchrow(
                        """
                        UPDATE icp_settings 
                        SET settings = $1::jsonb, name = $2, is_active = TRUE, updated_at = NOW() 
                        WHERE auth0_id = $3 AND id = $4
                        RETURNING id, name
                        """,
                        json.dumps(resolved), name, auth0_id, setting_id
                    )
                    if not row:
                        # Fallback: maybe the ID didn't match auth0_id, let's insert a new one
                        row = await conn.fetchrow(
                            """
                            INSERT INTO icp_settings (auth0_id, settings, name, is_active, created_at, updated_at)
                            VALUES ($1, $2::jsonb, $3, TRUE, NOW(), NOW())
                            RETURNING id, name
                            """,
                            auth0_id, json.dumps(resolved), name
                        )
                else:
                    # No setting_id: check if name already exists for this user to update or insert
                    existing = await conn.fetchrow(
                        "SELECT id FROM icp_settings WHERE auth0_id = $1 AND name = $2",
                        auth0_id, name
                    )
                    await conn.execute("UPDATE icp_settings SET is_active = FALSE WHERE auth0_id = $1", auth0_id)
                    if existing:
                        row = await conn.fetchrow(
                            """
                            UPDATE icp_settings
                            SET settings = $1::jsonb, is_active = TRUE, updated_at = NOW()
                            WHERE id = $2 AND auth0_id = $3
                            RETURNING id, name
                            """,
                            json.dumps(resolved), existing['id'], auth0_id
                        )
                    else:
                        row = await conn.fetchrow(
                            """
                            INSERT INTO icp_settings (auth0_id, settings, name, is_active, created_at, updated_at)
                            VALUES ($1, $2::jsonb, $3, TRUE, NOW(), NOW())
                            RETURNING id, name
                            """,
                            auth0_id, json.dumps(resolved), name
                        )
                
                if row:
                    logger.info("Updated/inserted ICP settings '%s' (ID: %s) for %s", row['name'], row['id'], auth0_id)
                    return dict(row)
        return None
    except asyncpg.PostgresError as e:
        logger.error(f"Database error while upserting icp settings: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while upserting icp settings: {str(e)}")
        return None

if __name__ == "__main__":
    async def main():
        settings = {
            "age": [
                [[0, 2], 100],
                [[3, 5], 70],
                [[6, 10], 50],
                [[11, 20], 30]
            ],

            "employee_count": [
                [[1, 5], 100],
                [[6, 15], 80],
                [[16, 20], 70],
                [[21, 50], 40],
                [[51, 100], 20]
            ],

            "funding_stage": {
                "series_a": 100,
                "seed": 90,
                "pre_seed": 50,
                "grant": 40,
                "bootstrapped": 30,
                "series_b": 10
            },

            "industry": [
                [["fintech", "ecommerce", "saas"], 100],
                [["healthtech", "insurtech"], 70],
                [["education", "government"], 30]
            ],

            "geography": {
                "primary": [
                    ["united kingdom", "ireland", "netherlands", "germany"],
                    100
                ],
                "eastern_eu_wedge": 85,
                "north_america": 60,
                "western_eu_rest": 50
            },

            "keywords": {
                "outsourcing_terms": 100,
                "remote_hiring_terms": 70,
                "generic_terms": 30
            },

            "weights": {
                "geography": 0.30,
                "funding_stage": 0.20,
                "employee_count": 0.15,
                "age": 0.15,
                "industry": 0.15,
                "keywords": 0.05
            }
        }
        async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=10) as pool:
            # x = await get_hiring_area("14.ai", pool)
            x = await fetch_icp_settings(pool, "auth0|6a0329e290f1881ac4d163b4", 1)
            print(x)

    asyncio.run(main())