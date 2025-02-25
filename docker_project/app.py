from flask import Flask, request
import os

app = Flask(__name__)
DATA_DIR = "/data"

@app.route("/")
def index():
    return "Hello, Dockerized Python App!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    with open(os.path.join(DATA_DIR, "webhook.log"), "a") as f:
        f.write(str(data) + "\n")
    return "Webhook received", 200

from idea_summarizer import load_config, IdeaSummarizer
config = load_config()
summarizer = IdeaSummarizer(config)

@app.route("/summarize", methods=["POST"])
def summarize():
    idea_text = request.json.get("idea_text")
    if not idea_text:
        return {"error": "Missing idea_text"}, 400
    idea = summarizer.process_input("direct_text", text=idea_text)
    if idea:
        return {"title": idea.title, "summary": idea.summary}, 200
    else:
        return {"error": "Failed to process the idea."}, 500

@app.route("/voip", methods=["POST"])
def voip():
    data = request.get_json()
    action = data.get("action")
    number = data.get("number")
    if action not in ["call", "text"] or not number:
        return {"error": "Invalid parameters"}, 400
    if action == "call":
        result = "Calling " + number
    else:
        message = data.get("message", "")
        result = "Texting " + number + " with message: " + message
    return {"result": result}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
