from flask import Flask, request, render_template, redirect, url_for, flash, session
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator
import textwrap
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# User model for login and registration
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

# Home route for login/registration
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('index.html')

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.", "danger")

    return render_template('login.html')

# Route for logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# Route for YouTube transcript and translation functionality
@app.route('/index')
def index():
    if 'user_id' not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    youtube_url = request.form.get('youtube_url')
    if not youtube_url:
        flash("Please provide a YouTube URL.", "danger")
        return redirect(url_for('index'))

    try:
        # Extract video ID from the URL
        video_id = youtube_url.split('v=')[1].split('&')[0]

        # Get transcript from YouTube
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Format transcript as text
        transcript_text = " ".join([entry['text'] for entry in transcript])

        if not transcript_text:
            flash("No transcript text found for this video.", "danger")
            return redirect(url_for('index'))

        return render_template('transcript.html', transcript_text=transcript_text, youtube_url=youtube_url)

    except Exception as e:
        flash(f"Error extracting transcript: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/translate_transcript', methods=['POST'])
def translate_transcript():
    transcript_text = request.form.get('transcript_text')
    selected_languages = request.form.getlist('languages')

    if not transcript_text:
        flash("Transcript text is missing.", "danger")
        return redirect(url_for('index'))

    if not selected_languages:
        flash("Please select at least one language for translation.", "danger")
        return redirect(url_for('get_transcript'))

    # Break transcript into smaller chunks to handle long texts
    chunks = textwrap.wrap(transcript_text, 500)  # Split the transcript into chunks of 500 characters

    translations = {}

    try:
        for lang_code in selected_languages:
            translated_chunks = []
            for chunk in chunks:
                # Translate each chunk to the selected language
                translated = GoogleTranslator(source='auto', target=lang_code).translate(chunk)
                translated_chunks.append(translated)

            # Join the translated chunks into one final translated text for the language
            translations[lang_code] = " ".join(translated_chunks)

        return render_template('translation_result.html', 
                               original_text=transcript_text, 
                               translations=translations)

    except Exception as e:
        flash(f"Error occurred during translation: {str(e)}", "danger")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
