import os
import logging
import httpx
from dotenv import load_dotenv
import asyncio
from services.db_service import *
from utils.prompts.email_generation_prompt import get_email_generation_prompt

load_dotenv(override=True)
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
BASE_URL = "https://server.smartlead.ai/api/v1" 
SERVER_URL = os.getenv("SERVER_URL")

async def send_email(
        email_to: str,
        subject: str,
        content: str,
        unsubscribe_token: str,
        email_from = None,
        sequence_number: int = 1,
        first_name: str = "",
        last_name: str = "",
        company_name: str = ""
):
    campaign_id = os.getenv(f"SMARTLEAD_CAMPAIGN_STEP_{sequence_number}")
    if not campaign_id:
        logger.warning(f"No Smartlead campaign ID found for sequence step {sequence_number}. Skipping.")
        return None

    # Add unsubscribe footer to email content
    unsubscribe_footer = f"""
    <br><br>
    <hr style="border: 1px solid #ddd;">
    <p style="font-size: 12px; color: #666;">
        If you no longer wish to receive these emails, 
        <a href="{SERVER_URL}/unsubscribe?token={unsubscribe_token}">
            click here to unsubscribe
        </a>.
    </p>
    """
    
    full_content = content + unsubscribe_footer
    
    url = f"{BASE_URL}/campaigns/{campaign_id}/leads"
    params = {"api_key": SMARTLEAD_API_KEY}
    
    payload = {
        "lead_list": [
            {
                "email": email_to,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                "custom_fields": {
                    "personalized_subject": subject,
                    "personalized_body": full_content
                }
            }
        ],
        "settings": {
            "ignore_global_block_list": False,
            "ignore_unsubscribe_list": False,
            "ignore_community_bounce_list": False,
            "ignore_duplicate_leads_in_other_campaign": True
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url, 
            json=payload, 
            params=params,
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        logger.info(f"Email sent (added lead) to {email_to} via Smartlead campaign {campaign_id}")
        return r.json()



if __name__ == "__main__":
    import json
    from outreach_module.ai_email_generation import call_gemini_api
    async def main():
        company_description = """
        Darwin AI is a technology company that specializes in artificial intelligence solutions to enhance business processes, 
        particularly in sales and marketing. The company focuses on data-driven creative testing and analytics, offering software 
        that analyzes advertising creatives to identify effective design elements and messaging. This helps clients tailor their ads 
        to specific audiences and continuously improve their creative strategies.\n\nIn 2023, Darwin AI introduced a dedicated AI platform 
        for consultative sales in high-value B2C sectors such as real estate, automotive, education, and online courses. This platform 
        efficiently filters leads and identifies customer needs, ensuring that only qualified prospects are passed to sales agents, 
        which boosts sales efficiency and reduces costs for small and medium-sized businesses.\n\nDarwin AI's offerings include 
        creative analytics and testing software, consultative sales AI solutions, and personalized tools for SMBs, all aimed 
        at optimizing marketing effectiveness and sales processes. The company serves a range of clients looking to enhance 
        their sales strategies through AI-driven insights.
        """
        first_name = "Mark"
        company_name = "Adept"
        trigger_type = "funding"
        funding_round = "seed"
        sequence_number = 1
        
        prompt = get_email_generation_prompt(
            company_description=company_description,
            first_name = first_name,
            company_name=company_name,
            trigger_type=trigger_type,
            sequence_number=sequence_number,
            funding_round=funding_round
        )
        ai_response = await call_gemini_api(prompt)

        try:
            text = ai_response.candidates[0].content.parts[0].text
            email_json = json.loads(text)

            subject = email_json["subject"]
            content = email_json["content"]
            print(content)

            response = await send_email(
                email_to = 'm10mathenge@gmail.com',
                subject= subject,
                content= content,
                unsubscribe_token = "e3a3c375-cde9-420b-9001-2b188cb2fac8",
                first_name=first_name,
                company_name=company_name
            )
            print("Response:", response)
        except Exception as e:
            error_msg = f"Couldn't send email: {e}"
            logger.exception(error_msg)
    
    asyncio.run(main())
