import logging
import asyncio
import asyncpg
import json
from typing import Dict, Any
from scoring_module.icp_scoring import ICPScorer
from services.db_service import fetch_company_details, store_icp_score, update_company_icp_score, company_is_unscored

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Fetch unscored companies
async def score_and_store(pool: asyncpg.Pool, company_id: int, semaphore: asyncio.Semaphore, auth0_id: str, icp: Dict[str, Any]):
    async with semaphore: 

        #Fetch company details
        company_details = await fetch_company_details(company_id, auth0_id)
        if not company_details:
            logger.warning(f"No company details found for company id: {company_id}")
            return
        org_name = company_details.get("name", "")
        org_founded_year = company_details.get("founded_year", None)
        org_employee_count = company_details.get("estimated_num_employees", None)
        org_funding_stage = company_details.get("latest_funding_round", "")
        org_keywords = company_details.get("keywords", [])
        org_people = company_details.get("people", [])
        org_linkedin = company_details.get("linkedin_url", "")
        org_country = company_details.get("country", "")
        org_industry = company_details.get("industries", [])
        weights = icp["weights"]

        #Calculate total score
        scorer = ICPScorer(icp, weights, org_name, org_founded_year, org_employee_count,
                        org_funding_stage, org_keywords, org_people,
                        linkedin=org_linkedin, country=org_country, industry=org_industry)
        await scorer.log_scoring_start(org_name)
        scoring_data = await scorer.calculate_total_score()

        #Store icp score
        age_score = scoring_data.get("age_score", None)
        employee_count_score = scoring_data.get("employee_count_score", None)
        funding_stage_score = scoring_data.get("funding_stage_score", None)
        industry_score = scoring_data.get("industry_score", None)
        final_keywords_score = scoring_data.get("final_keywords_score", None)
        contactability_score = scoring_data.get("contactability_score", None)
        geography_score = scoring_data.get("geography_score", None)
        category_breakdown = scoring_data.get("category_breakdown", {})
        top_matches = scoring_data.get("top_matches", {})
        interpretation = scoring_data.get("interpretation")
        final_score = scoring_data.get("total_score") if scoring_data.get("total_score") else 0
        
        await store_icp_score(pool, company_id, age_score, employee_count_score,
                            funding_stage_score, final_keywords_score, contactability_score,
                            geography_score, industry_score, round(final_score, 1), category_breakdown,
                            top_matches, interpretation, auth0_id)
        await update_company_icp_score(pool, company_id, round(final_score, 1))

def normalize_icp(settings_raw) -> dict:
    if isinstance(settings_raw, str):
        try:
            return json.loads(settings_raw)
        except Exception:
            return {}
    return settings_raw or {}

async def score_user(pool: asyncpg.Pool, auth0_id: str, icp_raw, semaphore: asyncio.Semaphore):
    icp = normalize_icp(icp_raw)
    if not icp or "weights" not in icp:
        logger.warning(f"No valid ICP settings found for user {auth0_id}. Skipping user.")
        return
        
    logger.info(f"Scoring for user {auth0_id}...")
    unscored = await company_is_unscored(pool, auth0_id)
    company_ids = [c.get("id") for c in unscored]

    if not company_ids:
        logger.info(f"No unscored companies for user {auth0_id}")
        return

    tasks = [score_and_store(pool, c_id, semaphore, auth0_id, icp) for c_id in company_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for company_id, result in zip(company_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Scoring failed for user={auth0_id} company_id={company_id}: {result}")

async def main(pool: asyncpg.Pool, auth0_id: str = None):
    from services.db_service import fetch_all_users_with_icp, fetch_icp_settings
    logger.info("Scoring companies...")

    # one semaphore shared across ALL users and ALL companies
    # caps total concurrent DB/API operations regardless of user count
    semaphore = asyncio.Semaphore(20)

    if auth0_id:
        # Score only for the specified user
        icp_config = await fetch_icp_settings(pool, auth0_id)
        if icp_config:
            await score_user(pool, auth0_id, icp_config, semaphore)
        else:
            logger.error(f"No ICP settings found for user {auth0_id}. Aborting scoring.")
    else:
        # Score for all users in the system
        users = await fetch_all_users_with_icp(pool)
        logger.info(f"Scoring for {len(users)} users")
        user_tasks = [score_user(pool, user["auth0_id"], user["settings"], semaphore) for user in users]
        await asyncio.gather(*user_tasks, return_exceptions=True)

    logger.info("ICP Scoring Done")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    DB_URL = os.getenv("DATABASE_URL")
    async def run():
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await main(pool, "auth0|6a0329e290f1881ac4d163b4")

    asyncio.run(run())