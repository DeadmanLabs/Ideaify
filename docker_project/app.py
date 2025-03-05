from flask import Flask, request
import os
import uuid

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

from idea_summarizer import process_idea, save_idea_to_obsidian

@app.route("/summarize", methods=["POST"])
def summarize():
    idea_text = request.json.get("idea_text")
    if not idea_text:
        return {"error": "Missing idea_text"}, 400
    
    try:
        # Process the idea using our simplified function
        idea = process_idea(idea_text)
        
        # Always save to Obsidian by default
        obsidian_path = None
        try:
            obsidian_path = save_idea_to_obsidian(idea)
        except Exception as e:
            # Log the error but continue with the response
            print(f"Warning: Failed to save to Obsidian: {str(e)}")

        # Return a more comprehensive response
        response = {
            "id": idea.id,
            "title": idea.title,
            "summary": idea.summary,
            "key_points": idea.key_points,
            "category": idea.category,
            "tech_stack": idea.tech_stack.to_dict(),
            "design_philosophy": idea.design_philosophy.to_dict(),
            "market_analysis": idea.market_analysis,
            "risks": idea.risks
        }
        
        # Add obsidian_path to response if available
        if obsidian_path:
            response["obsidian_path"] = obsidian_path
            
        return response, 200
        
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
