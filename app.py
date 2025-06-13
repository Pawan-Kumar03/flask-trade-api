from flask import Flask, request, jsonify
import uuid
import os
import base64
import time

app = Flask(__name__)

# Directory to store images temporarily
IMAGE_DIR = "chart_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Shared state
latest_prompt = None
latest_prompt_id = None
latest_trade_response = None  # Stores response from CustomGPT

@app.route("/trade_signal", methods=["POST"])
def receive_trade_signal():
    global latest_prompt, latest_prompt_id, latest_trade_response

    data = request.json
    print("\n🔵 [RECEIVED FROM NINJA] Raw JSON Data (excluding chart_image):")
    for key, value in data.items():
        if key != "chart_image":
            print(f"{key}: {value}")

    price = data.get("price")
    volume = data.get("volume")
    vwap = data.get("vwap")
    macro = data.get("macro")
    chart_base64 = data.get("chart_image")

    # Save chart image
    image_path = None
    if chart_base64:
        image_id = str(uuid.uuid4())
        image_path = os.path.join(IMAGE_DIR, f"{image_id}.png")
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(chart_base64))

    # Prepare prompt
    latest_prompt_id = str(uuid.uuid4())
    latest_prompt = {
        "id": latest_prompt_id,
        "text": f"""Trade Signal Data:
- Price: {price}
- Volume: {volume}
- VWAP: {vwap}
- Macro: {macro}
- Chart Image Path: {image_path if image_path else "No image provided"}"""
    }
    latest_trade_response = None  # Clear previous result

    print("\n📤 [PROMPT FOR GPT]")
    print(latest_prompt["text"])

    # ⏳ Wait for GPT to respond
    print("\n🕒 [WAITING FOR CUSTOMGPT TO RESPOND WITH SIGNAL]")

    wait_time = 30  # seconds
    interval = 1
    waited = 0
    while waited < wait_time:
        if latest_trade_response:
            print("\n✅ [RESPONSE RECEIVED FROM CUSTOMGPT]")
            print(latest_trade_response)
            return jsonify(latest_trade_response), 200
        time.sleep(interval)
        waited += interval

    print("❌ [TIMEOUT] No response from CustomGPT.")
    return jsonify({"error": "Timeout waiting for GPT response"}), 504

@app.route("/get-latest-prompt", methods=["GET"])
def get_latest_prompt():
    if latest_prompt is None:
        return jsonify({"message": "No prompt available"}), 404
    return jsonify(latest_prompt), 200

@app.route("/execute-trade", methods=["POST"])
def execute_trade():
    global latest_trade_response

    data = request.json
    print("\n🔵 [RECEIVED FROM GPT OR UI] Trade Execution Request:")
    print(data)

    entry_type = data.get("entry_type")
    entry_price = data.get("entry_price")
    stop_loss = data.get("stop_loss")
    target = data.get("target")

    if not all([entry_type, entry_price, stop_loss, target]):
        print("❌ Missing required fields in trade execution.")
        return jsonify({"error": "Missing required fields"}), 400

    # Store response
    latest_trade_response = {
        "entry_type": entry_type,
        "entry_price": float(entry_price),
        "stop_loss": float(stop_loss),
        "target": float(target)
    }

    print("\n✅ [TRADE SIGNAL RECEIVED FROM CUSTOMGPT]")
    print(latest_trade_response)

    return jsonify({"message": "Trade signal received successfully"}), 200

if __name__ == "__main__":
    app.run(port=5000)
