"""import os
import sqlite3
import re
import random
import nltk
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from pypdf import PdfReader
from nltk.corpus import stopwords
from fpdf import FPDF
from flask import send_file, session
import io

# NLTK Download (Sirf ek baar)
nltk.download('stopwords')

app = Flask(__name__)
app.secret_key = 'aura_hire_ai_master_key_2026'

# Path Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Setup
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    try:
        # Purani table mein 'timestamp' add karne ki koshish karega
        conn.execute('ALTER TABLE history ADD COLUMN timestamp TEXT')
        print("Column 'timestamp' added successfully!")
    except:
        # Agar column pehle se hai toh ignore karega
        pass
    
    # Baaki tables create karein
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT, filename TEXT, ats_score TEXT, 
                    git_score TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

# --- NLP Logic ---
def analyze_match(resume_path, jd_text):
    text = ""
    try:
        reader = PdfReader(resume_path)
        for page in reader.pages:
            text += page.extract_text()
    except: text = ""

    stop_words = set(stopwords.words('english'))
    custom_noise = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'have', 'been'}
    all_stop = stop_words.union(custom_noise)

    resume_words = {w.lower() for w in re.findall(r'\b\w{3,}\b', text) if w.lower() not in all_stop}
    jd_words = {w.lower() for w in re.findall(r'\b\w{3,}\b', jd_text) if w.lower() not in all_stop}

    matched = sorted(list(jd_words.intersection(resume_words)))
    missing = sorted(list(jd_words.difference(resume_words)))
    detected = sorted(list(resume_words))

    match_count = len(matched)
    total_jd = len(jd_words)
    raw_score = (match_count / total_jd * 100) if total_jd > 0 else 0
    final_score = round(90 + (raw_score * 0.09), 2) if raw_score > 0 else 0
    p_rank = round(80 + (match_count * 0.5), 1)
    if p_rank > 99: p_rank = 98.2

    tech_hits = [m for m in matched if len(m) > 4]
    questions = [f"How do you apply your knowledge of {m.upper()} in solving complex problems?" for m in tech_hits[:7]]
    while len(questions) < 10:
        questions.append("Describe a project where you demonstrated exceptional problem-solving skills.")

    return final_score, matched, missing, p_rank, questions, detected

@app.route('/')
def index():
    return redirect(url_for('login')) if 'user' not in session else redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u, p = request.form['username'], generate_password_hash(request.form['password'])
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
            conn.commit()
            return redirect(url_for('login'))
        except: flash("User already exists!")
    return render_template('signup.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        jd_input = request.form.get('jd', '')
        file = request.files.get('resume_pdf')
        
        if file and jd_input:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            
            # 1. Analysis Run karein
            score, matched, missing, p_rank, questions, detected = analyze_match(path, jd_input)
            
            # 2. Database mein Save karein (YAHAN LIKHNA HAI)
            conn = get_db()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute('''
                INSERT INTO history (user_id, filename, ats_score, git_score, timestamp) 
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user'], file.filename, f"{score}%", f"{p_rank}%", current_time))
            conn.commit()
            conn.close()

            # 3. Response bhejein
            ai_conf = round(98.8 + random.uniform(0.1, 0.7), 2)
            return jsonify({
                "score": f"{score}%",
                "status": "Shortlisted",
                "confidence": f"{ai_conf}%",
                "matched": matched,
                "unmatched": missing,
                "detected": detected,
                "questions": questions,
                "github": {"portfolio_score": p_rank}
            })
            
    return render_template('dashboard.html')


@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db()
    # Query mein ensure karo ki 'timestamp' hi likha ho
    rows = conn.execute('''SELECT filename, ats_score, git_score, timestamp as analysis_date 
                           FROM history WHERE user_id = ? ORDER BY id DESC''', 
                        (session['user'],)).fetchall()
    conn.close()
    return render_template('history.html', analyses=rows)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db()
    if request.method == 'POST':
        new_username = request.form.get('username')
        if new_username:
            conn.execute('UPDATE users SET username = ? WHERE username = ?', (new_username, session['user']))
            conn.execute('UPDATE history SET user_id = ? WHERE user_id = ?', (new_username, session['user']))
            conn.commit()
            session['user'] = new_username
            flash("Profile updated successfully!")
    user_data = conn.execute('SELECT * FROM users WHERE username = ?', (session['user'],)).fetchone()
    analysis_count = conn.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (session['user'],)).fetchone()[0]
    conn.close()
    return render_template('profile.html', user=user_data, count=analysis_count)

@app.route('/download_report', methods=['POST'])
def download_report():
    # 1. Frontend form se data nikalna
    score = request.form.get('score', '0')
    matching = request.form.get('matching_skills', 'N/A') # Variable name is 'matching'
    missing = request.form.get('missing_skills', 'N/A')   # Variable name is 'missing'

    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(0, 200, 255)
    pdf.cell(200, 20, txt="AuraHire AI Report", ln=True, align='C')
    
    # Candidate Name
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(200, 10, txt=f"Candidate: {session.get('user', 'User')}", ln=True, align='C')
    pdf.ln(10)

    # Score Box
    pdf.set_fill_color(230, 250, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 15, txt=f"Analysis Score: {score}", ln=True, align='L', fill=True)
    pdf.ln(10)

    # Matching Skills - YAHAN FIX KIYA HAI
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(190, 10, txt="Matched Skills:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 8, txt=str(matching)) # Pehle yahan matching_skills tha
    pdf.ln(5)

    # Missing Skills - YAHAN FIX KIYA HAI
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(190, 10, txt="Missing Skills:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 8, txt=str(missing)) # Pehle yahan missing_skills tha

    # Final Buffer Output
    response = make_response(pdf.output(dest='S').encode('latin-1', 'ignore'))
    response.headers.set('Content-Disposition', 'attachment', filename='AuraHire_Report.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()  # <--- Ye line yahan zaroori hai
    app.run(port=5000, debug=True)
    """


import os
import sqlite3
import re
import random
import torch
import numpy as np
import io
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from pypdf import PdfReader
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'aura_hire_ai_ultra_fast_2026'

# --- CONFIGURATIONS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- FAST AI ENGINE: DIRECT LOADING (To Fix NoneType Error) ---
device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

print(f"🚀 Initializing DistilBERT AI on {device}... Please wait.")
try:
    # DistilBERT is 60% faster than standard BERT
    tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
    model = AutoModel.from_pretrained('distilbert-base-uncased').to(device)
    model.eval() 
    print("✅ AI Engine Ready. Server Starting...")
except Exception as e:
    print(f"❌ Error loading AI Model: {e}")

def get_bert_embeddings(text):
    """Generates high-quality vectors for semantic matching"""
    if tokenizer is None or model is None:
        return None
    # Optimization: Only process first 512 tokens for speed
    inputs = tokenizer(text[:1024], return_tensors='pt', truncation=True, padding=True).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy()

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, fullname TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, filename TEXT, 
                    ats_score TEXT, git_score TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

# --- ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials!")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u, p = request.form.get('username'), generate_password_hash(request.form.get('password'))
        try:
            db = get_db()
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
            db.commit()
            db.close()
            return redirect(url_for('login'))
        except: flash("User already exists!")
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user' not in session: 
        return jsonify({"error": "Unauthorized"}), 401
    
    jd_text = request.form.get('jd')
    file = request.files.get('resume_pdf')

    if not file or not jd_text:
        return jsonify({"error": "Missing input data"}), 400

    try:
        # 1. Extraction
        filename = f"{session['user']}_{file.filename}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        reader = PdfReader(path)
        resume_text = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])

        # 2. Skill Mapping
        SKILLS_DB = ["Python", "Machine Learning", "Deep Learning", "Flask", "SQL", "React", "NLP", "TensorFlow", "AWS", "Docker", "Computer Vision", "YOLO", "BERT"]
        HIGH_IMPACT = ["YOLO", "BERT", "PyTorch", "Deployment", "FastAPI", "Cloud"]
        
        detected = [s for s in SKILLS_DB if s.lower() in resume_text.lower()]
        required = [s for s in SKILLS_DB if s.lower() in jd_text.lower()]
        matched = [s for s in detected if s in required]
        unmatched = [s for s in required if s not in detected]
        impact_boost = len([s for s in HIGH_IMPACT if s.lower() in resume_text.lower()])

        # 3. BERT Semantic Analysis
        res_vec = get_bert_embeddings(resume_text)
        jd_vec = get_bert_embeddings(jd_text)
        
        if res_vec is None or jd_vec is None:
            return jsonify({"error": "AI Engine is not ready"}), 500
            
        sim = float(cosine_similarity(res_vec, jd_vec)[0][0])
        
        # ATS Score Logic
        if not unmatched and required:
            ats_score = 100.0
        else:
            ats_score = round(70 + (sim * 28), 2)
            ats_score = min(99.4, ats_score)

        # Portfolio Rank Logic
        if not unmatched:
            p_rank = round(min(99.94, 98.6 + (impact_boost * 0.25) + (sim * 0.4)), 2)
        else:
            variety = (len(detected) / len(SKILLS_DB)) * 100
            p_rank = round((sim * 45) + (variety * 0.5), 2)

        ai_conf = round(99.3 + random.uniform(0.1, 0.4), 2) if ats_score == 100 else round(96.5 + (sim * 3), 2)

        # --- FIX: Define Questions and Roadmap properly ---
        
        # Generate dynamic questions based on matched skills
        generated_questions = [f"How have you implemented {s} in your previous projects?" for s in matched[:5]]
        
        # Add fallback questions if matched skills are fewer than 5
        fallbacks = [
            "Explain the most challenging technical hurdle you faced in your AI projects.",
            "How do you stay updated with the latest trends in Machine Learning?",
            "Describe your workflow for fine-tuning a pre-trained model like BERT or YOLO.",
            "How do you handle data preprocessing for inconsistent datasets?",
            "Tell us about a time you had to optimize code for better performance."
        ]
        
        for q in fallbacks:
            if len(generated_questions) >= 5: break
            generated_questions.append(q)

        # Roadmap Logic
        if not unmatched:
            roadmap = ["Elite Profile: Your skills align perfectly. Focus on System Design and Scalability."]
        else:
            roadmap = [f"Master {s} to bridge the gap with the job description." for s in unmatched[:3]]

        # 4. Database Save
        db = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        db.execute('INSERT INTO history (user_id, filename, ats_score, git_score, timestamp) VALUES (?,?,?,?,?)',
                   (session['user'], file.filename, f"{ats_score}%", f"{p_rank}%", now))
        db.commit()
        db.close()

        # 5. Final Response Object
        analysis_result = {
            "score": f"{ats_score}", # Number string for Chart.js
            "status": "Perfect Match" if ats_score == 100 else "Shortlisted",
            "confidence": f"{ai_conf}",
            "matched": matched,
            "detected": detected,
            "unmatched": unmatched,
            "roadmap": roadmap,
            "questions": generated_questions, # Correctly linked variable
            "github": {"portfolio_score": f"{p_rank}"}
        }
        
        # Store in session for the /insights page
        session['last_analysis'] = analysis_result
        session.modified = True

        return jsonify(analysis_result)

    except Exception as e:
        print(f"🔥 Server Error: {e}")
        return jsonify({"error": f"AI Error: {str(e)}"}), 500
    
@app.route('/history')
def history():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    rows = db.execute('SELECT filename, ats_score, git_score, timestamp as analysis_date FROM history WHERE user_id = ? ORDER BY id DESC', (session['user'],)).fetchall()
    db.close()
    return render_template('history.html', analyses=rows)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # User ki information (Aap yahan Database se bhi fetch kar sakte hain)
    user_data = {
        "name": session.get('user', 'Rana Aman'),
        "email": session.get('email', 'rana@example.com'), # Agar session mein save hai
        "role": "AI & ML Specialist",
        "university": "Chandigarh University",
        "skills": ["Python", "Flask", "YOLOv8", "NLP", "Computer Vision"]
    }
    return render_template('profile.html', user=user_data)

# Profile Update karne ka route (Optional)
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' in session:
        new_name = request.form.get('name')
        # Yahan database update logic aayega
        session['user'] = new_name
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/download_report', methods=['POST'])
def download_report():
    score = request.form.get('score', '0%')
    detected = request.form.get('detected_skills', 'N/A')
    matched = request.form.get('matching_skills', 'N/A')
    missing = request.form.get('missing_skills', '').strip()

    # Logic for "No missing words"
    if not missing or missing.lower() in ["none", "null", ""] or len(missing) < 2:
        missing_text = "PERFECT ALIGNMENT: No missing keywords identified for this role."
        m_color = (21, 128, 61) # Professional Green
    else:
        missing_text = missing
        m_color = (185, 28, 28) # Professional Red

    def safe_str(s):
        return str(s).encode('ascii', 'ignore').decode('ascii')

    # PDF Setup: Custom margins for 1-page fit
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False) # Manual control to keep it 1 page
    pdf.add_page()
    pdf.set_margins(15, 10, 15)
    
    # --- HEADER SECTION (Compact) ---
    pdf.set_fill_color(15, 23, 42) 
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_y(10)
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt="AURAHIRE AI | ANALYSIS REPORT", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, txt=f"CANDIDATE: {safe_str(session.get('user', 'User')).upper()} | DATE: {datetime.now().strftime('%d %b, %Y')}", ln=True, align='C')
    
    # --- SCORE BOX (Professional Blue) ---
    pdf.set_y(40)
    pdf.set_fill_color(240, 249, 255)
    pdf.set_draw_color(186, 230, 253)
    pdf.rect(15, 40, 180, 15, 'DF')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(180, 15, txt=f"ATS COMPATIBILITY SCORE: {safe_str(score)}", align='C', ln=True)
    
    pdf.ln(5)

    # --- 1. MATCHED SKILLS (Green) ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(21, 128, 61)
    pdf.cell(0, 8, txt="[V] MATCHED COMPETENCIES", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(40, 40, 40)
    # Line height kam rakhi hai (5) taaki space bache
    pdf.multi_cell(0, 5, txt=safe_str(matched))
    pdf.ln(4)

    # --- 2. DETECTED ENTITIES (Blue) ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 8, txt="[+] ALL DETECTED SKILLS & ENTITIES", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, txt=safe_str(detected))
    pdf.ln(4)

    # --- 3. MISSING SKILLS / NO MISSING (Red or Green) ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(*m_color)
    pdf.cell(0, 8, txt="[!] SKILL GAP ANALYSIS", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, txt=safe_str(missing_text))

    # --- FOOTER (Fixed at bottom of page) ---
    pdf.set_y(280)
    pdf.set_font("Arial", 'I', 7)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 5, txt="This is an AI-generated technical assessment. Verified by AuraHire Engineering Hub.", align='C')

    # Output
    pdf_out = pdf.output(dest='S').encode('latin-1', 'ignore')
    response = make_response(pdf_out)
    response.headers.set('Content-Disposition', 'attachment', filename=f"Report_{session.get('user')}.pdf")
    response.headers.set('Content-Type', 'application/pdf')
    return response

@app.route('/insights')
def insights():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Check if user has done any analysis in this session
    data = session.get('last_analysis')
    
    if not data:
        # Agar data nahi hai, toh user ko dashboard pe bhejo ek message ke saath
        flash("Please run an analysis first to see Deep Insights!")
        return redirect(url_for('dashboard'))
        
    return render_template('insights.html', data=data)
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(port=8080, debug=True)