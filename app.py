import os
# --- FIX 1: Allows Google login to work on your local computer (http) ---
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from google import genai 

app = Flask(__name__)

# --- SAFE CONFIG: Loading secrets from Environment Variables ---
# This prevents GitHub from blocking your upload
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "travel_secret_123")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "your-id-here")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "your-secret-here")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# --- 1. DATABASE CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vlog.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

# --- 2. DEFINE MODEL ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    filename = db.Column(db.String(100))
    desc = db.Column(db.Text)

with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- 3. GOOGLE OAUTH CONFIG ---
app.config["GOOGLE_OAUTH_CLIENT_ID"] = GOOGLE_CLIENT_ID
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = GOOGLE_CLIENT_SECRET

blueprint = make_google_blueprint(
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    offline=True
)
app.register_blueprint(blueprint, url_prefix="/login")

# --- 4. NEW AI CONFIG ---
# This safely uses the variable we set at the top
client = genai.Client(api_key=GEMINI_KEY)

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

@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get(id)
    if post and session.get('user'):
        try: 
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post.filename))
        except: 
            pass
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/chat', methods=['POST'])
def chat():
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
        print(f"DEBUG ERROR: {e}")
        return jsonify({"reply": "I'm refreshing my travel maps. Please try again in a moment!"})
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)