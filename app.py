import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from google import genai 
from dotenv import load_dotenv

load_dotenv()

# Allows Google login to work on local computer (http)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

# --- SAFE CONFIG ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret-for-local")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# --- 1. DATABASE CONFIG ---
# Added 'check_same_thread' for better stability on free hosts
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vlog.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 2. DEFINE MODEL ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    filename = db.Column(db.String(100))
    desc = db.Column(db.Text)

# Create DB and Folders safely
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- 3. GOOGLE OAUTH CONFIG ---
blueprint = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    offline=True
)
app.register_blueprint(blueprint, url_prefix="/login")

# --- 4. AI CONFIG WITH SAFETY CHECK ---
# We only initialize the AI if the key is actually found
client = None
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"AI Initialization failed: {e}")

# --- 5. ROUTES ---
@app.route('/')
def home():
    if not session.get('user') and google.authorized:
        try:
            resp = google.get("/oauth2/v1/userinfo")
            if resp.ok: 
                session['user'] = resp.json()['email']
        except: 
            session.clear()
    
    all_posts = Post.query.all()
    return render_template('index.html', posts=all_posts)

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if file and session.get('user'):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_post = Post(
            title=request.form.get('title'), 
            filename=filename, 
            desc=request.form.get('desc')
        )
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/chat', methods=['POST'])
def chat():
    # If the AI isn't set up yet, return a friendly message instead of crashing
    if not client:
        return jsonify({"reply": "Vlogy is resting today. Please add an API key to wake me up!"})

    try:
        user_msg = request.json.get("message")
        all_posts = Post.query.all()
        posts_info = "\n".join([f"- {p.title}: {p.desc}" for p in all_posts])
        prompt = f"You are 'Vlogy', a travel assistant. Context:\n{posts_info}\nUser: {user_msg}"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": "I'm refreshing my travel maps. Please try again later!"})
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)