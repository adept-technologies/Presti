import os
import json
import asyncio
import asyncpg
import logging
import aiofiles
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

# We use a dictionary to map SmartLead events to a value in the contacted_status db column.
# The 'status' is the value to be set in the database.
# The 'precedence' is a numerical value that determines which status is "better".
# A higher number means a higher precedence. This prevents a "bounce" from overwriting
# a "delivered" status.
EVENT_STATUS_MAP = {
    "EMAIL_SENT": {"status": "contacted", "precedence": 2},
    "EMAIL_BOUNCE": {"status": "failed", "precedence": 1},
    "EMAIL_REPLY": {"status": "replied", "precedence": 3},
    "LEAD_UNSUBSCRIBED": {"status": "opted_out", "precedence": 4}, # A terminal status
}

async def update_contacted_status(events):
    """
    Updates emails_sent.status from webhook events,
    propagates status to people, then updates company status.
    """

    try:
        #Write events to file
        try:
            async with aiofiles.open("smartlead_webhooks", "a") as file:
                await file.write(json.dumps(events, indent=2))
        except Exception as file_err:
            logger.warning(f"Could not write webhook log to file: {file_err}")

        # Build a map of emails to deduplicate and store their highest precedence status
        email_updates_map = {}
        for event in events:
            logger.info(f"Event is: {event}")
            email = event.get("to_email")
            sl_event = event.get("event_type")
            update_info = EVENT_STATUS_MAP.get(sl_event)
            
            if email and update_info:
                current_best = email_updates_map.get(email)
                if not current_best or update_info["precedence"] > current_best["precedence"]:
                    email_updates_map[email] = {
                        "email": email,
                        "status": update_info["status"],
                        "precedence": update_info["precedence"]
                    }

        email_updates = list(email_updates_map.values())
        if not email_updates:
            logger.info("No valid email events to process.")
            return

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with pool.acquire() as conn:
                # We wrap the entire operation in a transaction to ensure atomicity
                async with conn.transaction():
                    # Create a temporary table for a single, efficient update query
                    await conn.execute("""
                        CREATE TEMP TABLE tmp_email_status (
                            email TEXT PRIMARY KEY,
                            status contacted_status_enum,
                            precedence INTEGER
                        ) ON COMMIT DROP;
                    """)

                    # Bulk insert all email updates into the temp table
                    await conn.executemany(
                        "INSERT INTO tmp_email_status(email, status, precedence) VALUES($1, $2, $3)",
                        [(email["email"], email['status'], email['precedence']) for email in email_updates]
                    )

                    # Update emails_sent with new statuses, respecting precedence
                    # (won't downgrade e.g. 'engaged' back to 'contacted' from a later 'open' event)
                    await conn.execute("""
                        UPDATE emails_sent e
                        SET status = t.status::contacted_status_enum
                        FROM tmp_email_status t
                        JOIN people p ON LOWER(p.email) = LOWER(t.email)
                        WHERE e.recipient_id = p.id
                        AND t.precedence >= COALESCE(
                            CASE e.status::text
                                WHEN 'opted_out'  THEN 4
                                WHEN 'replied'    THEN 3
                                WHEN 'contacted'  THEN 2
                                WHEN 'failed'     THEN 1
                                ELSE 0
                            END, 0
                        );
                    """
                    )

                    # Update each person's contacted_status, respecting precedence.
                    # 'open' maps to 'contacted' (precedence 3) and is handled here.
                    await conn.execute("""
                        UPDATE people p
                        SET
                            contacted_status = t.status,
                            times_contacted = times_contacted + CASE
                                WHEN t.status = 'contacted' THEN 1
                                ELSE 0
                            END
                        FROM tmp_email_status t
                        WHERE LOWER(p.email) = LOWER(t.email)
                        AND t.precedence >= COALESCE(
                            CASE p.contacted_status::text
                                WHEN 'opted_out'  THEN 4
                                WHEN 'replied'    THEN 3
                                WHEN 'contacted'  THEN 2
                                WHEN 'failed'     THEN 1
                                ELSE 0
                            END, 0
                        );
                    """)


                    # Get all affected organization_ids
                    org_ids = await conn.fetch("""
                        SELECT DISTINCT organization_id
                        FROM people
                        WHERE contacted_status IN ('contacted','replied','failed','opted_out')
                    """)
                    org_id_list = [record["organization_id"] for record in org_ids]

                    # Update companies based on the highest status of their people
                    if org_id_list:
                        await conn.execute("""
                            WITH company_max_status AS (
                                SELECT
                                    organization_id,
                                    MAX(
                                        CASE contacted_status
                                            WHEN 'opted_out'  THEN 4
                                            WHEN 'replied'    THEN 3
                                            WHEN 'contacted'  THEN 2
                                            WHEN 'failed'     THEN 1
                                            ELSE 0
                                        END
                                    ) AS max_precedence
                                FROM people
                                WHERE organization_id = ANY($1::text[])
                                GROUP BY organization_id
                            )
                            UPDATE companies c
                            SET contacted_status = CASE cns.max_precedence
                                WHEN 4 THEN 'opted_out'::contacted_status_enum
                                WHEN 3 THEN 'replied'::contacted_status_enum
                                WHEN 2 THEN 'contacted'::contacted_status_enum
                                WHEN 1 THEN 'failed'::contacted_status_enum
                                ELSE 'uncontacted'::contacted_status_enum
                            END
                            FROM company_max_status cns
                            WHERE c.apollo_id = cns.organization_id;
                        """, org_id_list)

        logger.info(f"Updated {len(email_updates)} people and {len(org_id_list)} companies.")

    except Exception as e:
        logger.error(f"Failed to update contacted status because: {str(e)}")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_events = [
        {"to_email": "aalice@example.com", "event_type": "EMAIL_SENT"},
        {"to_email": "bbob@example.com", "event_type": "EMAIL_REPLY"},
        {"to_email": "ccarol@example.com", "event_type": "EMAIL_BOUNCE"},
        {"to_email": "ddave@example.com", "event_type": "LEAD_UNSUBSCRIBED"},
        {"to_email": "aalice@example.com", "event_type": "EMAIL_REPLY"},  # Alice gets a higher precedence event
    ]
    asyncio.run(update_contacted_status(sample_events))