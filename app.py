from flask import Flask, request, jsonify
import requests
import os
from responses import get_response  # your custom response logic

app = Flask("A M Yusuf Official")

# Environment variables
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_token")  # default fallback

# Root endpoint for testing
@app.route("/", methods=["GET"])
def index():
    return "✅ WhatsApp Chatbot is running!"

# Webhook verification
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK VERIFIED")
        return challenge, 200
    else:
        return "Verification token mismatch", 403

# Webhook to handle incoming WhatsApp messages
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = message["text"]["body"]
        from_number = message["from"]

        # Generate a reply using your responses.py logic
        reply = get_response(text)

        # Send reply via WhatsApp Cloud API
        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": from_number,
            "text": {"body": reply}
        }

        requests.post(url, headers=headers, json=payload)

    except Exception as e:
        print("Error handling message:", e)

    return jsonify(status="ok")

# Run app on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
