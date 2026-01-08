from flask import Flask, request, jsonify
import requests
import os
import logging
from responses import get_response  # your custom response logic

# Initialize Flask app
app = Flask("A M Yusuf Official")

# Configure logging for better debugging
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
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_token")  # default fallback

# API version - update to latest stable (currently v20.0)
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")

# =======================
# Root Endpoint (Health Check)
# =======================
@app.route("/", methods=["GET"])
def index():
    """
    Root endpoint to verify the chatbot is running.
    Useful for Render.com health checks.
    """
    return "✅ WhatsApp Chatbot is running!", 200


# =======================
# Webhook Verification (GET)
# =======================
@app.route("/webhook", methods=["GET"])
def verify():
    """
    Webhook verification endpoint.
    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must respond with the challenge token to verify ownership.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    logger.info(f"Verification request received - Mode: {mode}, Token: {'***' if token else 'None'}")
    
    # Check if mode is subscribe and token matches
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ WEBHOOK VERIFIED SUCCESSFULLY")
        return challenge, 200
    else:
        logger.warning(f"❌ Verification failed - Mode: {mode}, Token mismatch: {token != VERIFY_TOKEN}")
        return "Verification token mismatch", 403


# =======================
# Webhook Handler (POST)
# =======================
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Webhook handler to process incoming WhatsApp messages.
    Receives messages, generates responses, and sends them back via WhatsApp API.
    """
    data = request.json
    
    try:
        # Safely extract nested data structures
        entry = data.get("entry", [])
        if not entry:
            logger.warning("No 'entry' found in webhook payload")
            return jsonify(status="ok"), 200
        
        changes = entry[0].get("changes", [])
        if not changes:
            logger.warning("No 'changes' found in entry")
            return jsonify(status="ok"), 200
        
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        # If no messages, this might be a status update or other event
        if not messages:
            logger.info("Webhook event received (status update, delivery confirmation, etc.)")
            return jsonify(status="ok"), 200
        
        # Extract message details
        message = messages[0]
        text = message.get("text", {}).get("body", "").strip()
        from_number = message.get("from")
        message_id = message.get("id")
        
        # Validate required fields
        if not text:
            logger.warning(f"No text body found in message from {from_number}")
            return jsonify(status="ok"), 200
        
        if not from_number:
            logger.warning("No 'from' number found in message")
            return jsonify(status="ok"), 200
        
        logger.info(f"📨 Message received from {from_number}: {text}")
        
        # =======================
        # Generate AI Response
        # =======================
        reply = get_response(text)
        
        if not reply:
            logger.warning(f"No response generated for message: {text}")
            reply = "Sorry, I couldn't process your message. Please try again."
        
        logger.info(f"💬 Generated reply: {reply[:100]}...")  # Log first 100 chars
        
        # =======================
        # Send Reply via WhatsApp API
        # =======================
        send_whatsapp_message(from_number, reply)
        
    except KeyError as e:
        logger.error(f"❌ KeyError - Missing expected field: {str(e)}")
        logger.error(f"Webhook payload structure: {data}")
    except Exception as e:
        logger.error(f"❌ Unexpected error handling message: {str(e)}")
        logger.error(f"Full exception: {type(e).__name__}")
    
    # Always return 200 OK to acknowledge receipt
    return jsonify(status="ok"), 200


# =======================
# Helper Function: Send WhatsApp Message
# =======================
def send_whatsapp_message(recipient_number, message_text):
    """
    Send a text message via WhatsApp Cloud API.
    
    Args:
        recipient_number (str): WhatsApp phone number (with country code, no +)
        message_text (str): Message content to send
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Construct API endpoint
        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Prepare payload
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
        
        # Send the request
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # Check response status
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("messages", [{}])[0].get("id", "Unknown")
            logger.info(f"✅ Message sent successfully to {recipient_number} (ID: {message_id})")
            return True
        else:
            logger.error(f"❌ WhatsApp API Error - Status: {response.status_code}")
            logger.error(f"Error response: {response.text}")
            
            # Try to extract error details from response
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"API Error Details: {error_message}")
            except:
                pass
            
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Request timeout while sending message to {recipient_number}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection error while sending message to {recipient_number}")
        return False
    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
        return False


# =======================
# Error Handler
# =======================
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Error - Endpoint not found: {request.path}")
    return jsonify(status="error", message="Endpoint not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Error - Internal server error: {str(error)}")
    return jsonify(status="error", message="Internal server error"), 500


# =======================
# Application Startup
# =======================
if __name__ == "__main__":
    # Validate required environment variables
    if not TOKEN or not PHONE_NUMBER_ID:
        logger.error("❌ CRITICAL: Missing required environment variables!")
        logger.error("   - WHATSAPP_TOKEN: Required for API authentication")
        logger.error("   - PHONE_NUMBER_ID: Required to identify your WhatsApp Business account")
        logger.error("   Please set these in your Render environment variables.")
    else:
        logger.info("✅ Environment variables validated successfully")
    
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    logger.info(f"🚀 Starting WhatsApp Chatbot Server...")
    logger.info(f"   Running on http://0.0.0.0:{port}")
    logger.info(f"   Webhook endpoint: /webhook")
    logger.info(f"   Health check: /")
    logger.info(f"   WhatsApp API Version: {WHATSAPP_API_VERSION}")
    
    # Run Flask app
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False  # Always False in production
    )
