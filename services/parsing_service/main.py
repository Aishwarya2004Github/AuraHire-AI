import spacy
import fitz
from flask import Flask, request, jsonify
import re

app = Flask(__name__)
# Load NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def get_keywords(text):
    # Clean text: lowercase and remove special chars
    text = re.sub(r'[^\w\s]', '', text.lower())
    doc = nlp(text)
    # Filter: Nouns and Proper Nouns (Skills)
    keywords = {token.text for token in doc if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'] and len(token.text) > 2}
    return keywords

@app.route('/parse', methods=['POST'])
def parse():
    try:
        file = request.files['file']
        jd_text = request.form.get('jd', '').lower()
        
        # 1. Read PDF Text
        doc = fitz.open(stream=file.read(), filetype="pdf")
        resume_text = " ".join([page.get_text() for page in doc]).lower()
        
        if not resume_text.strip():
            return jsonify({"matched_keywords": [], "unmatched_keywords": ["Error: PDF is not readable"], "text": ""})

        # 2. Extract Keywords using NLP
        resume_keys = get_keywords(resume_text)
        jd_keys = get_keywords(jd_text)
        
        # 3. Intersection Logic
        matched = list(resume_keys.intersection(jd_keys))
        unmatched = list(jd_keys.difference(resume_keys))
        
        # Debugging print in terminal
        print(f"Extraction Successful! Matched: {len(matched)} words")

        return jsonify({
            "text": resume_text[:1000],
            "matched_keywords": matched[:15], # Sending top 15
            "unmatched_keywords": unmatched[:15]
        })
    except Exception as e:
        print(f"Parsing Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8001, debug=True)