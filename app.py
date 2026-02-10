# ImageRecognizer/app.py
import os
import uuid
import json
import sqlite3
import re
import random
from collections import Counter
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
from flask import (
    Flask, request, render_template, jsonify, send_from_directory,
    send_file, flash, redirect, url_for, abort, session
)
from PIL import Image
# --- EXIF Fix ---
from PIL.ExifTags import TAGS, GPSTAGS
from ultralytics import YOLO
from ultralytics.engine.results import Results
from werkzeug.utils import secure_filename
from sklearn.cluster import KMeans
import numpy as np
import cv2
from io import BytesIO

# --- NEW: ReportLab Imports for PDF Generation ---
# This fixes the "NameError: name 'SimpleDocTemplate' is not defined"
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY

# --- IMPORTS FOR LOGIN, POSTGRESQL & MAIL ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message

# --- Import AI processors ---
from ai_provider import get_ai_analysis, get_ai_text_prompt, generate_prompt_from_image
from stability_processor import generate_image_from_prompt, generate_image_from_image
from imagga_processor import get_imagga_tags
import image_editor_processor
import groq_processor
import gemini_processor

# --- App Initialization & Configuration ---
app = Flask(__name__)

# --- Configuration ---
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'
app.config['GENERATED_FOLDER'] = 'static/generated'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['DB_PATH'] = 'analysis_history.db' # SQLite for history

# --- DATABASE & SECURITY CONFIG ---
app.config['SECRET_KEY'] = 'y5k+152=b@q!nmdw08ttn^@26jahml3ow0fb1n5tye19u)-e=5'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1122@localhost/image_suite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- EMAIL CONFIGURATION (GMAIL EXAMPLE) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@ai-image-analyzer.com'

# --- OBJECT INITIALIZATIONS ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
mail = Mail(app)

# Configure login manager
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' 

# --- Create directories ---
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

# --- AI Model Loading ---
print("[INFO] Loading YOLOv8 models...")
try:
    yolo_models = {
        'detection': YOLO('yolov8l.pt'),
        'segmentation': YOLO('yolov8l-seg.pt'),
    }
    print("[INFO] All YOLO models loaded successfully!")
except Exception as e:
    print(f"[ERROR] Could not load YOLO models: {e}")
    yolo_models = {}


# --- UPDATED USER MODEL ---
class User(db.Model, UserMixin):
    """User Model for PostgreSQL Database."""
    __tablename__ = 'user' 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # --- NEW FIELDS FOR OTP ---
    otp_secret = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """Hashes and sets the password."""
        if password:
            self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks the hashed password."""
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login callback to reload the user from session."""
    return db.session.get(User, int(user_id))


# --- Helper Functions (Unchanged) ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- SQLite Connection (Unchanged) ---
def get_db_connection():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    return conn

# --- Tag Normalization (Unchanged) ---
STOP_WORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
    'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
    'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
    'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
    'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
    'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
    'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'image',
    'photo', 'picture', 'shows', 'depicts', 'style', 'lighting', 'composition'
])
TAG_NORMALIZATION_MAP = {
    'automobile': 'car', 'vehicle': 'car', 'motorbike': 'motorcycle',
    'person': 'person', 'man': 'person', 'woman': 'person', 'child': 'person',
}

def extract_gemini_keywords(text_content: str, num_keywords=5) -> list:
    try:
        cleaned_text = re.sub(r'[^\w\s]', '', text_content.lower())
        words = [
            word for word in cleaned_text.split()
            if word not in STOP_WORDS and len(word) > 2
        ]
        common_tags = [word for word, count in Counter(words).most_common(num_keywords)]
        return common_tags
    except Exception as e:
        print(f"[ERROR] Could not extract Gemini keywords: {e}")
        return []

def normalize_and_merge_tags(tags_list: list[dict]) -> list[dict]:
    merged_tags = {}
    for tag in tags_list:
        try:
            name = tag['name'].lower().strip()
            name = TAG_NORMALIZATION_MAP.get(name, name)
            tag['name'] = name
            if name not in merged_tags:
                merged_tags[name] = tag
            else:
                existing_tag = merged_tags[name]
                new_conf = tag.get('confidence') or 0
                existing_conf = existing_tag.get('confidence') or 0
                if new_conf > existing_conf: merged_tags[name] = tag
                elif new_conf == existing_conf and tag['source'] == 'YOLO' and existing_tag['source'] != 'YOLO': merged_tags[name] = tag
        except Exception as e:
            print(f"[ERROR] Could not normalize tag: {tag} - {e}")
    return list(merged_tags.values())

# --- Database Initialization (For SQLite History DB) ---
def initialize_db():
    conn = get_db_connection()
    if conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS upload_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    predictions TEXT NOT NULL, -- Storing JSON as text
                    upload_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS image_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER NOT NULL,
                    tag_name TEXT NOT NULL,
                    source TEXT NOT NULL, -- e.g., 'YOLO', 'Gemini'
                    confidence REAL, -- Confidence score, if applicable
                    FOREIGN KEY (image_id) REFERENCES upload_history (id)
                        ON DELETE CASCADE -- Delete tags if image is deleted
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_name ON image_tags (tag_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_image_id ON image_tags (image_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON upload_history (user_id);")
        conn.close()
        print("[INFO] SQLite database and tables confirmed.")


# --- EXIF and GPS Helper Functions ---
def _convert_to_degrees(value):
    """Helper to convert GPS exif data to degrees."""
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)

def get_exif_data(image_path):
    """Extracts EXIF data, focusing on GPS."""
    exif_data = {}
    gps_info = {}
    friendly_message = None

    try:
        img = Image.open(image_path)
        info = img._getexif()

        if not info:
            friendly_message = "No EXIF data found. Image may have been scrubbed of metadata (e.g., by WhatsApp or Instagram)."
            return {"EXIF Data": {"Info": friendly_message}}

        # Standard EXIF data
        for tag, value in info.items():
            decoded_tag = TAGS.get(tag, tag)
            if decoded_tag in ["Make", "Model", "DateTime", "Software"]:
                exif_data[decoded_tag] = value

        # GPS Data
        gps_tag = 34853 # GPSInfo IFD Pointer
        if gps_tag not in info:
            friendly_message = "No location data found in this image."
        else:
            gps_data = {}
            # Use GPSTAGS, not TAGS, to decode the GPS sub-dictionary
            gps_ifd = info[gps_tag]
            for t in gps_ifd:
                sub_decoded = GPSTAGS.get(t, t)
                gps_data[sub_decoded] = gps_ifd[t]
            
            lat = gps_data.get('GPSLatitude')
            lat_ref = gps_data.get('GPSLatitudeRef')
            lon = gps_data.get('GPSLongitude')
            lon_ref = gps_data.get('GPSLongitudeRef')

            if lat and lat_ref and lon and lon_ref:
                lat_deg = _convert_to_degrees(lat)
                lon_deg = _convert_to_degrees(lon)
                
                if lat_ref in ['S', 's']: lat_deg = -lat_deg
                if lon_ref in ['W', 'w']: lon_deg = -lon_deg
                
                gps_info = {"latitude": lat_deg, "longitude": lon_deg}
            else:
                friendly_message = "EXIF data found, but it does not contain GPS coordinates."

    except Exception as e:
        print(f"[ERROR] Could not read EXIF data: {e}")
        friendly_message = "Could not read EXIF data. The file might be corrupted or in an unsupported format."

    # Compile the final metadata dictionary
    metadata_output = {}
    if exif_data:
        metadata_output["Device Info"] = exif_data
    
    if gps_info:
        metadata_output["gps_info"] = gps_info 
        metadata_output["Location"] = {"Status": "Coordinates Found!"}
    elif friendly_message:
        metadata_output["Location"] = {"Status": friendly_message}
        
    return metadata_output


# --- Palette Generator Function ---
def get_color_palette(image_path, num_colors=10, resize_dim=256):
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] Palette: Failed to read image file: {image_path}")
            return []

        height, width = image.shape[:2]
        if max(height, width) > resize_dim:
            if height > width:
                scale = resize_dim / height
                new_height = resize_dim
                new_width = int(width * scale)
            else:
                scale = resize_dim / width
                new_width = resize_dim
                new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            if image is None:
                 print(f"[ERROR] Palette: Failed to resize image: {image_path}")
                 return []
        
        image_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        pixels = image_lab.reshape((-1, 3))
        if pixels.shape[0] == 0:
             print(f"[ERROR] Palette: No pixels found after reshaping image: {image_path}")
             return []
        pixels = np.float32(pixels)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        attempts = 10
        compactness, labels, centers_lab = cv2.kmeans(pixels, num_colors, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)

        if centers_lab is None or len(centers_lab) == 0:
             print(f"[ERROR] Palette: K-Means failed to find centers for image: {image_path}")
             return []

        centers_lab_uint8 = np.uint8(centers_lab)
        centers_bgr_uint8 = cv2.cvtColor(centers_lab_uint8.reshape(-1, 1, 3), cv2.COLOR_LAB2BGR)
        bgr_palette = centers_bgr_uint8.reshape(-1, 3)

        # Return hex strings
        hex_palette = []
        for color in bgr_palette:
            b, g, r = color
            hex_code = f'#{int(r):02x}{int(g):02x}{int(b):02x}'
            hex_palette.append(hex_code)
        
        return hex_palette
        
    except Exception as e:
        print(f"[ERROR] Could not generate color palette for {image_path}: {e}")
        return []


# --- AUTHENTICATION & PUBLIC ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_type = request.form.get('login_type') # 'password' or 'otp'

        if login_type == 'password':
            # Regular Username/Password Login
            username_input = request.form.get('username')
            password_input = request.form.get('password')
            
            # Allow login by either username or email
            user = User.query.filter((User.username == username_input) | (User.email == username_input)).first()

            if user and user.check_password(password_input):
                login_user(user, remember=True)
                flash('Logged in successfully!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Login failed. Check username and password.', 'danger')
        
        elif login_type == 'otp':
            # OTP Email Login Step 1: Generate & Send Code
            email_input = request.form.get('email_otp')
            user = User.query.filter_by(email=email_input).first()
            
            if user:
                # Generate 6-digit OTP
                otp = str(random.randint(100000, 999999))
                expiry = datetime.utcnow() + timedelta(minutes=10)
                
                user.otp_secret = otp
                user.otp_expiry = expiry
                db.session.commit()
                
                # Send Email
                try:
                    msg = Message('Your Login OTP', recipients=[email_input])
                    msg.body = f"Your verification code is: {otp}\nIt expires in 10 minutes."
                    mail.send(msg)
                    
                    # Store ID in session for verification step
                    session['otp_user_id'] = user.id
                    flash('OTP sent to your email. Please verify.', 'info')
                    return redirect(url_for('verify_otp'))
                    
                except Exception as e:
                    print(f"Mail Error: {e}")
                    flash('Failed to send email. Check server logs.', 'danger')
            else:
                flash('No account found with that email.', 'danger')

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if 'otp_user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        user_id = session.get('otp_user_id')
        user = db.session.get(User, user_id)
        
        if user and user.otp_secret == entered_otp and user.otp_expiry > datetime.utcnow():
            # Success
            user.otp_secret = None
            user.otp_expiry = None
            db.session.commit()
            
            login_user(user, remember=True)
            session.pop('otp_user_id', None)
            flash('Logged in via OTP successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
            
    return render_template('verify_otp.html') 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Check if user or email already exists in DB
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        # 2. Generate OTP
        otp = str(random.randint(100000, 999999))
        expiry_str = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        # 3. Hash password NOW so we don't store plain text in session cookies
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # 4. Store details in Session temporarily
        session['register_data'] = {
            'username': username,
            'email': email,
            'pw_hash': pw_hash,
            'otp': otp,
            'expiry': expiry_str
        }

        # 5. Send Email
        try:
            msg = Message('Verify Registration', recipients=[email])
            msg.body = f"Welcome to AI Image Analyzer!\n\nYour registration verification code is: {otp}\n\nThis code expires in 10 minutes."
            mail.send(msg)
            
            flash('Verification code sent to your email. Please verify to complete registration.', 'info')
            return redirect(url_for('verify_registration'))
            
        except Exception as e:
            print(f"Mail Error: {e}")
            flash('Failed to send verification email. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/verify_registration', methods=['GET', 'POST'])
def verify_registration():
    # If no registration data in session, kick them back to start
    if 'register_data' not in session:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        reg_data = session['register_data']
        
        # 1. Check Expiry
        expiry = datetime.fromisoformat(reg_data['expiry'])
        if datetime.utcnow() > expiry:
            flash('OTP has expired. Please register again.', 'danger')
            session.pop('register_data', None) # Clear invalid data
            return redirect(url_for('register'))
            
        # 2. Check OTP Match
        if entered_otp == reg_data['otp']:
            # OTP Valid! Now we actually create the user in the DB
            try:
                # Create user with the pre-hashed password
                new_user = User(
                    username=reg_data['username'], 
                    email=reg_data['email'],
                    password_hash=reg_data['pw_hash'] # Use the hash we stored
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                # Cleanup session
                session.pop('register_data', None)
                
                flash('Account created successfully! You can now log in.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving user to database: {e}', 'danger')
                return redirect(url_for('register'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')

    return render_template('verify_register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """A new, protected homepage for logged-in users."""
    return render_template('dashboard.html')

# --- PROTECTED APPLICATION ROUTES ---

@app.route('/analyzer')
@login_required
def analyzer():
    return render_template('analyzer.html')

@app.route('/palette_generator')
@login_required
def palette_generator():
    return render_template('palette.html')

@app.route('/generate')
@login_required
def generate():
    return render_template('generate.html')

@app.route('/history')
@login_required
def history():
    search_query = request.args.get('search', '').strip()
    records = []
    conn = get_db_connection()
    if conn:
        try:
            # Always filter by current user
            params = [current_user.id]
            
            # --- Check for special search term ---
            if search_query.lower() == 'ai generated':
                base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h"
                base_query += " WHERE h.user_id = ? AND h.predictions LIKE '%\"source\": \"generation%' "
                base_query += " ORDER BY h.upload_timestamp DESC"
            
            # --- Existing tag search logic ---
            elif search_query:
                tags = [tag.strip().lower() for tag in search_query.split(',') if tag.strip()]
                if tags:
                    placeholders = ','.join('?' for _ in tags)
                    base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h"
                    base_query += f" WHERE h.user_id = ? AND h.id IN (SELECT t.image_id FROM image_tags t WHERE t.tag_name IN ({placeholders}) GROUP BY t.image_id HAVING COUNT(DISTINCT t.tag_name) = ?)"
                    params.extend(tags); params.append(len(tags))
                    base_query += " ORDER BY h.upload_timestamp DESC"
                else:
                    # Search was empty or just commas
                    base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h WHERE h.user_id = ? ORDER BY h.upload_timestamp DESC"
            
            # --- Default: No search ---
            else:
                base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h WHERE h.user_id = ? ORDER BY h.upload_timestamp DESC"


            cursor = conn.execute(base_query, params)
            for record_row in cursor.fetchall():
                record = dict(record_row)
                try:
                    record['predictions_json'] = json.loads(record['predictions'])
                    record['predictions_str'] = record['predictions']
                except (json.JSONDecodeError, TypeError):
                    record['predictions_json'] = {'error': 'Could not parse prediction data.'}
                    record['predictions_str'] = json.dumps({'error': 'Could not parse.'})
                ts_str = record.get('upload_timestamp')
                if ts_str: record['upload_timestamp'] = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')

                tag_cursor = conn.execute("SELECT tag_name, source FROM image_tags WHERE image_id = ? ORDER BY source, tag_name", (record['id'],))
                record['tags'] = tag_cursor.fetchall()
                records.append(record)
        except Exception as e: print(f"[ERROR] Failed to search history: {e}")
        finally: conn.close()
    return render_template('history.html', records=records, search_query=search_query)


# --- NEW: History Detail Page (Full View) ---
@app.route('/history/<int:record_id>')
@login_required
def history_detail(record_id):
    conn = get_db_connection()
    try:
        # Fetch the specific record for the current user
        cursor = conn.execute(
            "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h WHERE h.id = ? AND h.user_id = ?", 
            (record_id, current_user.id)
        )
        row = cursor.fetchone()
        
        if not row:
            flash('Record not found or access denied.', 'danger')
            return redirect(url_for('history'))
            
        record = dict(row)
        
        # Parse predictions
        try:
            record['predictions_json'] = json.loads(record['predictions'])
        except (json.JSONDecodeError, TypeError):
            record['predictions_json'] = {'error': 'Could not parse prediction data.'}
            
        # Parse timestamp
        ts_str = record.get('upload_timestamp')
        if ts_str: 
            record['upload_timestamp'] = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            
        # Fetch tags
        tag_cursor = conn.execute("SELECT tag_name, source, confidence FROM image_tags WHERE image_id = ? ORDER BY source, tag_name", (record['id'],))
        record['tags'] = tag_cursor.fetchall()
        
        return render_template('history_detail.html', item=record)
        
    except Exception as e:
        print(f"[ERROR] Failed to load history detail: {e}")
        flash('An error occurred while loading details.', 'danger')
        return redirect(url_for('history'))
    finally:
        conn.close()


# --- NEW: Delete History Item Route ---
@app.route('/history/delete', methods=['POST'])
@login_required
def delete_history_item():
    data = request.get_json()
    record_id = data.get('id')
    
    if not record_id:
        return jsonify({'error': 'Missing ID'}), 400
        
    conn = get_db_connection()
    try:
        # Verify ownership
        record = conn.execute("SELECT id FROM upload_history WHERE id = ? AND user_id = ?", (record_id, current_user.id)).fetchone()
        if not record:
            return jsonify({'error': 'Record not found or access denied'}), 404
            
        # Delete related tags first (foreign key might cascade, but being safe)
        conn.execute("DELETE FROM image_tags WHERE image_id = ?", (record_id,))
        
        # Delete history record
        conn.execute("DELETE FROM upload_history WHERE id = ?", (record_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Deleting history item: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# --- Bulk Delete History Items Route ---
@app.route('/delete_history_bulk', methods=['POST'])
@login_required
def delete_history_bulk():
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'error': 'No items selected'}), 400
    
    conn = get_db_connection()
    deleted = 0
    try:
        for record_id in ids:
            # Verify ownership and get filename
            record = conn.execute(
                "SELECT id, filename FROM upload_history WHERE id = ? AND user_id = ?", 
                (record_id, current_user.id)
            ).fetchone()
            
            if record:
                # Delete file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], record['filename'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Delete from generated folder too
                gen_path = os.path.join(app.config['GENERATED_FOLDER'], record['filename'])
                if os.path.exists(gen_path):
                    os.remove(gen_path)
                
                # Delete tags and record
                conn.execute("DELETE FROM image_tags WHERE image_id = ?", (record_id,))
                conn.execute("DELETE FROM upload_history WHERE id = ?", (record_id,))
                deleted += 1
        
        conn.commit()
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        print(f"[ERROR] Bulk delete: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()



# --- NEW: PDF Download Route ---
@app.route('/history/download_pdf/<int:record_id>')
@login_required
def download_pdf(record_id):
    conn = get_db_connection()
    # Only allow download if record belongs to current user
    record = conn.execute("SELECT * FROM upload_history WHERE id = ? AND user_id = ?", (record_id, current_user.id)).fetchone()
    
    if not record:
        conn.close()
        flash('Record not found.', 'danger')
        return redirect(url_for('history'))

    # Fetch Tags
    tags_cursor = conn.execute("SELECT tag_name, confidence FROM image_tags WHERE image_id = ?", (record_id,))
    tags = tags_cursor.fetchall()
    conn.close()

    # Parse Data
    filename = record['filename']
    predictions = json.loads(record['predictions'])
    timestamp = record['upload_timestamp']
    
    # Determine Main Image Path
    is_generated = 'generation' in predictions.get('source', '')
    folder = app.config['GENERATED_FOLDER'] if is_generated else app.config['UPLOAD_FOLDER']
    image_path = os.path.join(folder, filename)

    # --- PDF Helper: Add Image ---
    def add_image_to_story(path, max_w, max_h, story_list):
        if os.path.exists(path):
            try:
                img = RLImage(path)
                img_width = img.drawWidth
                img_height = img.drawHeight
                
                if img_width > max_w:
                    scale = max_w / img_width
                    img_width = max_w
                    img_height = img_height * scale
                
                if img_height > max_h:
                    scale = max_h / img_height
                    img_height = max_h
                    img_width = img_width * scale
                    
                img.drawHeight = img_height
                img.drawWidth = img_width
                story_list.append(img)
            except Exception as e:
                story_list.append(Paragraph(f"[Image Error: {e}]", styles['Normal']))

    # --- PDF Generation ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='WrapBold', parent=styles['Normal'], fontSize=10, leading=12))
    
    story = []

    # 1. Title
    story.append(Paragraph(f"Analysis Report", styles['Title']))
    story.append(Paragraph(f"File: {filename}", styles['Heading3']))
    story.append(Paragraph(f"Date: {timestamp}", styles['Normal']))
    story.append(Spacer(1, 12))

    # 2. Main Image
    add_image_to_story(image_path, 6*inch, 5*inch, story)
    story.append(Spacer(1, 12))

    # 3. Generated Image Details (Reference Image & Prompts)
    if is_generated:
        story.append(Paragraph("Generation Details", styles['Heading2']))
        
        # Display Prompt
        if 'prompt' in predictions:
             story.append(Paragraph(f"<b>Prompt:</b> {predictions['prompt']}", styles['Normal']))
             story.append(Spacer(1, 6))
        
        if 'style_used' in predictions:
             story.append(Paragraph(f"<b>Style:</b> {predictions['style_used']}", styles['Normal']))
             story.append(Spacer(1, 6))

        # Display Reference Image if available
        if 'init_image_url' in predictions:
            ref_url = predictions['init_image_url']
            ref_filename = ref_url.split('/')[-1]
            ref_path = os.path.join(app.config['UPLOAD_FOLDER'], ref_filename)
            
            if os.path.exists(ref_path):
                story.append(Spacer(1, 12))
                story.append(Paragraph("Reference/Source Image:", styles['Heading4']))
                add_image_to_story(ref_path, 4*inch, 3*inch, story)
                story.append(Spacer(1, 12))

    # 4. Gemini Analysis (Updated for new data format)
    if 'gemini' in predictions:
        gemini = predictions['gemini']
        story.append(Paragraph("AI Analysis", styles['Heading2']))
        
        # Caption
        if gemini.get('caption'):
            story.append(Paragraph("<b>✨ Caption:</b>", styles['Heading4']))
            story.append(Paragraph(gemini['caption'], styles['Normal']))
            story.append(Spacer(1, 6))

        # Overview/Summary (new format: overview, fallback: summary)
        overview_text = gemini.get('overview') or gemini.get('summary') or ''
        if overview_text:
            story.append(Paragraph("<b>📸 Overview:</b>", styles['Heading4']))
            overview_text = overview_text.replace('**', '').replace('\n', '<br/>')
            story.append(Paragraph(overview_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Key Details (new format: details)
        details_text = gemini.get('details') or ''
        if details_text:
            story.append(Paragraph("<b>🔍 Key Details:</b>", styles['Heading4']))
            details_text = details_text.replace('**', '').replace('\n', '<br/>')
            story.append(Paragraph(details_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Comprehensive Analysis (new format: comprehensive, fallback: detailed_prompt)
        comprehensive_text = gemini.get('comprehensive') or gemini.get('detailed_prompt') or ''
        if comprehensive_text:
            story.append(Paragraph("<b>📝 Detailed Analysis:</b>", styles['Heading4']))
            comprehensive_text = comprehensive_text.replace('**', '').replace('\n', '<br/>')
            story.append(Paragraph(comprehensive_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Visual Style (new format)
        style_text = gemini.get('style') or ''
        if style_text:
            story.append(Paragraph("<b>🎨 Visual Style:</b>", styles['Heading4']))
            style_text = style_text.replace('**', '').replace('\n', '<br/>')
            story.append(Paragraph(style_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Social Media Post (new format)
        social_text = gemini.get('social_post') or ''
        if social_text:
            story.append(Paragraph("<b>📱 Social Media Post:</b>", styles['Heading4']))
            story.append(Paragraph(social_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Fun Fact / Did You Notice (new format: fun_fact, fallback: hidden_details)
        fun_fact_text = gemini.get('fun_fact') or gemini.get('hidden_details') or ''
        if fun_fact_text and fun_fact_text != 'No specific hidden details noted.':
            story.append(Paragraph("<b>💡 Did You Notice?</b>", styles['Heading4']))
            fun_fact_text = fun_fact_text.replace('**', '').replace('\n', '<br/>')
            story.append(Paragraph(fun_fact_text, styles['Normal']))
            story.append(Spacer(1, 6))
        
        # SD Recreation Prompts (new format)
        sd_prompts_text = gemini.get('sd_prompts') or ''
        if sd_prompts_text:
            story.append(Paragraph("<b>🎭 Recreation Prompts:</b>", styles['Heading4']))
            story.append(Paragraph(sd_prompts_text, styles['Normal']))
            story.append(Spacer(1, 6))

    # 4.5 AI Visual Analytics (NEW SECTION)
    if 'ai_analytics' in predictions and predictions['ai_analytics']:
        analytics = predictions['ai_analytics']
        story.append(Paragraph("📊 AI Visual Analytics", styles['Heading2']))
        
        # Key Insights Summary
        key_insights = analytics.get('key_insights', {})
        if key_insights:
            insights_text = []
            if key_insights.get('overall_score'):
                insights_text.append(f"<b>Quality Score:</b> {key_insights['overall_score']}%")
            if key_insights.get('resolution_quality'):
                insights_text.append(f"<b>Resolution:</b> {key_insights['resolution_quality']}")
            if key_insights.get('mood_summary'):
                mood_emoji = key_insights.get('mood_emoji', '🎭')
                insights_text.append(f"<b>Mood:</b> {mood_emoji} {key_insights['mood_summary']}")
            if key_insights.get('style_category'):
                insights_text.append(f"<b>Style:</b> {key_insights['style_category']}")
            
            if insights_text:
                story.append(Paragraph("<b>Key Insights:</b>", styles['Heading4']))
                story.append(Paragraph(" | ".join(insights_text), styles['Normal']))
                story.append(Spacer(1, 8))
        
        # Content Detection Table
        content_detection = analytics.get('content_detection', [])
        if content_detection:
            story.append(Paragraph("<b>Content Detection:</b>", styles['Heading4']))
            data = [['Element', 'Detection %']]
            for item in content_detection:
                label = item.get('label', 'Unknown')
                percentage = item.get('percentage', 0)
                data.append([label, f"{percentage}%"])
            
            t = Table(data, colWidths=[3*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        
        # Quality Metrics Table
        quality_metrics = analytics.get('quality_metrics', [])
        if quality_metrics:
            story.append(Paragraph("<b>Quality Metrics:</b>", styles['Heading4']))
            data = [['Metric', 'Score']]
            for item in quality_metrics:
                name = item.get('name', 'Unknown')
                score = item.get('score', 0)
                data.append([name, f"{score}/100"])
            
            t = Table(data, colWidths=[3*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22C55E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        
        # Mood Analysis Table
        mood_analysis = analytics.get('mood_analysis', [])
        if mood_analysis:
            story.append(Paragraph("<b>Mood Analysis:</b>", styles['Heading4']))
            data = [['Emotion', 'Intensity']]
            for item in mood_analysis:
                emotion = item.get('emotion', 'Unknown')
                intensity = item.get('intensity', 0)
                data.append([emotion, f"{intensity}%"])
            
            t = Table(data, colWidths=[3*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A855F7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        
        # Technical Metrics Table
        technical_metrics = analytics.get('technical_metrics', [])
        if technical_metrics:
            story.append(Paragraph("<b>Technical Metrics:</b>", styles['Heading4']))
            data = [['Metric', 'Value']]
            for item in technical_metrics:
                name = item.get('name', 'Unknown')
                value = item.get('value', 0)
                data.append([name, f"{value}/100"])
            
            t = Table(data, colWidths=[3*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F97316')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

    # 5. YOLO Analysis (Objects & Segmentation)
    if 'yolo' in predictions:
        for task, result in predictions['yolo'].items():
            story.append(Paragraph(f"Object Analysis: {task.capitalize()}", styles['Heading2']))
            
            # Annotated Image
            if 'processed_image_url' in result:
                proc_filename = result['processed_image_url'].split('/')[-1]
                proc_path = os.path.join(app.config['PROCESSED_FOLDER'], proc_filename)
                story.append(Paragraph("Annotated Result:", styles['Heading4']))
                add_image_to_story(proc_path, 5*inch, 4*inch, story)
                story.append(Spacer(1, 6))

            # Segmentation Plot
            if 'plot_url' in result:
                plot_filename = result['plot_url'].split('/')[-1]
                plot_path = os.path.join(app.config['PROCESSED_FOLDER'], plot_filename)
                story.append(Paragraph("Segmentation Plot:", styles['Heading4']))
                add_image_to_story(plot_path, 5*inch, 4*inch, story)
                story.append(Spacer(1, 6))
            
            # Counts Table
            if 'detection_counts' in result and result['detection_counts']:
                story.append(Paragraph("Detected Objects:", styles['Heading4']))
                data = [['Object Class', 'Count']]
                for label, count in result['detection_counts'].items():
                    data.append([label, str(count)])
                
                t = Table(data, colWidths=[3*inch, 1.5*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ]))
                story.append(t)
                story.append(Spacer(1, 12))

    # 6. Tags
    if tags:
        story.append(Paragraph("🏷️ Detected Tags", styles['Heading2']))
        tag_list = [f"{t['tag_name']} ({t['confidence'] if t['confidence'] else 'AI'})" for t in tags]
        story.append(Paragraph(", ".join(tag_list), styles['Normal']))
        story.append(Spacer(1, 12))
    
    # 6.5 Imagga Tags (if available with confidence scores)
    if 'imagga' in predictions and predictions['imagga']:
        imagga_tags = predictions['imagga']
        if isinstance(imagga_tags, list) and len(imagga_tags) > 0:
            story.append(Paragraph("📸 AI Tagging (Imagga)", styles['Heading2']))
            data = [['Tag', 'Confidence']]
            for tag in imagga_tags:
                name = tag.get('name', 'Unknown')
                confidence = tag.get('confidence', 0)
                data.append([name, f"{confidence:.1f}%"])
            
            t = Table(data, colWidths=[3*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EC4899')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

    # 7. Metadata Table
    if 'metadata' in predictions and predictions['metadata']:
        story.append(Paragraph("Metadata", styles['Heading2']))
        data = [['Property', 'Value']]
        for section, values in predictions['metadata'].items():
            if isinstance(values, dict):
                for k, v in values.items():
                    data.append([Paragraph(f"<b>{section} - {k}</b>", styles['WrapBold']), Paragraph(str(v), styles['WrapBold'])])
        
        if len(data) > 1:
            t = Table(data, colWidths=[2.5*inch, 3.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

    # 8. OCR Text
    if 'ocr' in predictions and predictions['ocr'].get('extracted_text'):
        story.append(Paragraph("Extracted Text (OCR)", styles['Heading2']))
        
        # --- NEW: Add Annotated Image ---
        if predictions['ocr'].get('annotated_image_url'):
            ocr_img_url = predictions['ocr']['annotated_image_url']
            # Convert URL to local path: /processed/filename -> app.config['PROCESSED_FOLDER']/filename
            ocr_img_filename = ocr_img_url.split('/')[-1]
            ocr_img_path = os.path.join(app.config['PROCESSED_FOLDER'], ocr_img_filename)
            
            story.append(Paragraph("Annotated Result:", styles['Heading4']))
            add_image_to_story(ocr_img_path, 6*inch, 5*inch, story)
            story.append(Spacer(1, 6))

        # OCR Stats
        ocr_data = predictions['ocr']
        stats_parts = []
        if ocr_data.get('detection_count') is not None:
            stats_parts.append(f"<b>Detections:</b> {ocr_data['detection_count']}")
        if ocr_data.get('time_taken') is not None:
            stats_parts.append(f"<b>Time:</b> {ocr_data['time_taken']}s")
        if ocr_data.get('provider'):
            stats_parts.append(f"<b>Provider:</b> {ocr_data['provider'].capitalize()}")
        
        if stats_parts:
            story.append(Paragraph(" | ".join(stats_parts), styles['Normal']))
            story.append(Spacer(1, 6))
        
        # OCR Text
        ocr_text = ocr_data['extracted_text'].replace('\n', '<br/>')
        story.append(Paragraph(ocr_text, styles['Normal']))
        story.append(Spacer(1, 12))
    
    # 9. Q&A Conversations
    if 'qa_history' in predictions and predictions['qa_history']:
        story.append(Paragraph("Follow-up Questions & Answers", styles['Heading2']))
        for i, qa in enumerate(predictions['qa_history'], 1):
            story.append(Paragraph(f"<b>Q{i}: {qa.get('question', 'N/A')}</b>", styles['Normal']))
            answer = qa.get('answer', 'No answer').replace('**', '').replace('*', '').replace('\n', '<br/>')
            story.append(Paragraph(f"A: {answer}", styles['Normal']))
            story.append(Spacer(1, 8))

    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"Report_{filename}.pdf", mimetype='application/pdf')


# --- NEW: Add Custom Tag Route ---
@app.route('/add_custom_tag', methods=['POST'])
@login_required
def add_tag_from_analyzer():
    """Add a custom tag from the analyzer page using filename."""
    data = request.get_json()
    filename = data.get('filename', '').strip()
    tag_name = data.get('tag', '').strip().lower()
    
    if not filename or not tag_name:
        return jsonify({'success': False, 'error': 'Missing filename or tag'}), 400
    
    # Validate tag name (alphanumeric, spaces, hyphens only)
    if not re.match(r'^[a-z0-9\s\-]+$', tag_name):
        return jsonify({'success': False, 'error': 'Invalid tag name. Use only letters, numbers, spaces, and hyphens.'}), 400
    
    if len(tag_name) > 30:
        return jsonify({'success': False, 'error': 'Tag name too long (max 30 characters).'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500
    
    try:
        # Find the history record by filename for the current user
        record = conn.execute(
            "SELECT id FROM upload_history WHERE filename = ? AND user_id = ?", 
            (filename, current_user.id)
        ).fetchone()
        
        if not record:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        history_id = record['id']
        
        # Check if tag already exists for this image
        existing = conn.execute(
            "SELECT id FROM image_tags WHERE image_id = ? AND tag_name = ?",
            (history_id, tag_name)
        ).fetchone()
        
        if existing:
            return jsonify({'success': True, 'message': 'Tag already exists', 'tag_name': tag_name})
        
        # Insert the new tag
        conn.execute(
            "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
            (history_id, tag_name, 'user', None)
        )
        conn.commit()
        
        return jsonify({'success': True, 'tag_name': tag_name})
    except Exception as e:
        print(f"[ERROR] Failed to add custom tag from analyzer: {e}")
        return jsonify({'success': False, 'error': 'Failed to add tag'}), 500
    finally:
        conn.close()


@app.route('/history/add_tag', methods=['POST'])
@login_required
def add_custom_tag():
    """Add a custom tag to an image in the user's history."""
    data = request.get_json()
    history_id = data.get('history_id')
    tag_name = data.get('tag_name', '').strip().lower()
    
    if not history_id or not tag_name:
        return jsonify({'success': False, 'error': 'Missing history_id or tag_name'}), 400
    
    # Validate tag name (alphanumeric, spaces, hyphens only)
    if not re.match(r'^[a-z0-9\s\-]+$', tag_name):
        return jsonify({'success': False, 'error': 'Invalid tag name. Use only letters, numbers, spaces, and hyphens.'}), 400
    
    if len(tag_name) > 30:
        return jsonify({'success': False, 'error': 'Tag name too long (max 30 characters).'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500
    
    try:
        # Verify the record belongs to the current user
        record = conn.execute(
            "SELECT id FROM upload_history WHERE id = ? AND user_id = ?", 
            (history_id, current_user.id)
        ).fetchone()
        
        if not record:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        # Check if tag already exists for this image
        existing = conn.execute(
            "SELECT id FROM image_tags WHERE image_id = ? AND tag_name = ?",
            (history_id, tag_name)
        ).fetchone()
        
        if existing:
            return jsonify({'success': False, 'error': 'Tag already exists'}), 400
        
        # Insert the new tag
        conn.execute(
            "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
            (history_id, tag_name, 'user', None)
        )
        conn.commit()
        
        return jsonify({'success': True, 'tag_name': tag_name})
    except Exception as e:
        print(f"[ERROR] Failed to add custom tag: {e}")
        return jsonify({'success': False, 'error': 'Failed to add tag'}), 500
    finally:
        conn.close()


@app.route('/get_custom_tags/<filename>', methods=['GET'])
@login_required
def get_custom_tags(filename):
    """Fetch all custom tags for an image by filename."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Find the history record by filename for the current user
        record = conn.execute(
            "SELECT id FROM upload_history WHERE filename = ? AND user_id = ?", 
            (filename, current_user.id)
        ).fetchone()
        
        if not record:
            return jsonify({'custom_tags': []})
        
        history_id = record['id']
        
        # Get all tags for this image where source is 'user' (custom tags)
        tags = conn.execute(
            "SELECT tag_name FROM image_tags WHERE image_id = ? AND source = 'user'",
            (history_id,)
        ).fetchall()
        
        tag_names = [tag['tag_name'] for tag in tags]
        
        return jsonify({'custom_tags': tag_names})
    except Exception as e:
        print(f"[ERROR] Failed to get custom tags: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# --- ADMIN PANEL ROUTES ---
@app.route('/admin')
@login_required
def admin_panel():
    # Secure this route to only admins
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Fetch all users for the admin to see
    all_users = User.query.order_by(User.created_at.desc()).all()
    
    # Fetch stats from the SQLite DB
    conn = get_db_connection()
    total_analyses = 0
    recent_activity = []
    
    if conn:
        try:
            total_analyses = conn.execute("SELECT COUNT(id) FROM upload_history").fetchone()[0]
            
            # Fetch last 5 analyses for activity feed
            recent_rows = conn.execute("""
                SELECT filename, user_id, uploaded_at 
                FROM upload_history 
                ORDER BY uploaded_at DESC 
                LIMIT 5
            """).fetchall()
            
            for row in recent_rows:
                user = User.query.get(row['user_id'])
                recent_activity.append({
                    'filename': row['filename'],
                    'username': user.username if user else 'Unknown',
                    'uploaded_at': row['uploaded_at']
                })
        except Exception as e:
            print(f"Admin panel couldn't get stats: {e}")
        finally:
            conn.close()
    
    # Calculate storage usage (uploads folder)
    storage_mb = 0
    try:
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        if os.path.exists(upload_folder):
            total_size = sum(
                os.path.getsize(os.path.join(upload_folder, f))
                for f in os.listdir(upload_folder)
                if os.path.isfile(os.path.join(upload_folder, f))
            )
            storage_mb = round(total_size / (1024 * 1024), 2)
    except Exception as e:
        print(f"Admin panel couldn't calculate storage: {e}")

    return render_template('admin.html', 
        all_users=all_users, 
        total_analyses=total_analyses,
        storage_mb=storage_mb,
        recent_activity=recent_activity
    )

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Promotes a user to admin or demotes an admin to user."""
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash("You cannot change your own admin status.", 'danger')
        return redirect(url_for('admin_panel'))
        
    user_to_toggle = db.get_or_404(User, user_id)
    user_to_toggle.is_admin = not user_to_toggle.is_admin
    db.session.commit()
    
    action = "promoted" if user_to_toggle.is_admin else "demoted"
    flash(f"User {user_to_toggle.username} has been {action}.", 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Deletes a user from the database."""
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('dashboard'))

    if user_id == current_user.id:
        flash("You cannot delete your own account from the admin panel.", 'danger')
        return redirect(url_for('admin_panel'))
        
    user_to_delete = db.get_or_404(User, user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f"User {user_to_delete.username} has been permanently deleted.", 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/bulk_toggle_admin', methods=['POST'])
@login_required
def bulk_toggle_admin():
    """Toggle admin status for multiple users."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'success': False, 'error': 'No users selected'}), 400
    
    toggled = 0
    for uid in user_ids:
        if uid == current_user.id:
            continue  # Skip self
        user = User.query.get(uid)
        if user:
            user.is_admin = not user.is_admin
            toggled += 1
    
    db.session.commit()
    return jsonify({'success': True, 'toggled': toggled})

@app.route('/admin/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    """Delete multiple users."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'success': False, 'error': 'No users selected'}), 400
    
    deleted = 0
    for uid in user_ids:
        if uid == current_user.id:
            continue  # Skip self
        user = User.query.get(uid)
        if user:
            db.session.delete(user)
            deleted += 1
    
    db.session.commit()
    return jsonify({'success': True, 'deleted': deleted})

# --- File Serving Routes ---
@app.route('/uploads/<path:filename>')
def uploaded_file(filename): return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/processed/<path:filename>')
def processed_file(filename): return send_from_directory(app.config['PROCESSED_FOLDER'], filename)
@app.route('/generated/<path:filename>')
def generated_file(filename): return send_from_directory(app.config['GENERATED_FOLDER'], filename)

# --- API Endpoints ---

@app.route('/analyze', methods=['POST'])
@login_required
def analyze_image():
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    tasks = request.form.getlist('tasks')
    if file.filename == '' or not tasks: return jsonify({'error': 'No file or tasks'}), 400
    if not file or not allowed_file(file.filename): return jsonify({'error': 'File type not allowed'}), 400

    try:
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(original_path)

        # --- Capture Basic Metadata (Always) ---
        basic_meta = {}
        try:
            with Image.open(original_path) as img:
               basic_meta = {
                   'format': img.format,
                   'mode': img.mode,
                   'width': img.width,
                   'height': img.height,
                   'size_bytes': os.path.getsize(original_path)
               }
        except Exception as e:
            print(f"[ERROR] Could not extract basic metadata: {e}")

        response_data = {'filename': unique_filename, 'original_image_url': f"/uploads/{unique_filename}", 'results': {}, 'metadata': basic_meta}
        
        # Track which tasks were run for history display
        db_predictions = {
            'metadata': basic_meta,
            'source': 'analysis',
            'tasks_run': tasks  # List of task IDs that were selected
        }
        
        tags_to_save = []
        
        # --- Get EXIF data (Optional) ---
        if 'metadata' in tasks:
            exif_data = get_exif_data(original_path)
            response_data['metadata'].update(exif_data)
            db_predictions['metadata'].update(exif_data)

        if 'gemini_description' in tasks:
            # NEW PROMPT: Produces consistent, emoji-enhanced, professional output with proper formatting
            gemini_prompt = (
                "You are a professional image analysis system. Analyze the image and provide a structured report. "
                "Your output MUST follow this EXACT format. CRITICAL: Each bullet point MUST be on its own separate line.\n\n"
                "%%%CAPTION%%%\n"
                "[Creative, catchy caption in 1-7 words]\n\n"
                "%%%SUMMARY%%%\n"
                "[Brief 1-2 sentence summary describing the main subject, setting, and mood of the image]\n\n"
                "%%%DETAILS%%%\n"
                "🔍 **Key Observations:**\n\n"
                "- [Observation 1 - most prominent element]\n"
                "- [Observation 2 - secondary element]\n"
                "- [Observation 3 - background/context]\n"
                "- [Observation 4 - small detail most would miss]\n\n"
                "%%%COMPREHENSIVE%%%\n"
                "📝 **Detailed Analysis:**\n\n"
                "[Write a comprehensive 3-5 sentence paragraph describing the image in detail. "
                "Include the subject, setting, colors, textures, mood, and any notable elements. "
                "This should read like professional documentation that could be used for notes, reports, or archives. "
                "Be descriptive and thorough, using complete sentences in a flowing paragraph format.]\n\n"
                "%%%STYLE%%%\n"
                "🎨 **Visual Style:**\n\n"
                "- **Colors:** [Primary color palette]\n"
                "- **Lighting:** [Natural/artificial, soft/harsh, direction]\n"
                "- **Composition:** [Centered, rule of thirds, symmetry, etc.]\n"
                "- **Aesthetic:** [Photography style or art style]\n\n"
                "%%%SOCIAL%%%\n"
                "📱 [Ready-to-post social media caption with 3-5 relevant hashtags]\n\n"
                "%%%FUNFACT%%%\n"
                "💡 **Did you notice?** [One interesting, subtle, or surprising observation]\n\n"
                "%%%PROMPTS%%%\n"
                "[Generate 2 Stable Diffusion prompts to recreate this image, comma-separated keywords only]\n\n"
                "%%%QUESTIONS%%%\n"
                "[3 short questions (max 8 words each) separated by |||]\n\n"
                "%%%ANALYTICS%%%\n"
                "{\n"
                '  "key_insights": {\n'
                '    "overall_score": [0-100 integer],\n'
                '    "resolution_quality": "[Low/Medium/HD/4K]",\n'
                '    "mood_summary": "[one word mood]",\n'
                '    "mood_emoji": "[single emoji that best represents the mood, e.g. 😊🦁👑🌅🔥💕🌙]",\n'
                '    "style_category": "[one word style]"\n'
                '  },\n'
                '  "content_detection": [\n'
                '    {"label": "[main subject]", "percentage": [40-60]},\n'
                '    {"label": "[secondary element]", "percentage": [20-35]},\n'
                '    {"label": "[background/scene]", "percentage": [10-25]}\n'
                '  ],\n'
                '  "quality_metrics": [\n'
                '    {"name": "Sharpness", "score": [0-100]},\n'
                '    {"name": "Lighting", "score": [0-100]},\n'
                '    {"name": "Composition", "score": [0-100]},\n'
                '    {"name": "Color Balance", "score": [0-100]}\n'
                '  ],\n'
                '  "mood_analysis": [\n'
                '    {"emotion": "[primary emotion]", "intensity": [50-100]},\n'
                '    {"emotion": "[secondary emotion]", "intensity": [30-70]},\n'
                '    {"emotion": "[tertiary emotion]", "intensity": [20-50]}\n'
                '  ],\n'
                '  "technical_metrics": [\n'
                '    {"name": "Brightness", "value": [0-100]},\n'
                '    {"name": "Contrast", "value": [0-100]},\n'
                '    {"name": "Saturation", "value": [0-100]},\n'
                '    {"name": "Noise Level", "value": [0-100]},\n'
                '    {"name": "Detail", "value": [0-100]}\n'
                '  ]\n'
                "}\n"
                "[Provide ONLY valid JSON for ANALYTICS. Replace bracketed placeholders with actual values.]\n\n"
                "CRITICAL FORMATTING RULES:\n"
                "1. Use the %%% markers exactly as shown\n"
                "2. Each bullet point (-) MUST be on its own line\n"
                "3. The ANALYTICS section MUST be valid JSON"
            )

            full_response = get_ai_analysis(original_path, gemini_prompt)
            
            # --- SMART MULTI-PROVIDER PARSER ---
            # Works with new %%%SECTION%%% format and legacy formats
            
            def smart_parse_ai_response(response_text):
                """Parse AI response with new %%%SECTION%%% format."""
                import re
                import json
                
                result = {
                    'caption': '',
                    'overview': '',
                    'details': '',
                    'comprehensive': '',
                    'style': '',
                    'social_post': '',
                    'fun_fact': '',
                    'sd_prompts': '',
                    'suggestions': [],
                    # Analytics
                    'analytics': None,
                    # Legacy fields
                    'summary': '',
                    'detailed_prompt': '',
                    'hidden_details': ''
                }
                
                # Try new %%%SECTION%%% format
                sections = {}
                pattern = r'%%%(\w+)%%%\s*(.*?)(?=%%%\w+%%%|$)'
                matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
                
                for section_name, content in matches:
                    sections[section_name.upper()] = content.strip()
                
                if sections:
                    # Text Sections
                    result['caption'] = sections.get('CAPTION', '').strip()
                    result['summary'] = sections.get('SUMMARY', '').strip()
                    result['details'] = sections.get('DETAILS', '').strip()
                    result['comprehensive'] = sections.get('COMPREHENSIVE', '').strip()
                    result['style'] = sections.get('STYLE', '').strip()
                    result['social_post'] = sections.get('SOCIAL', '').strip()
                    result['fun_fact'] = sections.get('FUNFACT', '').strip()
                    result['sd_prompts'] = sections.get('PROMPTS', '').strip()
                    
                    # Parse Questions
                    questions_raw = sections.get('QUESTIONS', '')
                    result['suggestions'] = _parse_suggestions(questions_raw)
                    
                    # Parse Analytics JSON
                    analytics_raw = sections.get('ANALYTICS', '')
                    if analytics_raw:
                        try:
                            # Clean markdown
                            clean_json = re.sub(r'^```json\s*', '', analytics_raw.strip())
                            clean_json = re.sub(r'^```\s*', '', clean_json)
                            clean_json = re.sub(r'\s*```$', '', clean_json)
                            result['analytics'] = json.loads(clean_json)
                        except Exception as e:
                            print(f"[ERROR] Analytics parsing in main call: {e}")
                    
                    # Fill legacy fields
                    result['overview'] = result['summary']
                    result['detailed_prompt'] = f"{result['details']}\n\n{result['comprehensive']}\n\n{result['style']}"
                    result['hidden_details'] = result['fun_fact']
                else:
                    # Fallback to legacy parser (omitted for brevity, can remain if needed)
                    # For now assuming new format will work with new prompt
                    pass
                
                # Ensure defaults
                if not result['suggestions']:
                    result['suggestions'] = ["What colors are prominent?", "Describe the mood.", "What's the main subject?"]
                
                return result
            
            def _parse_suggestions(text):
                """Parse Q&A suggestions."""
                suggestions = []
                normalized = text.replace('|||', '\n').replace('||', '\n')
                for line in normalized.split('\n'):
                    clean = line.strip().lstrip('0123456789.-*? ').strip()
                    if len(clean) > 5 and len(clean) < 100:
                        suggestions.append(clean)
                return suggestions[:3]
            
            gemini_data = smart_parse_ai_response(full_response)
            
            response_data['results']['gemini'] = gemini_data
            db_predictions['gemini'] = gemini_data
            
            # --- EXTRACT ANALYTICS ---
            if gemini_data.get('analytics'):
                analytics_data = gemini_data['analytics']
                analytics_result = {
                    'key_insights': analytics_data.get('key_insights', {}),
                    'content_detection': analytics_data.get('content_detection', [])[:5],
                    'quality_metrics': analytics_data.get('quality_metrics', [])[:4],
                    'mood_analysis': analytics_data.get('mood_analysis', [])[:5],
                    'technical_metrics': analytics_data.get('technical_metrics', [])[:5]
                }
                response_data['results']['ai_analytics'] = analytics_result
                db_predictions['ai_analytics'] = analytics_result
            else:
                response_data['results']['ai_analytics'] = None
            
            # Extract keywords for tags
            gemini_text_for_tags = (gemini_data.get('overview', '') or gemini_data.get('summary', '')) + " " + (gemini_data.get('details', '') or gemini_data.get('detailed_prompt', ''))
            gemini_tags = extract_gemini_keywords(gemini_text_for_tags, num_keywords=5)
            
            for tag in gemini_tags: tags_to_save.append({'name': tag, 'source': 'Gemini', 'confidence': None})

        if 'ocr' in tasks:
            # Import provider detection
            from ai_provider import get_current_provider
            current_provider = get_current_provider()
            
            # Provider-specific OCR prompts
            if current_provider == 'gemini':
                # Gemini uses [y_min, x_min, y_max, x_max] format natively
                ocr_prompt = (
                    "Perform OCR on this image. "
                    "Return a JSON object with a single key 'detections'. "
                    "Each detection should have: "
                    "1. 'text': The detected text string. "
                    "2. 'box_2d': Bounding box as [y_min, x_min, y_max, x_max] with values 0-1000. "
                    "If no text is detected, return {\"detections\": []}. "
                    "Return ONLY valid JSON, no other text."
                )
            else:
                # Groq/Other uses [x_min, y_min, x_max, y_max] format
                ocr_prompt = (
                    "Perform OCR on this image. "
                    "Return a JSON object with a single key 'detections'. "
                    "Each detection should have: "
                    "1. 'text': The detected text string. "
                    "2. 'box_2d': Bounding box as [x_min, y_min, x_max, y_max] with INTEGER values between 0 and 1000. "
                    "   x_min is left edge, y_min is top edge, x_max is right edge, y_max is bottom edge. "
                    "   IMPORTANT: Do NOT use mathematical expressions (like '0.5 * 1000'). Use ONLY plain integers (e.g., 500). "
                    "If no text is detected, return {\"detections\": []}. "
                    "Return ONLY valid JSON, no other text or explanation."
                )
            
            # Start timing
            import time
            ocr_start_time = time.time()
            
            ai_response = get_ai_analysis(original_path, ocr_prompt)
            
            ocr_text_list = []
            ocr_filename = f"{os.path.splitext(unique_filename)[0]}_ocr.jpg"
            ocr_save_path = os.path.join(app.config['PROCESSED_FOLDER'], ocr_filename)
            ocr_annotated_url = None
            detection_count = 0

            try:
                # Smart JSON extraction - handles both raw JSON and markdown-wrapped JSON
                # NOTE: 're' and 'json' are imported at top of file - do not reimport here
                
                # Clean the response of any hidden/control characters
                cleaned_response = ai_response.strip()
                # Remove any BOM or zero-width characters
                cleaned_response = cleaned_response.encode('utf-8', errors='ignore').decode('utf-8')
                # Remove control characters except newlines and tabs
                cleaned_response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned_response)
                
                # First try to find JSON in markdown code block
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', cleaned_response)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    # Try to find raw JSON object - use greedy matching for nested arrays
                    json_match = re.search(r'\{\s*"detections"\s*:\s*\[[\s\S]*\]\s*\}', cleaned_response)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        # Fallback: try the whole response stripped
                        json_str = cleaned_response.lstrip('```json').lstrip('```').rstrip('```').strip()
                
                # Additional cleanup for the JSON string
                json_str = json_str.strip()
                
                ocr_data = json.loads(json_str)
                detections = ocr_data.get('detections', [])

                # Load image with cv2 to draw on it
                img = cv2.imread(original_path)
                h, w, _ = img.shape
                
                print(f"[DEBUG] OCR Provider: {current_provider}, Image size: {w}x{h}")

                if detections:
                    for detection in detections:
                        text = detection.get('text')
                        # Support multiple field names: 'box_2d', 'bbox', 'bounding_box'
                        bbox = detection.get('box_2d') or detection.get('bbox') or detection.get('bounding_box')
                        if not text or not bbox:
                            continue
                        
                        # Handle nested list format: [[y,x,y,x]] -> [y,x,y,x]
                        if isinstance(bbox, list) and len(bbox) > 0 and isinstance(bbox[0], list):
                            bbox = bbox[0]
                        
                        if len(bbox) < 4:
                            continue
                        
                        ocr_text_list.append(text)
                        
                        # Provider-specific coordinate handling
                        max_val = max(bbox)
                        
                        if current_provider == 'gemini':
                            # Gemini: [y_min, x_min, y_max, x_max] with values 0-1000
                            if max_val <= 1.0:
                                # Normalized 0-1
                                y1 = int(bbox[0] * h)
                                x1 = int(bbox[1] * w)
                                y2 = int(bbox[2] * h)
                                x2 = int(bbox[3] * w)
                            else:
                                # 0-1000 scale
                                y1 = int(bbox[0] / 1000 * h)
                                x1 = int(bbox[1] / 1000 * w)
                                y2 = int(bbox[2] / 1000 * h)
                                x2 = int(bbox[3] / 1000 * w)
                        else:
                            # Groq/Other: Usually [x_min, y_min, x_max, y_max] format
                            # Check if it's pixel coordinates or 0-1000 scale
                            if max_val <= 1.0:
                                # Normalized 0-1 with [x,y,x,y]
                                x1 = int(bbox[0] * w)
                                y1 = int(bbox[1] * h)
                                x2 = int(bbox[2] * w)
                                y2 = int(bbox[3] * h)
                            elif max_val <= 1000:
                                # 0-1000 scale - Groq uses [x,y,x,y] format (not [y,x,y,x] like Gemini)
                                x1 = int(bbox[0] / 1000 * w)
                                y1 = int(bbox[1] / 1000 * h)
                                x2 = int(bbox[2] / 1000 * w)
                                y2 = int(bbox[3] / 1000 * h)
                            else:
                                # Pixel coordinates - treat as [x,y,x,y]
                                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                        
                        # Ensure coordinates are within image bounds
                        x1 = max(0, min(x1, w - 1))
                        y1 = max(0, min(y1, h - 1))
                        x2 = max(0, min(x2, w - 1))
                        y2 = max(0, min(y2, h - 1))

                        # Draw bounding box
                        cv2.rectangle(img, (x1, y1), (x2, y2), (36, 255, 12), 2)
                        # Draw filled rectangle for text background
                        cv2.rectangle(img, (x1, y1 - 20), (x1 + len(text) * 10, y1), (36, 255, 12), -1)
                        # Put text
                        cv2.putText(img, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                    
                    cv2.imwrite(ocr_save_path, img)
                    ocr_annotated_url = f"/processed/{ocr_filename}"
                else:
                    ocr_text_list.append("No text detected.")
                    cv2.imwrite(ocr_save_path, img)
                    ocr_annotated_url = f"/processed/{ocr_filename}"

            except Exception as e:
                print(f"[ERROR] Failed to parse OCR JSON: {e}")
                print(f"AI Response was: {ai_response}")
                ocr_text_list.append("Error processing OCR data.")
                img = cv2.imread(original_path)
                cv2.imwrite(ocr_save_path, img)
                ocr_annotated_url = f"/processed/{ocr_filename}"

            # Calculate time taken
            ocr_end_time = time.time()
            ocr_time_taken = round(ocr_end_time - ocr_start_time, 2)
            detection_count = len(ocr_text_list) if ocr_text_list and ocr_text_list[0] != "No text detected." and ocr_text_list[0] != "Error processing OCR data." else 0
            
            final_ocr_text = "\n".join(ocr_text_list)
            ocr_result_data = {
                "annotated_image_url": ocr_annotated_url,
                "extracted_text": final_ocr_text,
                "detections": ocr_text_list,
                "detection_count": detection_count,
                "time_taken": ocr_time_taken,
                "provider": current_provider
            }
            response_data['results']['ocr'] = ocr_result_data
            # FIXED: Removed Duplicate Assignment
            db_predictions['ocr'] = ocr_result_data

        if 'imagga_tags' in tasks:
            try:
                imagga_results = get_imagga_tags(original_path, limit=8)
                
                if imagga_results:
                    response_data['results']['imagga'] = imagga_results
                    db_predictions['imagga'] = imagga_results
                    
                    for tag in imagga_results:
                        tags_to_save.append({
                            'name': tag['name'],
                            'source': 'Imagga',
                            'confidence': tag.get('confidence')
                        })
            except Exception as e:
                print(f"[ERROR] Imagga tagging failed: {e}")
                db_predictions['imagga'] = {'error': str(e)}

        yolo_results = {}
        for task in tasks:
            if task in yolo_models:
                results: list[Results] = yolo_models[task](original_path)
                
                if task == 'segmentation':
                    try:
                        if not results or not results[0].masks:
                            raise Exception("No objects found for segmentation.")
                        
                        all_masks = results[0].masks.data.cpu().numpy()
                        combined_mask_float = np.max(all_masks, axis=0)
                        
                        original_shape = cv2.imread(original_path).shape[:2] # (height, width)
                        mask_resized = cv2.resize(combined_mask_float, (original_shape[1], original_shape[0]), interpolation=cv2.INTER_NEAREST)
                        
                        mask_filename = f"{os.path.splitext(unique_filename)[0]}_mask.png"
                        mask_path = os.path.join(app.config['PROCESSED_FOLDER'], mask_filename)
                        cv2.imwrite(mask_path, mask_resized * 255)
                        
                        plot_filename = f"{os.path.splitext(unique_filename)[0]}_plot.jpg"
                        plot_path = os.path.join(app.config['PROCESSED_FOLDER'], plot_filename)
                        plot_image = results[0].plot(boxes=False)
                        cv2.imwrite(plot_path, plot_image)
                        
                        yolo_results[task] = {
                            'type': 'segmentation_data',
                            'mask_url': f"/processed/{mask_filename}",
                            'plot_url': f"/processed/{plot_filename}"
                        }
                    except Exception as e:
                        print(f"[ERROR] Failed to process and save mask: {e}")
                        yolo_results[task] = {'type': 'error', 'message': f'Failed to generate mask: {e}'}
                
                elif task == 'detection':
                    processed_filename = f"{os.path.splitext(unique_filename)[0]}_{task}{ext}"
                    processed_path_abs = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
                    
                    object_counts = Counter()
                    total_objects = 0
                    
                    try:
                        results[0].plot(save=True, filename=processed_path_abs)
                        
                        for box in results[0].boxes:
                            confidence = box.conf[0].item()
                            if confidence > 0.5: 
                                label = results[0].names[int(box.cls[0].item())]
                                object_counts[label] += 1
                                total_objects += 1
                                tags_to_save.append({'name': label, 'source': 'YOLO', 'confidence': round(confidence, 2)})

                        yolo_results[task] = {
                            'type': 'annotated_image', 
                            'processed_image_url': f"/processed/{processed_filename}",
                            'detection_counts': dict(object_counts), 
                            'total_objects': total_objects 
                        }

                    except AttributeError:
                        print(f"[WARNING] .plot() not available for YOLO task '{task}'.");
                        yolo_results[task] = {'type': 'error', 'message': f'Plot not available for {task}.'}
                
            

        if yolo_results: response_data['results']['yolo'] = yolo_results; db_predictions['yolo'] = yolo_results

        # --- Add Enhanced File Properties BEFORE DB Save (so it gets saved) ---
        if 'metadata' in tasks:
            try:
                with Image.open(original_path) as img:
                    width, height = img.size
                    file_size_kb = os.path.getsize(original_path) / 1024
                    
                    file_properties = {
                        "Filename": filename, 
                        "File Size": f"{file_size_kb:.2f} KB", 
                        "Format": img.format
                    }
                    image_details = {
                        "Dimensions": f"{width} x {height} pixels", 
                        "Color Mode": img.mode
                    }
                    
                    # Update response_data
                    if "File Properties" not in response_data['metadata']:
                        response_data['metadata']["File Properties"] = {}
                    response_data['metadata']["File Properties"].update(file_properties)
                    
                    if "Image Details" not in response_data['metadata']:
                        response_data['metadata']["Image Details"] = {}
                    response_data['metadata']["Image Details"].update(image_details)
                    
                    # CRITICAL: Also update db_predictions so it gets saved
                    if "File Properties" not in db_predictions['metadata']:
                        db_predictions['metadata']["File Properties"] = {}
                    db_predictions['metadata']["File Properties"].update(file_properties)
                    
                    if "Image Details" not in db_predictions['metadata']:
                        db_predictions['metadata']["Image Details"] = {}
                    db_predictions['metadata']["Image Details"].update(image_details)
            except Exception as e:
                print(f"[ERROR] Enhanced metadata extraction failed: {e}")

        image_id = None; normalized_tags = []
        
        if db_predictions:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO upload_history (user_id, filename, predictions) VALUES (?, ?, ?)", (current_user.id, unique_filename, json.dumps(db_predictions)))
                    image_id = cursor.lastrowid
                    
                    if image_id and tags_to_save:
                        normalized_tags = normalize_and_merge_tags(tags_to_save)
                        tag_insert_data = [(image_id, tag['name'], tag['source'], tag.get('confidence')) for tag in normalized_tags]
                        
                        cursor.executemany("INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)", tag_insert_data)
                    conn.commit()
                except Exception as e: print(f"[ERROR] DB transaction failed: {e}"); conn.rollback()
                finally: conn.close()

        response_data['tags'] = [tag['name'] for tag in normalized_tags]

        # Enhanced metadata already processed above and saved to db_predictions

        return jsonify(response_data)

    # In app.py -> def analyze_image():

    except Exception as e:
        print(f"[ERROR] An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()
        # REPLACE THIS LINE:
        # return jsonify({'error': 'An unexpected error occurred during analysis.'}), 500
        # WITH THIS LINE:
        return jsonify({'error': f'Analysis Error: {str(e)}'}), 500

@app.route('/ask', methods=['POST'])
@login_required
def ask_analyzer_question():
    data = request.get_json()
    if not data or 'question' not in data or 'filename' not in data: return jsonify({'error': 'Missing data'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(data['filename']))
    if not os.path.exists(filepath): return jsonify({'error': f'Image file not found: {data["filename"]}'}), 404
    
    try: 
        # UPDATED PROMPT: Request Markdown structure
        # UPDATED PROMPT: Direct Answer Focus
        prompt = (
            f"The user is asking a specific question about this image: '{data['question']}'. "
            "1. Answer the question DIRECTLY and IMMEDIATELY. "
            "2. Do NOT start with a generic image description or visual analysis unless the user explicitly asks 'What is this?'. "
            "3. If the user asks for 'benefits', 'history', or 'recipe', provide ONLY that information relevant to the image subject. "
            "4. Keep the formatting rules: Use **bold** for key facts and bullet points for lists."
        )
        answer = get_ai_analysis(filepath, prompt)
        
        # --- SAVE Q&A TO HISTORY DATABASE ---
        try:
            conn = get_db_connection()
            # Find the history record for this filename and current user
            record = conn.execute(
                "SELECT id, predictions FROM upload_history WHERE filename = ? AND user_id = ?",
                (data['filename'], current_user.id)
            ).fetchone()
            
            if record:
                predictions = json.loads(record['predictions'])
                
                # Initialize qa_history if it doesn't exist
                if 'qa_history' not in predictions:
                    predictions['qa_history'] = []
                
                # Append this Q&A
                predictions['qa_history'].append({
                    'question': data['question'],
                    'answer': answer,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Update the database
                conn.execute(
                    "UPDATE upload_history SET predictions = ? WHERE id = ?",
                    (json.dumps(predictions), record['id'])
                )
                conn.commit()
            conn.close()
        except Exception as db_error:
            print(f"[WARNING] Could not save Q&A to history: {db_error}")
        
        return jsonify({'answer': answer})
    except Exception as e: 
        print(f"[ERROR] Follow-up failed: {e}")
        return jsonify({'error': 'Failed to get answer.'}), 500

@app.route('/palette', methods=['POST'])
@login_required
def generate_palette():
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename): return jsonify({'error': 'Invalid file'}), 400
    try:
        ext = os.path.splitext(file.filename)[1]; temp_filename = f"temp_palette_{uuid.uuid4()}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename); file.save(filepath)
        image_url = f"/uploads/{temp_filename}"; 
        
        palette_colors = get_color_palette(filepath, num_colors=10)
        
        return jsonify({'image_url': image_url, 'palette': palette_colors}) 
    except Exception as e: 
        print(f"[ERROR] Palette generation failed: {e}"); 
        return jsonify({'error': 'Could not process image.'}), 500

@app.route('/get-color-name', methods=['POST'])
@login_required
def get_color_name_api():
    data = request.get_json()
    hex_code = data.get('hex_code')
    
    if not hex_code or not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code):
        return jsonify({'error': 'Invalid hex code provided.'}), 400
        
    try:
        prompt = (
            f"What is the most common, simple name for the color with this "
            f"hex code: {hex_code}? Respond with *only* the color name and nothing else. "
            f"For example, if the code is #FF0000, just respond 'Red'."
        )
        
        color_name = get_ai_text_prompt(prompt)
        color_name = color_name.strip().replace('*', '').replace('"', '')
        
        return jsonify({'color_name': color_name})
        
    except Exception as e:
        print(f"[ERROR] Gemini color name generation failed: {e}")
        return jsonify({'error': 'Failed to get color name from AI.'}), 500

# --- Define this dictionary at the top level or before the function ---
STYLE_PRESETS = {
    'cinematic': ", cinematic lighting, shallow depth of field, 8k, masterpiece, highly detailed, dramatic atmosphere, wide angle",
    'anime': ", anime style, studio ghibli, vibrant colors, detailed line art, cel shaded, trending on artstation",
    'photorealistic': ", 8k, raw photo, highly detailed, ultra-realistic, professional photography, sharp focus, f/1.8",
    'digital-art': ", digital art, concept art, trending on artstation, highly detailed, smooth, vibrant, illustration",
    'oil-painting': ", oil painting, textured canvas, heavy brush strokes, classical art style, impressionist",
    'cyberpunk': ", cyberpunk, neon lights, futuristic, sci-fi, dark atmosphere, highly detailed, synthwave",
    'low-poly': ", low poly, isometric, blender render, 3d, minimalistic, flat shading, pastel colors",
    'pixel-art': ", pixel art, 16-bit, retro game style, dithering, limited palette"
}

# --- REPLACEMENT FUNCTION ---
@app.route('/generate-image', methods=['POST'])
@login_required
def generate_image_api():
    base_prompt = request.form.get('prompt')
    style = request.form.get('style', 'none')  # Get the style from the form
    custom_name = request.form.get('custom_name', '').strip()  # Custom name from user
    model_provider = request.form.get('model_provider', 'auto')  # Model provider selection
    
    if not base_prompt: 
        return jsonify({'error': 'Prompt is missing.'}), 400
        
    try: 
        # 1. Append Style Modifiers
        modifier = STYLE_PRESETS.get(style, "")
        final_prompt = f"{base_prompt}{modifier}"
        
        # 2. Generate Image with the modified prompt (pass model_provider)
        filename = generate_image_from_prompt(final_prompt, app.config['GENERATED_FOLDER'], style=style, model_provider=model_provider)
        
        # 3. Generate AI Tags for the image using Groq (with Gemini fallback)
        image_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
        ai_tags = []
        
        # Try Groq first
        if groq_processor.is_available():
            ai_tags = groq_processor.generate_image_tags(image_path, num_tags=8)
        
        # Fallback to Gemini if Groq failed or returned empty
        if not ai_tags:
            ai_tags = gemini_processor.generate_image_tags(image_path, num_tags=8)
        
        # Extract keywords from prompt as backup tags
        if not ai_tags:
            # Simple keyword extraction from prompt
            words = base_prompt.lower().split()
            ai_tags = [w for w in words if len(w) > 3 and w.isalpha()][:5]
        
        # Add style as a tag
        if style and style != 'none':
            ai_tags.append(style.replace('-', ' '))
        
        # Add "ai generated" tag for searchability
        ai_tags.append("ai generated")
        
        # Extract metadata from generated image
        generated_meta = {}
        try:
           with Image.open(image_path) as img:
               generated_meta = {
                   'format': img.format,
                   'mode': img.mode,
                   'width': img.width,
                   'height': img.height,
                   'size_bytes': os.path.getsize(image_path)
               }
        except Exception as e:
            print(f"[ERROR] Error getting generated image metadata: {e}")

        # 4. Prepare data for History DB
        caption = custom_name if custom_name else f"AI Generated Image ({style} style)"
        predictions_data = {
            "source": "generation-txt2img",
            "prompt": base_prompt,       # Store original prompt (what user typed)
            "style_used": style,         # Store the style key
            "full_prompt": final_prompt, # Store actual prompt used
            "custom_name": custom_name,  # Store user's custom name
            "gemini": { "caption": caption },
            "metadata": generated_meta   # Save metadata
        }
        
        # 5. Save to Database (history + tags)
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO upload_history (user_id, filename, predictions) VALUES (?, ?, ?)",
                    (current_user.id, filename, json.dumps(predictions_data))
                )
                image_id = cursor.lastrowid
                
                # Save AI-generated tags
                for tag in ai_tags:
                    tag_clean = tag.strip().lower()
                    if tag_clean:
                        cursor.execute(
                            "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
                            (image_id, tag_clean, 'AI-Generated', 0.9)
                        )
                
                # Save custom name as a tag too (for searchability)
                if custom_name:
                    cursor.execute(
                        "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
                        (image_id, custom_name.lower(), 'Custom', 1.0)
                    )
                
                conn.commit()
                print(f"[INFO] Saved generated image with {len(ai_tags)} tags + custom name: {custom_name}")
            except Exception as e:
                print(f"[ERROR] Failed to save generated image to history: {e}")
                conn.rollback()
            finally:
                conn.close()
                
        return jsonify({'image_url': f"/generated/{filename}"})

    except Exception as e: 
        print(f"[ERROR] Image generation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-prompt-idea', methods=['POST'])
@login_required
def generate_prompt_idea():
    data = request.get_json(); idea = data.get('idea')
    if not idea: return jsonify({'error': 'No idea provided'}), 400
    try:
        prompt_template = (
    "Act as a technical prompt generator for Stable Diffusion XL. "
    "Translate the concept '{idea}' into a prompt. "
    "CRITICAL FOR TEXT RENDERING: If the user requests text, names, or words to appear ON or IN the image (e.g., 'with NAME written on it', 'label saying X', 'cup with NAME'), "
    "use NATURAL LANGUAGE format WITHOUT weights. "
    "Format: text \"EXACT_TEXT\" on SURFACE, [subject description], [context], [style], [lighting], [quality keywords]. "
    "Example for 'coffee cup with Jack written on it': text \"Jack\" on cup side, white coffee mug on wooden table, close-up, photorealistic, warm lighting, highly detailed, sharp focus, 8k, masterpiece. "
    "DO NOT use parentheses or weights like (keyword:1.2) when text is requested - they confuse the AI and appear as literal text in the image. "
    "If NO text is requested, then use weighted syntax: '(Main Subject:1.3), (Action), (Context), (Art Style:1.2), (Lighting), (Camera/View), (Quality tags)'. "
    "Include quality keywords: highly detailed, sharp focus, professional quality, 8k, masterpiece, best quality. "
    "CRITICAL: No filler words like 'A picture of'. Output ONLY the prompt."
)

        formatted_prompt = prompt_template.format(idea=idea)
        generated_prompt = get_ai_text_prompt(formatted_prompt)
        if generated_prompt.startswith("Error:"): raise Exception(generated_prompt)
        return jsonify({'prompt': generated_prompt.strip()})
    # ... inside the try/except block ...
    except Exception as e: 
        print(f"[ERROR] Prompt idea generation failed: {e}"); 
        # REPLACE THIS LINE:
        # return jsonify({'error': 'Failed to generate prompt idea.'}), 500
        # WITH THIS LINE:
        return jsonify({'error': f'Prompt Gen Failed: {str(e)}'}), 500

@app.route('/generate-image-from-image', methods=['POST'])
@login_required
def generate_image_from_image_api():
    # 1. Validation
    if 'init_image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['init_image']
    style = request.form.get('style', 'none')
    custom_name = request.form.get('custom_name', '').strip()  # Custom name from user
    model_provider = request.form.get('model_provider', 'auto')  # Model provider selection

    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
            
    try:
        # 2. Save uploaded image
        # We save this PERMANENTLY (or at least don't delete immediately) 
        # so it can be displayed in the frontend as "Original".
        filename = secure_filename(file.filename)
        # Use a unique name to prevent overwrites, but keep extension
        unique_name = f"img2img_src_{uuid.uuid4()}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)
        
        # URL for the frontend to display the original
        original_image_url = f"/uploads/{unique_name}"
        
        # --- PROMPT CACHING LOGIC ---
        # We use the filename as a key to know if we're working on the same image
        # If the user uploads a NEW image, the filename changes, so we regenerate.
        
        # Check if we have a cached prompt for this specific image and style
        cache_key = f"prompt_cache_{filename}_{style}"
        cached_prompt = session.get(cache_key)
        
        if cached_prompt and request.form.get('regenerate') == 'true':
             # If "regenerate" flag is sent AND we have a cache, use it!
             print(f"[INFO] Using CACHED prompt for {filename} ({style})")
             base_prompt = cached_prompt
        else:
            # 3. Use Gemini to create a Style-Aware Prompt (Fresh Generation)
            print(f"[INFO] Asking Gemini to describe {filename} in '{style}' style...")
            
            # Pass the 'style' to Gemini so it avoids conflicting terms (like 'photorealistic' vs 'low-poly')
            base_prompt = generate_prompt_from_image(save_path, prompt_type="recreate", target_style=style) 
    
            if base_prompt.startswith("Error"):
                 raise Exception(f"Gemini API Error: {base_prompt}")
            
            # Store in session for next time
            session[cache_key] = base_prompt
            print(f"[INFO] Coded prompt into session: {cache_key}")

        # 4. Append Style Modifiers (Double enforcement)
        # We still add the preset keywords to ensure the generator gets the specific tech specs (e.g., 'unreal engine', '8k')
        modifier = STYLE_PRESETS.get(style, "")
        final_prompt = f"{base_prompt}{modifier}"

        print(f"[INFO] Final Prompt: {final_prompt}")
        
        # 5. GENERATE (pass model_provider)
        generated_filename = generate_image_from_prompt(final_prompt, app.config['GENERATED_FOLDER'], style=style, model_provider=model_provider)
        
        # 6. Generate AI Tags for the image using Groq (with Gemini fallback)
        image_path = os.path.join(app.config['GENERATED_FOLDER'], generated_filename)
        ai_tags = []
        
        # Try Groq first
        if groq_processor.is_available():
            ai_tags = groq_processor.generate_image_tags(image_path, num_tags=8)
        
        # Fallback to Gemini if Groq failed or returned empty
        if not ai_tags:
            ai_tags = gemini_processor.generate_image_tags(image_path, num_tags=8)
        
        # Fallback: Extract keywords from prompt
        if not ai_tags:
            words = base_prompt.lower().split()
            ai_tags = [w for w in words if len(w) > 3 and w.isalpha()][:5]
        
        # Add style and "ai generated" tags
        if style and style != 'none':
            ai_tags.append(style.replace('-', ' '))
        ai_tags.append("ai generated")
        ai_tags.append("image to image")
        
        # Extract metadata from generated image
        generated_meta = {}
        try:
           with Image.open(image_path) as img:
               generated_meta = {
                   'format': img.format,
                   'mode': img.mode,
                   'width': img.width,
                   'height': img.height,
                   'size_bytes': os.path.getsize(image_path)
               }
        except Exception as e:
            print(f"[ERROR] Error getting generated img2img metadata: {e}")

        # 7. Save to History DB
        caption = custom_name if custom_name else f"AI Image Recreation ({style} style)"
        predictions_data = {
            "source": "generation-img2img", 
            "prompt": base_prompt,
            "style_used": style,
            "full_prompt": final_prompt,
            "custom_name": custom_name,
            "init_image_url": original_image_url,
            "gemini": { "caption": caption },
            "metadata": generated_meta
        }

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO upload_history (user_id, filename, predictions) VALUES (?, ?, ?)",
                    (current_user.id, generated_filename, json.dumps(predictions_data))
                )
                image_id = cursor.lastrowid
                
                # Save AI-generated tags
                for tag in ai_tags:
                    tag_clean = tag.strip().lower()
                    if tag_clean:
                        cursor.execute(
                            "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
                            (image_id, tag_clean, 'AI-Generated', 0.9)
                        )
                
                # Save custom name as a tag too (for searchability)
                if custom_name:
                    cursor.execute(
                        "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
                        (image_id, custom_name.lower(), 'Custom', 1.0)
                    )
                
                conn.commit()
                print(f"[INFO] Saved img2img with {len(ai_tags)} tags + custom name: {custom_name}")
            except Exception as e:
                 print(f"[ERROR] Failed to save to history: {e}")
                 conn.rollback()
            finally:
                 conn.close()

        # REMOVED: os.remove(save_path) 
        # We do NOT delete the file so the user can see "Original vs Generated" in the UI.

        return jsonify({
            'original_image_url': original_image_url,
            'generated_image_url': f"/generated/{generated_filename}"
        })
        
    except Exception as e:
        print(f"[ERROR] Recreation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/edit/spotlight', methods=['POST'])
@login_required
def edit_spotlight():
    try:
        data = request.get_json()
        original_path, mask_path = _get_file_paths_from_urls(data)
        
        # --- NEW: Get intensity from request, default to 50 ---
        intensity = int(data.get('intensity', 50))
        
        # --- NEW: Pass intensity to the processor ---
        pil_image = image_editor_processor.apply_spotlight_effect(original_path, mask_path, intensity)
        
        base_filename = os.path.basename(original_path)
        return jsonify(_save_and_get_url(pil_image, base_filename, "spotlight"))
    except Exception as e:
        print(f"[ERROR] /edit/spotlight failed: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/edit/remove-bg', methods=['POST'])
@login_required
def edit_remove_bg():
    try:
        data = request.get_json()
        original_path, mask_path = _get_file_paths_from_urls(data)
        
        # Apply the background removal
        pil_image = image_editor_processor.apply_remove_background(original_path, mask_path)
        
        base_filename = os.path.basename(original_path)
        return jsonify(_save_and_get_url(pil_image, base_filename, "bg_removed"))
    except Exception as e:
        print(f"[ERROR] /edit/remove-bg failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/edit/blur-bg', methods=['POST'])
@login_required
def edit_blur_bg():
    try:
        data = request.get_json()
        original_path, mask_path = _get_file_paths_from_urls(data)
        
        # Get blur amount (default 15 if not sent)
        blur_amount = int(data.get('blur_amount', 15))
        
        pil_image = image_editor_processor.apply_blur_background(original_path, mask_path, blur_amount)
        
        base_filename = os.path.basename(original_path)
        return jsonify(_save_and_get_url(pil_image, base_filename, "blur_bg"))
    except Exception as e:
        print(f"[ERROR] /edit/blur-bg failed: {e}")
        return jsonify({'error': str(e)}), 500

    # --- HELPER FUNCTIONS FOR EDITING (Paste this BEFORE the /edit/ routes) ---

def _get_file_paths_from_urls(data):
    """Helper to resolve file paths from frontend URLs."""
    if 'original_url' not in data or 'mask_url' not in data:
        raise Exception("Missing original_url or mask_url in request.")
    
    # Extract filenames from URLs
    original_filename = os.path.basename(data['original_url'])
    mask_filename = os.path.basename(data['mask_url'])
    
    # Resolve full paths
    # 1. Try Upload folder first
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    
    # 2. If not in uploads, check generated folder (for AI created images)
    if not os.path.exists(original_path):
        original_path = os.path.join(app.config['GENERATED_FOLDER'], original_filename)
        
    mask_path = os.path.join(app.config['PROCESSED_FOLDER'], mask_filename)

    if not os.path.exists(original_path):
        raise Exception(f"Original file not found on server: {original_path}")
    if not os.path.exists(mask_path):
        raise Exception(f"Mask file not found on server: {mask_path}")
        
    return original_path, mask_path

def _save_and_get_url(pil_image, base_filename, effect_name):
    """Helper to save the processed image and return the JSON response."""
    # Determine extension and save path
    ext = ".png" if pil_image.mode == 'RGBA' else ".jpg"
    new_filename = f"{os.path.splitext(base_filename)[0]}_{effect_name}{ext}"
    save_path = os.path.join(app.config['PROCESSED_FOLDER'], new_filename)
    
    # Save image
    if ext == ".jpg":
        pil_image.convert('RGB').save(save_path, "JPEG", quality=95)
    else:
        pil_image.save(save_path, "PNG")
        
    return {
        'status': 'success',
        'processed_image_url': f"/processed/{new_filename}",
        'filename': new_filename
    }
# --- END HELPERS ---


@app.route('/edit/smart-crop', methods=['POST'])
@login_required
def edit_smart_crop():
    try:
        data = request.get_json()
        original_path, mask_path = _get_file_paths_from_urls(data)
        pil_image = image_editor_processor.apply_smart_crop(original_path, mask_path)
        base_filename = os.path.basename(original_path)
        return jsonify(_save_and_get_url(pil_image, base_filename, "cropped"))
    except Exception as e:
        print(f"[ERROR] /edit/smart-crop failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/edit/filter', methods=['POST'])
@login_required
def edit_filter():
    # 1. Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    filter_type = request.form.get('filter_name', 'bw') # User snippet uses 'filter_name'
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # 2. Save the uploaded file temporarily
        # We need to save it because image_editor_processor expects a path for cv2.imread
        filename = secure_filename(file.filename)
        # Use a temp name to avoid conflicts if needed, or just overwrite/use distinct name
        temp_filename = f"temp_upload_{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(filepath)

        # 3. Apply the filter
        # Ensure image_editor_processor.apply_filter is available (it is)
        pil_image = image_editor_processor.apply_filter(filepath, filter_type)
        
        # 4. Save and return URL
        # We'll use the helper _save_and_get_url but we need to pass a base filename
        # The user's snippet constructs manual path, but using the helper is consistent with other routes
        
        # Clean up the temp input file? 
        # For now, let's leave it or clean it up. The user's snippet doesn't show cleanup.
        # But we should probably clean it up to avoid clutter.
        
        response = _save_and_get_url(pil_image, filename, f"filter_{filter_type}")
        
        # Cleanup temp file
        try:
            os.remove(filepath)
        except:
            pass
            
        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] /edit/filter failed: {e}")
        return jsonify({'error': str(e)}), 500


# --- History Deletion ---
@app.route('/delete_history', methods=['POST'])
@login_required
def delete_history_entry():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({'error': 'Missing history ID'}), 400
    
    history_id = data['id']
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Could not connect to database'}), 500

    try:
        cursor = conn.cursor()
        # Only allow delete if record belongs to current user
        cursor.execute("SELECT filename, predictions FROM upload_history WHERE id = ? AND user_id = ?", (history_id, current_user.id))
        record = cursor.fetchone()
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
            
        original_filename = record['filename']
        predictions_json = json.loads(record['predictions'])

        cursor.execute("DELETE FROM upload_history WHERE id = ? AND user_id = ?", (history_id, current_user.id))
        conn.commit()

        # Determine path to delete
        file_to_delete_path = None
        if predictions_json.get('source') and 'generation' in predictions_json.get('source'):
            file_to_delete_path = os.path.join(app.config['GENERATED_FOLDER'], original_filename)
        else:
            file_to_delete_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)

        try:
            if file_to_delete_path and os.path.exists(file_to_delete_path):
                os.remove(file_to_delete_path)
                print(f"[INFO] Deleted main file: {file_to_delete_path}")
        except Exception as e:
            print(f"[ERROR] Could not delete main file {original_filename}: {e}")

        # Delete processed files (masks, etc.)
        if 'yolo' in predictions_json:
            for task, result in predictions_json['yolo'].items():
                if result.get('processed_image_url'):
                    try:
                        processed_filename = os.path.basename(result['processed_image_url'])
                        processed_filepath = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
                        if os.path.exists(processed_filepath):
                            os.remove(processed_filepath)
                    except Exception: pass
                
                if result.get('mask_url'):
                    try:
                        mask_filename = os.path.basename(result['mask_url'])
                        mask_filepath = os.path.join(app.config['PROCESSED_FOLDER'], mask_filename)
                        if os.path.exists(mask_filepath):
                            os.remove(mask_filepath)
                    except Exception: pass
                
                if result.get('plot_url'):
                    try:
                        plot_filename = os.path.basename(result['plot_url'])
                        plot_filepath = os.path.join(app.config['PROCESSED_FOLDER'], plot_filename)
                        if os.path.exists(plot_filepath):
                            os.remove(plot_filepath)
                    except Exception: pass
        
        if 'ocr' in predictions_json and predictions_json['ocr'].get('annotated_image_url'):
            try:
                ocr_filename = os.path.basename(predictions_json['ocr']['annotated_image_url'])
                ocr_filepath = os.path.join(app.config['PROCESSED_FOLDER'], ocr_filename)
                if os.path.exists(ocr_filepath):
                    os.remove(ocr_filepath)
            except Exception: pass

        return jsonify({'status': 'success', 'message': f'Record {history_id} deleted.'})

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to delete history entry {history_id}: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500
    finally:
        conn.close()

# --- Clear All History for Current User ---
@app.route('/clear_all_history', methods=['POST'])
@login_required
def clear_all_history():
    """Deletes all history records for the current user."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Could not connect to database'}), 500

    try:
        cursor = conn.cursor()
        
        # Get all records for current user to delete associated files
        cursor.execute("SELECT id, filename, predictions FROM upload_history WHERE user_id = ?", (current_user.id,))
        records = cursor.fetchall()
        
        deleted_count = 0
        for record in records:
            predictions_json = json.loads(record['predictions'])
            filename = record['filename']
            
            # Delete main file
            if predictions_json.get('source') and 'generation' in predictions_json.get('source'):
                file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
            else:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"[WARN] Could not delete file {filename}: {e}")
            
            deleted_count += 1
        
        # Delete all records for current user (CASCADE will delete tags)
        cursor.execute("DELETE FROM upload_history WHERE user_id = ?", (current_user.id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'Cleared {deleted_count} history entries.'})
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to clear history: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500
    finally:
        conn.close()


# --- Main Execution ---
if __name__ == '__main__':
    # Initialize the SQLite history DB
    initialize_db()
    
    # Create the PostgreSQL user DB tables if they don't exist
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)