from flask import Flask, request, jsonify
import requests
import os
import logging
from responses import get_response
from datetime import datetime

# Initialize Flask app
app = Flask("A M Yusuf Official")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =======================
# Environment Variables
# =======================
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_token")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v24.0")

logger.info(f"Loaded config - Phone ID: {PHONE_NUMBER_ID}, API Version: {WHATSAPP_API_VERSION}")


# =======================
# Root Endpoint
# =======================
@app.route("/", methods=["GET", "HEAD"])
def index():
    """Health check endpoint for Render.com"""
    logger.info("Health check request received")
    return "✅ WhatsApp Chatbot is running!", 200


# =======================
# Webhook Verification (GET)
# =======================
@app.route("/webhook", methods=["GET"])
def verify():
    """
    Webhook verification endpoint.
    Meta sends: GET /webhook?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    logger.info(f"[VERIFY] Mode: {mode}, Challenge: {challenge}, Token received: {'Yes' if token else 'No'}")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ [VERIFY] WEBHOOK VERIFIED SUCCESSFULLY!")
        return challenge, 200
    else:
        logger.warning(f"❌ [VERIFY] Verification failed!")
        logger.warning(f"   Expected token: {VERIFY_TOKEN}")
        logger.warning(f"   Received token: {token}")
        return "Verification token mismatch", 403


# =======================
# Webhook Handler (POST)
# =======================
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive and process incoming WhatsApp messages.
    """
    data = request.get_json()
    
    logger.info(f"[WEBHOOK] Received POST request at {datetime.now()}")
    logger.debug(f"[WEBHOOK] Full payload: {str(data)[:500]}...")  # Log first 500 chars
    
    try:
        # Extract entry
        entry = data.get("entry", [])
        if not entry:
            logger.warning("[WEBHOOK] No 'entry' in payload")
            return jsonify(status="ok"), 200
        
        changes = entry[0].get("changes", [])
        if not changes:
            logger.warning("[WEBHOOK] No 'changes' in entry")
            return jsonify(status="ok"), 200
        
        value = changes[0].get("value", {})
        
        # Check for messages
        messages = value.get("messages", [])
        if messages:
            logger.info("[WEBHOOK] Processing message...")
            process_message(messages[0])
        else:
            # This might be a status update
            logger.info("[WEBHOOK] No messages - might be status/delivery update")
        
        return jsonify(status="ok"), 200
        
    except Exception as e:
        logger.error(f"[WEBHOOK] Error: {str(e)}", exc_info=True)
        return jsonify(status="error"), 500


# =======================
# Process Message
# =======================
def process_message(message):
    """
    Extract message details and send response.
    """
    try:
        # Extract fields
        text = message.get("text", {}).get("body", "").strip()
        from_number = message.get("from")
        message_id = message.get("id")
        
        logger.info(f"[MESSAGE] From: {from_number}, ID: {message_id}, Text: '{text[:50]}...'")
        
        if not text or not from_number:
            logger.warning(f"[MESSAGE] Missing text or phone number")
            return
        
        # Get response
        logger.info(f"[RESPONSE] Generating response...")
        reply = get_response(text)
        
        if not reply:
            reply = "Sorry, I couldn't process your message. Please try again."
            logger.warning(f"[RESPONSE] Empty response generated")
        else:
            logger.info(f"[RESPONSE] Generated: {reply[:100]}...")
        
        # Send reply
        logger.info(f"[SEND] Sending to {from_number}...")
        send_message(from_number, reply)
        
    except Exception as e:
        logger.error(f"[MESSAGE] Processing error: {str(e)}", exc_info=True)


# =======================
# Send Message via WhatsApp API
# =======================
def send_message(recipient_number, message_text):
    """
    Send message via WhatsApp Cloud API.
    """
    try:
        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        logger.info(f"[API] Sending to {recipient_number}...")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"[API] ✅ Message sent successfully!")
            return True
        else:
            logger.error(f"[API] ❌ Failed - Status {response.status_code}")
            logger.error(f"[API] Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"[API] ❌ Timeout sending to {recipient_number}")
        return False
    except Exception as e:
        logger.error(f"[API] ❌ Error: {str(e)}", exc_info=True)
        return False


# =======================
# Error Handlers
# =======================
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 - Not found: {request.path}")
    return jsonify(status="error", message="Not found"), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 - Server error: {str(error)}")
    return jsonify(status="error", message="Server error"), 500


# =======================
# App Startup
# =======================
if __name__ == "__main__":
    # Validate config
    if not TOKEN or not PHONE_NUMBER_ID:
        logger.error("❌ CRITICAL: Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID!")
        logger.error("   Set these in Render environment variables")
        exit(1)
    
    logger.info("=" * 60)
    logger.info("🚀 WhatsApp Chatbot Startup")
    logger.info("=" * 60)
    logger.info(f"✅ Phone Number ID: {PHONE_NUMBER_ID}")
    logger.info(f"✅ API Version: {WHATSAPP_API_VERSION}")
    logger.info(f"✅ Webhook URL: /webhook")
    logger.info("=" * 60)
    
    # Get port
    port = int(os.environ.get("PORT", 5000))
    
    logger.info(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)

