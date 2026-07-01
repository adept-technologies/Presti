import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv
from config.logging_config import setup_logging
import logging
from quart import Quart, jsonify, request, send_file, send_from_directory
from quart_cors import cors
from services.db_service import fetch_emails_sent, unsubscribe_user, get_user_by_token, add_company_note, delete_company_note, fetch_companies, fetch_people, fetch_company_details, fetch_events, mark_lead_replied, mark_lead_positive, fetch_engagement_metrics, fetch_icp_settings, fetch_all_icp_settings, delete_icp_setting, set_active_icp_setting
from services.email_sending import *
from services.sendgrid_webhook import *
from services.export_to_excel import export_to_excel
from import_excel.import_excel import main as import_excel_main
from orchestration.main import main as orchestration_main 
from orchestration.outreach import main as outreach_main
from orchestration.scoring import score_and_store, normalize_icp
import httpx
from utils.find_missing_people import find_missing_people
from healthcheck import HealthCheck
from outreach_module.smartlead.warmup_stats import get_warmup_stats
from utils.auth import requires_auth

#==============================APP SETUP====================================
# Configure logging before creating quart app
setup_logging()
logger = logging.getLogger(__name__)

def handle_task_result(task: asyncio.Task) -> None:
    """Callback attached to background tasks so exceptions are never silently lost."""
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Unhandled exception in background task: %s", task.get_name())

#The Database in use
load_dotenv()  # Never override env vars already set by Docker Compose / the OS
DB_URL = os.getenv("DATABASE_URL")

#Create quart App
app = Quart(__name__, static_folder="static", static_url_path="")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
app.logger.handlers = [] #Remove quart's default logging
app.logger.propagate = True #Use our configured logger

allowed_origins = [
    "http://localhost:4200",
    "http://localhost:5050",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:5050",
    "http://75.119.133.12"
    "http://lead-gen.adept-techno.co.ke",
    "https://lead-gen.adept-techno.co.ke"
]
server_url = os.getenv("SERVER_URL")
if server_url and server_url not in allowed_origins:
    allowed_origins.append(server_url)

app = cors(
    app,
    allow_origin=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True
)
#=================================APIs=======================================

# ============================================================================
# Serve React App
# ============================================================================

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
async def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return await send_from_directory(app.static_folder, path)
    else:
        return await send_from_directory(app.static_folder, "index.html")
        
@app.route("/debug")
def debug():
    return {
        "static_folder": app.static_folder,
        "static_folder_exists": os.path.exists(app.static_folder),
        "static_folder_contents": os.listdir(app.static_folder) if os.path.exists(app.static_folder) else [],
        "cwd": os.getcwd(),
        "index_exists": os.path.exists(os.path.join(app.static_folder, "index.html"))
    }

@app.route('/login', methods=['GET'])
async def login_route():
    return await send_from_directory(app.static_folder, "index.html")

@app.route("/api/config", methods=["GET"])
@app.route("/config", methods=["GET"])
async def get_config():
    # Return API_URL only. Empty string = frontend & backend are on the same
    # origin (production), so the Angular app will use relative URLs.
    # Only set API_URL when the API lives on a DIFFERENT host/port than the frontend.
    api_url = os.getenv("API_URL") or ""
    return jsonify({"apiUrl": api_url}), 200

# =============================================================================
# HEALTH CHECK
# =============================================================================
health = HealthCheck()
app.add_url_rule('/health', 'health', view_func=lambda: health.run())

@app.route('/settings/icp', methods=['GET'])
@requires_auth
async def settings_get_icp():
    """Return ICP settings for the logged-in user (by auth0 id).
    If no settings found, return empty object with 200 so frontend can trigger modal.
    """
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            settings_all = await fetch_all_icp_settings(pool, auth0_id)
            
            # Find active setting
            active_setting = None
            for s in settings_all:
                if s.get('is_active'):
                    active_setting = s
                    break
            
            settings = {}
            if active_setting:
                settings = await fetch_icp_settings(pool, auth0_id, active_setting['id'])
            
            return jsonify({
                'icp': settings or {},
                'active_id': active_setting['id'] if active_setting else None,
                'active_name': active_setting['name'] if active_setting else None,
                'all_settings': settings_all
            }), 200
    except Exception as e:
        logger.error(f"Failed to fetch ICP settings: {str(e)}")
        return jsonify({'Error': 'Failed to fetch ICP settings', 'Message': str(e)}), 500


async def background_rescore_for_user(auth0_id: str):
    logger.info("Background rescoring started for user: %s", auth0_id)
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            companies = await fetch_companies(auth0_id)
            if not companies:
                logger.info("No companies found to re-score")
                return
                
            icp_config = await fetch_icp_settings(pool, auth0_id)
            icp = normalize_icp(icp_config)
            if not icp or "weights" not in icp:
                logger.error(f"No valid ICP settings found for user {auth0_id} to re-score.")
                return
                
            semaphore = asyncio.Semaphore(20)
            tasks = [score_and_store(pool, c.get("id"), semaphore, auth0_id, icp) for c in companies]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Background rescoring finished for user: %s", auth0_id)
    except Exception as e:
        logger.error("Failed background rescoring for user %s: %s", auth0_id, str(e))

@app.route('/settings/icp', methods=['POST', 'PUT'])
@requires_auth
async def settings_upsert_icp():
    """Create or update ICP settings for the logged-in user."""
    try:
        data = await request.json
        if not data or 'icp' not in data:
            return jsonify({'Error': 'Missing icp payload'}), 400

        auth0_id = request.user.get('sub') or request.user.get('user_id')
        name = data.get('name', 'Default')
        setting_id = data.get('setting_id')

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            result = await upsert_icp_settings(pool, auth0_id, data['icp'], name, setting_id)

        if result:
            app.add_background_task(background_rescore_for_user, auth0_id)
            return jsonify({'Success': True, 'setting': result}), 200
        else:
            return jsonify({'Error': 'Failed to save settings'}), 500
    except Exception as e:
        logger.error(f"Failed to upsert ICP settings: {str(e)}")
        return jsonify({'Error': 'Failed to save settings', 'Message': str(e)}), 500

@app.route('/settings/icp/<int:setting_id>', methods=['DELETE'])
@requires_auth
async def settings_delete_icp(setting_id):
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            success = await delete_icp_setting(pool, auth0_id, setting_id)
        if success:
            app.add_background_task(background_rescore_for_user, auth0_id)
            return jsonify({'Success': True}), 200
        else:
            return jsonify({'Error': 'Failed to delete setting'}), 400
    except Exception as e:
        logger.error(f"Failed to delete ICP setting: {str(e)}")
        return jsonify({'Error': 'Failed to delete setting', 'Message': str(e)}), 500

@app.route('/settings/icp/<int:setting_id>/activate', methods=['POST'])
@requires_auth
async def settings_activate_icp(setting_id):
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            success = await set_active_icp_setting(pool, auth0_id, setting_id)
        if success:
            app.add_background_task(background_rescore_for_user, auth0_id)
            return jsonify({'Success': True}), 200
        else:
            return jsonify({'Error': 'Failed to activate setting'}), 400
    except Exception as e:
        logger.error(f"Failed to activate ICP setting: {str(e)}")
        return jsonify({'Error': 'Failed to activate setting', 'Message': str(e)}), 500


# =============================================================================
# SMARTLEAD WARMUP STATS
# =============================================================================
@app.route('/warmup-stats', methods=["GET"])
async def warmup_stats():
    return await get_warmup_stats()


@app.route('/find-missing-people', methods=["GET", "POST"])
@requires_auth
async def get_missing_people():
    logger.info("Manual trigger: Discover and enrich missing people...")
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                await find_missing_people(pool, client)
        return jsonify({"Success": "Discover people pipeline complete"}), 200
    except Exception as e:
        logger.error(f"Failed to discover people: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

@app.route('/run', methods=["GET", "POST"])
@requires_auth
async def main():
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        # Run the pipeline in the background
        app.add_background_task(orchestration_main, auth0_id)
        return jsonify({"success": "Main function done"}), 200
    except Exception as e:
        return jsonify({"Error": "An unexpected error occured", "Message": str(e) }), 500

# Feeder function for /outreach
async def outreach_task(org_ids):
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await outreach_main(pool, organization_ids=org_ids)
    except Exception:
        logger.exception("Unhandled exception in outreach_task")

@app.route('/outreach', methods=["POST"])
@requires_auth
async def trigger_outreach():
    logger.info("Manual trigger: Starting outreach...")
    try:
        org_ids = None
        app.add_background_task(outreach_task, org_ids=org_ids)
        return jsonify({"Success": "Outreach pipeline complete"}), 202
    except Exception as e:
        logger.error(f"Failed to run outreach: {str(e)}")
        return jsonify({"Error": str(e)}), 500

# For when the scoring algorithm changes
@app.route('/rescore-all', methods=["POST"])
@requires_auth
async def rescore_all():
    logger.info("Manual trigger: Re-scoring all companies...")
    try:
        companies = await fetch_companies()
        if not companies:
            return jsonify({"Message": "No companies found to score"}), 200
        
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            icp = await fetch_icp_settings(pool, auth0_id)
            if not icp or not icp.get("icp"):
                return jsonify({"Error": "No ICP settings found. Please configure ICP settings first."}), 400
            icp_config = icp["icp"]
            semaphore = asyncio.Semaphore(10)
            tasks = [score_and_store(pool, c.get("id"), semaphore, auth0_id, icp_config) for c in companies]
            await asyncio.gather(*tasks)
            
        return jsonify({"Success": f"Re-scored {len(companies)} companies"}), 200
    except Exception as e:
        logger.error(f"Failed to re-score companies: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

#Database API for fetching companies
@app.route('/fetch-companies', methods=["GET"])
@requires_auth
async def fetch_company_data():
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        company_data = await fetch_companies(auth0_id)
    except Exception as e:
        return jsonify({"Error": "Failed to fetch companies", "Message": str(e)}), 500
    return jsonify(company_data), 200

#Database API for fetching people
@app.route('/fetch-people', methods=["GET"])
@requires_auth
async def fetch_people_data():
    try:
        people_data = await fetch_people()
    except Exception as e:
        return jsonify({"Error": "Failed to fetch people", "Message": str(e)}), 500
    return jsonify(people_data), 200

#Database API for fetching company details
@app.route('/fetch-company-details/<id>', methods=["GET"])
@requires_auth
async def fetch_company_details_data(id):
    try:
        company_id = int(id)
    except (ValueError, TypeError):
        return jsonify({'Error': 'Invalid company ID', 'Message': 'ID must be an integer'}), 400
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        company_details = await fetch_company_details(company_id, auth0_id)
        if not company_details:
            return jsonify({'Error': 'No company details found', "Message": "Company details list is empty"}), 404
        return jsonify(company_details), 200
    except Exception as e:
        logger.error(f"Error fetching company details for ID {id}: {str(e)}")
        return jsonify({'Error': 'An unexpected error occurred', 'Message': str(e)}), 500

#Receive phone numbers from Apollo's People Enrichment API
#This method is dormant and not yet working.
@app.route('/apollo-phone-webhook', methods=["POST"])
async def receive_user_phone_number():
    logger.info("Receiving user phone number...")
    try:
        data = request.json
        if data:
            logger.info("Received phone number from Apollo webhook")
            logger.info(data)
            return jsonify({"status": "success", "message": "Phone number received"}), 200
        else:
            return jsonify({"status": "error", "message": "No data received"}), 400

    except Exception as e:
        logger.error(f"Failed to get phone number: {str(e)}")
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

#Smartlead webhook to receive data about emails sent
@app.route('/webhook', methods=["POST"])
async def smartlead_events_webhook():
    logger.info("Fetching webhook event data...")

    payload = await request.json
    if not payload:
        return jsonify({"Error": "No events received in request body"}), 400

    # Smartlead sends one event per POST as a single JSON object.
    # Normalize to a list so update_contacted_status can iterate uniformly.
    events = [payload] if isinstance(payload, dict) else payload

    try:
        # Get the running loop and schedule the update in the background
        # This allows the webhook to return 200 OK immediately and prevents loop collisions
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(update_contacted_status(events))
            task.add_done_callback(handle_task_result)
        else:
            # Fallback if no loop is running (unlikely during active orchestration)
            asyncio.run(update_contacted_status(events))
            
        logger.info("Webhook event data accepted for processing")
        return jsonify({"Success": "Accepted"}), 200

    except Exception as e:
        logger.error(f"Failed to accept webhook data: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

#Endpoint to fetch events
@app.route('/events', methods=["GET"])
@requires_auth
async def get_events():
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            events = await fetch_events(pool)
            return jsonify(events), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching events: {str(e)}")
        return jsonify([]), 500
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        return jsonify([]), 500

@app.route('/keywords', methods=["GET"])
@requires_auth
async def get_keywords():
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with pool.acquire() as conn:
                query = "SELECT keywords FROM companies"
                keyword_records = await conn.fetch(query)
                keyword_list = [dict(keywords) for keywords in keyword_records]
                return jsonify(keyword_list), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching keywords: {str(e)}")
        return jsonify({"Error": "Database error", "Message": str(e)}), 500
    except Exception as e:
        logger.error(f"Failed to fetch keywords: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

@app.route('/export', methods=["GET"])
@requires_auth
async def export():
    try:
        auth0_id = request.user.get('sub') or request.user.get('user_id')
        companies = await fetch_companies(auth0_id)
        exported_data = await export_to_excel(companies)
        if not exported_data:
            return jsonify({"Error": "No data to export"}), 400
        return send_file(exported_data, as_attachment=True)
    except Exception as e:
        return jsonify({"Error":"An unexpected error occured", "details": str(e)}), 500

@app.route('/import-leads', methods=['POST'])
@requires_auth
async def import_leads():
    try:
        if 'file' not in request.files:
            return jsonify({"Error": "No file in the request"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"Error": "No selected file"}), 400

        auth0_id = request.user.get('sub') or request.user.get('user_id')
        await import_excel_main(file, auth0_id)
        return jsonify({"Success": f"Done importing file {file.filename}"}), 200

    except Exception as e:
        logger.error(f"Failed to import excdl file: {str(e)}")
        return jsonify({"Error": "Failed to import file", "details": str(e)}), 500

@app.route('/view-sent-emails/<company_id>', methods=["GET"])
@requires_auth
async def get_sent_emails(company_id):
    try:
        cid = int(company_id)
    except (ValueError, TypeError):
        return jsonify({"Error": "Invalid company ID", "Message": "ID must be an integer"}), 400
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            emails = await fetch_emails_sent(pool, cid)
        return jsonify(emails), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching sent emails for company {company_id}: {str(e)}")
        return jsonify({"Error": "Database error", "Message": str(e)}), 500
    except Exception as e:
        logger.error(f"Failed to fetch sent emails for company {company_id}: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

@app.route('/unsubscribe', methods=['GET', 'POST'])
async def unsubscribe():
    """
    Handle email unsubscribe requests.
    Supports GET (from email links) and POST (from API/frontend).
    """
    try:
        # 1. Get token based on request method
        if request.method == 'GET':
            token = request.args.get('token')
        else:
            data = await request.json
            token = data.get('token') if data else None

        logger.info("Requested token: %r, length: %r", token, len(token) if token else None)
        
        if not token:
            if request.method == 'GET':
                return "<h1>Error</h1><p>Unsubscribe token is missing.</p>", 400
            return jsonify({"success": False, "message": "Token is required"}), 400
        
        # 2. Perform unsubscribe
        try:
            parsed_token = uuid.UUID(token)
        except ValueError as e:
            logger.error("Invalid UUID: %r", str(e))
            return jsonify({"success": False, "message": "Invalid unsubscribe token"}), 400

        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            success = await unsubscribe_user(pool, parsed_token)
            
            if success:
                if request.method == 'GET':
                    return """
                        <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                            <h1>Unsubscribed</h1>
                            <p>You have been successfully unsubscribed from receiving outreach.</p>
                        </div>
                    """, 200
                return jsonify({
                    "success": True, 
                    "message": "You have been successfully unsubscribed"
                }), 200
            else:
                if request.method == 'GET':
                    return """
                        <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                            <h1>Error</h1>
                            <p>Invalid or expired unsubscribe token.</p>
                        </div>
                    """, 404
                return jsonify({
                    "success": False, 
                    "message": "Invalid or expired unsubscribe token"
                }), 404
                
    except Exception as e:
        logger.error(f"Unsubscribe error: {str(e)}")
        if request.method == 'GET':
            return "<h1>Error</h1><p>An unexpected error occurred. Please try again later.</p>", 500
        return jsonify({
            "success": False, 
            "message": "An error occurred"
        }), 500

@app.route('/save-note/<id>', methods=["POST"])
@requires_auth
async def save_note(id):
    try:
        data = await request.json
        if not data or 'note' not in data:
            return jsonify({"Error": "No note content provided"}), 400
        
        note_text = data.get('note')
        result = await add_company_note(int(id), note_text)
        
        if result:
            return jsonify(result), 201
        else:
            return jsonify({"Error": "Failed to save note"}), 500
    except Exception as e:
        logger.error(f"Error saving note: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/engagement-metrics', methods=["GET"])
@requires_auth
async def get_engagement_metrics():
    try:
        start_date = request.args.get('start_date')  # ISO string: YYYY-MM-DD
        end_date = request.args.get('end_date')        # ISO string: YYYY-MM-DD
        metrics = await fetch_engagement_metrics(start_date=start_date, end_date=end_date)
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Failed to fetch engagement metrics: {str(e)}")
        return jsonify({"Error": "Failed to fetch metrics", "Message": str(e)}), 500

@app.route('/mark-replied/<id>', methods=["POST"])
@requires_auth
async def mark_replied(id):
    try:
        data = await request.json
        is_replied = data.get('replied', True)
        success = await mark_lead_replied(int(id), is_replied)
        if success:
            return jsonify({"Success": "Marked as replied"}), 200
        else:
            return jsonify({"Error": "Failed to mark as replied"}), 500
    except Exception as e:
        logger.error(f"Error marking as replied: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/mark-positive/<id>', methods=["POST"])
@requires_auth
async def mark_positive(id):
    try:
        data = await request.json
        is_positive = data.get('positive', True)
        success = await mark_lead_positive(int(id), is_positive)
        if success:
            return jsonify({"Success": "Marked as positive"}), 200
        else:
            return jsonify({"Error": "Failed to mark as positive"}), 500
    except Exception as e:
        logger.error(f"Error marking as positive: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/delete-note/<note_id>', methods=["DELETE"])
@requires_auth
async def delete_note(note_id):
    try:
        success = await delete_company_note(note_id)
        if success:
            return jsonify({"Success": "Note deleted"}), 200
        else:
            return jsonify({"Error": "Failed to delete note"}), 500
    except Exception as e:
        logger.error(f"Error deleting note: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == "__main__":
    logger.info("Application running....")
    app.run(port=5050, debug=True)
    logger.info("Application Done")
