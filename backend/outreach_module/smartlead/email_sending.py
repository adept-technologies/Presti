import os
import httpx 
import logging
import asyncio
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://server.smartlead.ai/api/v1" 
API_KEY = os.getenv("SMARTLEAD_API_KEY")
SMARTLEAD_EMAIL_ACCOUNT_ID = os.getenv("SMARTLEAD_EMAIL_ACCOUNT_ID")

headers = {"Content-Type": "application/json"} 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 1. CREATE CAMPAIGN 
async def create_campaign(name, client): 
    logger.info("Creating campaign...")
    url = f"{BASE_URL}/campaigns/create"
    params = {"api_key": API_KEY}
    r = await client.post(url, json={"name": name}, params=params, headers=headers) 
    r.raise_for_status()
    data = r.json()
    logger.info("Campaign created. ID is: %r", data.get("id"))
    return data.get("id") 

# 2. ADD SEQUENCES 
async def add_sequences(campaign_id, client): 
    logger.info("Adding sequences...")
    url = f"{BASE_URL}/campaigns/{campaign_id}/sequences"
    params = {"api_key": API_KEY}
    payload = [ 
        { 
            "seq_number": 1, 
            "seq_delay_details": {"delay_in_days": 0}, 
            "variant_distribution_type": "MANUALLY_EQUAL",
            "variants": [
                {
                    "subject": "{{personalized_subject}}", 
                    "email_body": "{{personalized_body}}", 
                    "variant_label": "A"
                }
            ]
        }
    ] 
    r = await client.post(url, json=payload, params=params, headers=headers)
    r.raise_for_status()
    return r.json()
        
# 3. CONNECT EMAIL ACCOUNTS 
async def connect_email_accounts(campaign_id, email_account_ids, client): 
    logger.info("Connecting email address...")
    url = f"{BASE_URL}/campaigns/{campaign_id}/email-accounts"
    params = {"api_key": API_KEY}
    r = await client.post(
        url, 
        json={"email_account_ids": email_account_ids}, 
        params=params,
        headers=headers
    ) 
    r.raise_for_status()
    return r.json()
        
# 4. ADD LEADS (max 400 per request — loop for larger lists) 
#async def add_leads(campaign_id, leads, client): 
    #logger.info("Adding leads...")
    #url = f"{BASE_URL}/campaigns/{campaign_id}/leads"
    #params = {"api_key": API_KEY}
    #r = await client.post(
        #url, 
        #json={"lead_list": leads}, 
        #params=params,
        #headers=headers
    #) 
    #r.raise_for_status()
    #return r.json()
        
# 5. CONFIGURE SCHEDULE 
#async def configure_schedule(campaign_id, client): 
    #logger.info("Configuring schedule...")
    #url = f"{BASE_URL}/campaigns/{campaign_id}/schedule"
    #params = {"api_key": API_KEY}
    #payload = { 
        #"timezone": "America/New_York", 
        #"days_of_the_week": [1, 2, 3, 4, 5], # Mon–Fri 
        #"start_hour": "09:00", 
        #"end_hour": "17:00", 
        #"min_time_btw_emails": 5, 
        #"max_leads_per_day": 50 
    #} 
    #r = await client.post(url, json=payload, params=params, headers=headers)
    #r.raise_for_status()
    #return r.json()

# 6. UPDATE SETTINGS 
async def update_settings(campaign_id, client): 
    logger.info("Updating campaign settings...")
    url = f"{BASE_URL}/campaigns/{campaign_id}/settings"
    params = {"api_key": API_KEY}
    payload = {"track_settings": []} 
    r = await client.post(url, json=payload, params=params, headers=headers) 
    r.raise_for_status()
    logger.info("Settings updated")
    return r.json()
    
# 7. LAUNCH 
async def launch_campaign(campaign_id, client): 
    logger.info("Launching campaign...")
    url = f"{BASE_URL}/campaigns/{campaign_id}/status"
    params = {"api_key": API_KEY}
    r = await client.patch(url, json={"status": "START"}, params=params, headers=headers) 
    r.raise_for_status()
    return r.json()
    
# ── RUN ── 
if __name__ == "__main__": 
    """
    A few key notes: 
    - WEBHOOOK!!! ENSURE DB MATCHES!!!
    - Email account IDs — find yours via GET /api/v1/email-accounts 
    - Lead batching — loop add_leads() in chunks of 400 for large lists 
    - Merge tags — {{first_name}}, {{last_name}}, {{company_name}} are auto-replaced per lead 
    - Schedule — days_of_the_week uses 0–6 (Sun=0, Sat=6); adjust hours and timezone as needed
    """
    async def main():
        # Parse email account ID from environment
        email_account_ids = []
        if SMARTLEAD_EMAIL_ACCOUNT_ID:
            email_account_ids = [
                int(x.strip()) 
                for x in SMARTLEAD_EMAIL_ACCOUNT_ID.split(",") 
                if x.strip().isdigit()
            ]
        
        if not email_account_ids:
            logger.error("SMARTLEAD_EMAIL_ACCOUNT_ID is not set or invalid.")
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 1. Create campaign
                campaign_id = await create_campaign("My Test Campaign", client) 
                print(f"✓ Campaign created with ID: {campaign_id}") 
                
                # 2. Add sequences
                #await add_sequences(campaign_id, client) 
                #print("✓ Sequences added") 
                
                # 3. Connect email accounts
                await connect_email_accounts(campaign_id, email_account_ids, client) 
                print("✓ Accounts connected") 
                
                # 4. Add leads
                lead_payload = {
                    "lead_list": [
                        {
                            "email": "lead@company.com",
                            "first_name": "John",
                            "last_name": "Smith",
                            "company_name": "Acme Corp",
                            "custom_fields": {
                                "personalized_subject": "Quick question about Acme Corp",
                                "personalized_body": "<p>Hi John, I noticed your company...</p>"
                            }
                        }
                    ]
                }

                #await add_leads(campaign_id, leads, client) 
                #print("✓ Leads added") 
                
                # 5. Configure schedule
                #await configure_schedule(campaign_id, client) 
                #print("✓ Schedule set") 
                
                # 6. Update settings
                await update_settings(campaign_id, client) 
                print("✓ Settings updated") 
                
                # 7. Launch campaign
                await launch_campaign(campaign_id, client) 
                print("✓ Campaign launched successfully!")

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Error during campaign creation: {e}", exc_info=True)

    asyncio.run(main())
