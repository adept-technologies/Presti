import os
import httpx 
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "https://api.smartlead.ai/api/v1" 
API_KEY = os.getenv("SMARTLEAD_API_KEY")
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"} 

# 1. CREATE CAMPAIGN 
async def create_campaign(name, client): 
    r = await client.post(f"{BASE_URL}/campaigns", json={"name": name}, headers=headers) 
    return r.json()["id"] 

# 2. ADD SEQUENCES 
async def add_sequences(campaign_id, client): 
    payload = { 
        "sequences": [ 
            { 
                "seq_number": 1, 
                "subject": "Quick question about {{company_name}}", 
                "email_body": "<p>Hi {{first_name}},</p><p>Your message here.</p>", 
                "seq_delay_details": {"delay_in_days": 0}, 
                "seq_type": "EMAIL" 
            }, 
            { 
                "seq_number": 2, 
                "subject": "Following up", 
                "email_body": "<p>Hi {{first_name}},</p><p>Just checking in!</p>", 
                "seq_delay_details": {"delay_in_days": 3}, 
                "seq_type": "EMAIL" 
            } 
        ] 
    } 
    return await client.put(
        f"{BASE_URL}/campaigns/{campaign_id}/sequences", 
        json=payload, 
        headers=headers).json() 
        
# 3. CONNECT EMAIL ACCOUNTS 
async def connect_email_accounts(campaign_id, email_account_ids, client): 
    return await client.post(
        f"{BASE_URL}/campaigns/{campaign_id}/email-accounts", 
        json={"email_account_ids": email_account_ids}, 
        headers=headers).json() 
        
# 4. ADD LEADS (max 400 per request — loop for larger lists) 
async def add_leads(campaign_id, leads, client): 
    return await client.post(
        f"{BASE_URL}/campaigns/{campaign_id}/leads", 
        json={"lead_list": leads}, 
        headers=headers).json() 
        
# 5. CONFIGURE SCHEDULE 
async def configure_schedule(campaign_id, client): 
    payload = { 
        "timezone": "America/New_York", 
        "days_of_the_week": [1, 2, 3, 4, 5], # Mon–Fri 
        "start_hour": "09:00", 
        "end_hour": "17:00", 
        "min_time_btw_emails": 5, 
        "max_new_leads_per_day": 50 
    } 
    return await client.put(
        f"{BASE_URL}/campaigns/{campaign_id}/schedule", 
        json=payload, 
        headers=headers).json() 

# 6. UPDATE SETTINGS 
async def update_settings(campaign_id, client): 
    payload = {"follow_up_percentage": 100, "track_settings": []} 
    return await client.put(f"{BASE_URL}/campaigns/{campaign_id}/settings", json=payload, headers=headers).json() 
    
# 7. LAUNCH 
async def launch_campaign(campaign_id, client): 
    return await client.patch(f"{BASE_URL}/campaigns/{campaign_id}/status", json={"status": "START"}, headers=headers).json() 
    
# ── RUN ── 
if __name__ == "__main__": 
    async def main():
        async with httpx.AsyncClient(timeout=30.0) as client:
            campaign_id = create_campaign("My Test Campaign", client) 
            print(f"✓ Campaign: {campaign_id}") 
            add_sequences(campaign_id, client) 
            print("✓ Sequences added") 
            connect_email_accounts(campaign_id, [12345], client) # replace with your account ID(s) 
            print("✓ Accounts connected") 
            leads = [ 
                {
                    "email": "alice@company.com", 
                    "first_name": "Alice", 
                    "last_name": "Smith", 
                    "company_name": "Acme"
                }, 
                {
                    "email": "bob@startup.io", 
                    "first_name": "Bob", 
                    "last_name": "Jones", 
                    "company_name": "StartupXYZ"
                }, 
            ] 
            add_leads(campaign_id, leads, client) 
            print("✓ Leads added") 
            configure_schedule(campaign_id, client) 
            print("✓ Schedule set") 
            update_settings(campaign_id, client) 
            print("✓ Settings updated") 
            launch_campaign(campaign_id, client) 
            print("✓ Campaign launched!") 
            
            """
            A few key notes: 
            - Email account IDs — find yours via GET /api/v1/email-accounts 
            - Lead batching — loop add_leads() in chunks of 400 for large lists 
            - Merge tags — {{first_name}}, {{last_name}}, {{company_name}} are auto-replaced per lead 
            - Schedule — days_of_the_week uses 0–6 (Sun=0, Sat=6); adjust hours and timezone as needed
            """