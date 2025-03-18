from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv, dotenv_values
import google.generativeai as genai
import json
from pydantic import BaseModel
import os

# Load environment variables
load_dotenv()
config = dotenv_values(".env")
GEMINI_API_KEY = config.get("GEMINI_API_KEY")

# Initialize Google Gemini AI Client
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai.GenerativeModel("gemini-2.0-flash")
else:
    raise ValueError("GEMINI_API_KEY is missing in .env file")

# Initialize Flask app
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "../frontend"),
    static_folder=os.path.join(BASE_DIR, "../frontend"),
)

# Load disease data from JSON file
json_path = os.path.join(BASE_DIR, "diseases.json")
with open(json_path, encoding="utf-8") as f:
    diseases_data = json.load(f)

# Pydantic model for disease data validation
class Diagnosis(BaseModel):
    key_id: str
    primary_name: str
    consumer_name: str
    word_synonyms: str
    synonyms: list[str]
    info_link_data: list[list[str]]

    @app.route("/", methods=["GET", "POST"])
    def home():
        if request.method == "POST":
            symptom = request.form.get("symptom", "").strip().lower()
            if not symptom:
                return render_template("index.html", error="Please enter a symptom.")
            
            matches = []
            for disease in diseases_data:
                word_synonyms = disease.get("word_synonyms", "").lower().split(";")
                synonyms = disease.get("synonyms", [])
                if isinstance(synonyms, str):
                    synonyms = synonyms.split(",")
                
                if symptom in word_synonyms or any(symptom in syn.lower() for syn in synonyms):
                    matches.append(disease)
            
            return render_template("results.html", matches=matches, symptom=symptom)
        
        return render_template("index.html")

@app.route("/diseases", methods=["GET"])
def get_diseases():
    return jsonify(diseases_data)

@app.route("/disease/<disease_id>")
def disease_details(disease_id):
    disease = next((d for d in diseases_data if d["key_id"] == disease_id), None)
    return render_template("disease.html", disease=disease) if disease else "Not Found"

@app.route('/chat', methods=['GET'])
def get_chat():
 response = client.models.generate_content(
 model="gemini-2.0-flash",
 contents=[
 "You a disease diagnosing staff",
 "Create a basic diagnosis for a patient with the following symptoms: black skin spots, swelling, fever, vomiting, and headache.",
 "The patient have been experiencing the symptoms for a week already",
 "Provide an accurate diagnosis"
 ])

 return response.text

@app.route("/diagnosis", methods=["POST"])
def get_diagnosis():
    data = request.get_json()
    symptoms = data.get("symptoms", "").lower()
    
    response = client.generate_content(
        contents=[
            "This is the existing data in JSON format: " + json.dumps(diseases_data),
            "Match the closest disease with the following symptoms: " + symptoms,
            "Include the info_link_data in the response.",
            "Return the top three matching items."
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": list[Diagnosis]
        }
    )
    
    return json.loads(response.text) if response.text else jsonify({"error": "No diagnosis found"})

if __name__ == "__main__":
    app.run(debug=True)
