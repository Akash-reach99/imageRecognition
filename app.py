# ImageRecognizer/app.py
import os
import uuid
import json
import sqlite3
import re
import random
from collections import Counter
from datetime import datetime, timedelta
from dotenv import load_dotenv  # <--- Add this
load_dotenv()
from flask import (
    Flask, request, render_template, jsonify, send_from_directory,
    send_file, flash, redirect, url_for, abort, session
)
from PIL import Image
# --- EXIF Fix ---
from PIL.ExifTags import TAGS, GPSTAGS
from ultralytics import YOLO
from ultralytics.engine.results import Results # Added for type hinting
from werkzeug.utils import secure_filename
from sklearn.cluster import KMeans
import numpy as np
import cv2
from io import BytesIO

# --- IMPORTS FOR LOGIN, POSTGRESQL & MAIL ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message # <--- Added Flask-Mail

# --- Import AI processors ---
from gemini_processor import get_gemini_analysis, get_gemini_text_prompt 
from stability_processor import generate_image_from_prompt
from imagga_processor import get_imagga_tags
import image_editor_processor

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
# You must generate an "App Password" in your Google Account settings if using Gmail.
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
mail = Mail(app) # <--- Initialize Mail

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
    password_hash = db.Column(db.String(255), nullable=True) # Nullable if only using Email OTP login
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
            
    return render_template('verify_otp.html') # You will need to create this template

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {e}', 'danger')

    return render_template('register.html')

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
            params = []
            
            # --- Check for special search term ---
            if search_query.lower() == 'ai generated':
                base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h"
                base_query += " WHERE h.predictions LIKE '%\"source\": \"generation%' "
                base_query += " ORDER BY h.upload_timestamp DESC"
            
            # --- Existing tag search logic ---
            elif search_query:
                tags = [tag.strip().lower() for tag in search_query.split(',') if tag.strip()]
                if tags:
                    placeholders = ','.join('?' for _ in tags)
                    base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h"
                    base_query += f" WHERE h.id IN (SELECT t.image_id FROM image_tags t WHERE t.tag_name IN ({placeholders}) GROUP BY t.image_id HAVING COUNT(DISTINCT t.tag_name) = ?)"
                    params.extend(tags); params.append(len(tags))
                    base_query += " ORDER BY h.upload_timestamp DESC"
                else:
                    # Search was empty or just commas
                    base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h ORDER BY h.upload_timestamp DESC"
            
            # --- Default: No search ---
            else:
                base_query = "SELECT h.id, h.filename, h.predictions, h.upload_timestamp FROM upload_history h ORDER BY h.upload_timestamp DESC"


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
    
    # You could also fetch stats from the SQLite DB
    conn = get_db_connection()
    total_analyses = 0
    if conn:
        try:
            total_analyses = conn.execute("SELECT COUNT(id) FROM upload_history").fetchone()[0]
        except Exception as e:
            print(f"Admin panel couldn't get history count: {e}")
        finally:
            conn.close()

    return render_template('admin.html', all_users=all_users, total_analyses=total_analyses)

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Promotes a user to admin or demotes an admin to user."""
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('dashboard'))
    
    # An admin cannot change their own status
    if user_id == current_user.id:
        flash("You cannot change your own admin status.", 'danger')
        return redirect(url_for('admin_panel'))
        
    user_to_toggle = db.get_or_404(User, user_id)
    
    # Toggle the boolean status
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

    # An admin cannot delete themselves
    if user_id == current_user.id:
        flash("You cannot delete your own account from the admin panel.", 'danger')
        return redirect(url_for('admin_panel'))
        
    user_to_delete = db.get_or_404(User, user_id)
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f"User {user_to_delete.username} has been permanently deleted.", 'success')
    return redirect(url_for('admin_panel'))

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

        response_data = {'filename': unique_filename, 'original_image_url': f"/uploads/{unique_filename}", 'results': {}, 'metadata': {}}
        db_predictions = {}
        
        tags_to_save = []
        
        # --- Get EXIF data ---
        if 'metadata' in tasks:
            exif_data = get_exif_data(original_path)
            response_data['metadata'].update(exif_data)
            db_predictions['metadata'] = exif_data

        if 'gemini_description' in tasks:
            gemini_prompt = (
                "Analyze the provided image and generate the following content sections, separated ONLY by '%%%':\n"
                "1.  **Caption:** A creative and concise caption (1-7 words).\n"
                "2.  **Summary:** A brief summary describing the main subject and mood (1-2 sentences).\n"
                "3.  **Detailed Description & Prompt:** A detailed analysis (1-2 paragraphs) focusing on visual elements (subject, setting, style, lighting, composition, colors). End this section with a bullet point list under the heading '**Stable Diffusion Prompt Suggestions:**' containing 1-2 optimized, comma-separated prompts suitable for Stable Diffusion (include style keywords like 'photorealistic', 'cinematic', 'illustration', etc.).\n"
                "4.  **Social Media Post:** A short, engaging post for social media (1-3 sentences) including 3-5 relevant hashtags.\n"
                "5.  **Hidden Details:** List 1-3 subtle or interesting details often missed, using bullet points like '* Detail: [Location hint]'. If none, state 'No specific hidden details noted.'\n"
                "Ensure '%%%' is the ONLY separator between these 5 numbered sections."
            )

            full_response = get_gemini_analysis(original_path, gemini_prompt)
            parts = full_response.split('%%%')

            gemini_data = {
                'caption': parts[0].replace('1. **Caption:**', '').strip() if len(parts) > 0 else "Analysis Error",
                'summary': parts[1].replace('2. **Summary:**', '').strip() if len(parts) > 1 else "",
                'detailed_prompt': parts[2].replace('3. **Detailed Description & Prompt:**', '').strip() if len(parts) > 2 else "",
                'social_post': parts[3].replace('4. **Social Media Post:**', '').strip() if len(parts) > 3 else "",
                'hidden_details': parts[4].replace('5. **Hidden Details:**', '').strip() if len(parts) > 4 else ""
            }
            response_data['results']['gemini'] = gemini_data
            db_predictions['gemini'] = gemini_data
            gemini_text_for_tags = gemini_data['summary'] + " " + gemini_data['detailed_prompt'].split('**Stable Diffusion Prompt Suggestions:**')[0]
            gemini_tags = extract_gemini_keywords(gemini_text_for_tags, num_keywords=5)
            
            for tag in gemini_tags: tags_to_save.append({'name': tag, 'source': 'Gemini', 'confidence': None})

        if 'ocr' in tasks:
            ocr_prompt = (
                "Perform OCR on this image. "
                "Return a JSON object with a single key 'detections'. "
                "The value of 'detections' should be a list of objects, where each object has: "
                "1. 'text': The detected text string. "
                "2. 'bbox': A list of [x_min, y_min, x_max, y_max] coordinates as normalized values (0.0 to 1.0). "
                "If no text is detected, return {\"detections\": []}."
            )
            
            gemini_response = get_gemini_analysis(original_path, ocr_prompt)
            
            ocr_text_list = []
            ocr_filename = f"{os.path.splitext(unique_filename)[0]}_ocr.jpg"
            ocr_save_path = os.path.join(app.config['PROCESSED_FOLDER'], ocr_filename)
            ocr_annotated_url = None

            try:
                # Clean the response from Gemini
                json_str = gemini_response.strip().lstrip('```json').rstrip('```')
                ocr_data = json.loads(json_str)
                detections = ocr_data.get('detections', [])

                # Load image with cv2 to draw on it
                img = cv2.imread(original_path)
                h, w, _ = img.shape

                if detections:
                    for detection in detections:
                        text = detection.get('text')
                        bbox = detection.get('bbox')
                        if not text or not bbox:
                            continue
                        
                        ocr_text_list.append(text)
                        
                        # Denormalize coordinates
                        x1 = int(bbox[0] * w); y1 = int(bbox[1] * h)
                        x2 = int(bbox[2] * w); y2 = int(bbox[3] * h)

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
                print(f"[ERROR] Failed to parse Gemini OCR JSON: {e}")
                print(f"Gemini Response was: {gemini_response}")
                ocr_text_list.append("Error processing OCR data.")
                img = cv2.imread(original_path)
                cv2.imwrite(ocr_save_path, img)
                ocr_annotated_url = f"/processed/{ocr_filename}"

            final_ocr_text = "\n".join(ocr_text_list)
            ocr_result_data = {
                "annotated_image_url": ocr_annotated_url,
                "extracted_text": final_ocr_text,
                "detections": ocr_text_list  # <--- ADD THIS LINE
            }
            response_data['results']['ocr'] = ocr_result_data
            response_data['results']['ocr'] = ocr_result_data
            db_predictions['ocr'] = ocr_result_data

        if 'imagga_tags' in tasks:
            try:
                imagga_results = get_imagga_tags(original_path, limit=4)
                
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

        image_id = None; normalized_tags = []
        
        if db_predictions:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO upload_history (filename, predictions) VALUES (?, ?)", (unique_filename, json.dumps(db_predictions)))
                    image_id = cursor.lastrowid
                    
                    if image_id and tags_to_save:
                        normalized_tags = normalize_and_merge_tags(tags_to_save)
                        tag_insert_data = [(image_id, tag['name'], tag['source'], tag.get('confidence')) for tag in normalized_tags]
                        
                        cursor.executemany("INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)", tag_insert_data)
                    conn.commit()
                except Exception as e: print(f"[ERROR] DB transaction failed: {e}"); conn.rollback()
                finally: conn.close()

        response_data['tags'] = [tag['name'] for tag in normalized_tags]

        # --- Add File Properties (metadata) ---
        # --- Add File Properties (ONLY runs if 'metadata' is checked) ---
        if 'metadata' in tasks:  # <--- This 'if' statement makes the checkbox work
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
                 
                 # Add File Properties to response
                 if "File Properties" in response_data['metadata']:
                    response_data['metadata']["File Properties"].update(file_properties)
                 else:
                    response_data['metadata']["File Properties"] = file_properties
                 
                 # Add Image Details to response
                 if "Image Details" in response_data['metadata']:
                    response_data['metadata']["Image Details"].update(image_details)
                 else:
                    response_data['metadata']["Image Details"] = image_details


        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred during analysis.'}), 500

@app.route('/ask', methods=['POST'])
@login_required
def ask_analyzer_question():
    data = request.get_json()
    if not data or 'question' not in data or 'filename' not in data: return jsonify({'error': 'Missing data'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(data['filename']))
    if not os.path.exists(filepath): return jsonify({'error': f'Image file not found: {data["filename"]}'}), 404
    try: answer = get_gemini_analysis(filepath, data['question']); return jsonify({'answer': answer})
    except Exception as e: print(f"[ERROR] Follow-up failed: {e}"); return jsonify({'error': 'Failed to get answer.'}), 500

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
        
        color_name = get_gemini_text_prompt(prompt)
        color_name = color_name.strip().replace('*', '').replace('"', '')
        
        return jsonify({'color_name': color_name})
        
    except Exception as e:
        print(f"[ERROR] Gemini color name generation failed: {e}")
        return jsonify({'error': 'Failed to get color name from AI.'}), 500

@app.route('/generate-image', methods=['POST'])
@login_required
def generate_image_api():
    prompt = request.form.get('prompt')
    if not prompt: return jsonify({'error': 'Prompt is missing.'}), 400
    try: 
        filename = generate_image_from_prompt(prompt, app.config['GENERATED_FOLDER'])
        
        predictions_data = {
            "source": "generation-txt2img",
            "prompt": prompt,
            "gemini": { "caption": "AI Generated Image" }
        }
        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    "INSERT INTO upload_history (filename, predictions) VALUES (?, ?)",
                    (filename, json.dumps(predictions_data))
                )
                conn.commit()
            except Exception as e:
                print(f"[ERROR] Failed to save generated image to history: {e}")
                conn.rollback()
            finally:
                conn.close()
                
        return jsonify({'image_url': f"/generated/{filename}"})
    except Exception as e: 
        print(f"[ERROR] Image generation failed: {e}"); 
        return jsonify({'error': str(e)}), 500

@app.route('/generate-prompt-idea', methods=['POST'])
@login_required
def generate_prompt_idea():
    data = request.get_json(); idea = data.get('idea')
    if not idea: return jsonify({'error': 'No idea provided'}), 400
    try:
        prompt_template = (
    "Act as a technical prompt generator for Stable Diffusion XL. "
    "Translate the concept '{idea}' into a strict, comma-separated list of weighted tags. "
    "Structure the output strictly as: '(Main Subject:1.3), (Action), (Context), (Art Style), (Lighting), (Camera/View), (Quality Boosters)'. "
    "Use emphasis syntax like '(keyword:1.2)' for the main subject. "
    "Include specific quality tags: '8k, masterpiece, best quality, uhd, hdr, sharp focus, highly detailed'. "
    "CRITICAL: Do not use natural language, filler words, or sentences. Do not say 'A picture of'. "
    "Return ONLY the raw prompt string."
)

        formatted_prompt = prompt_template.format(idea=idea)
        generated_prompt = get_gemini_text_prompt(formatted_prompt)
        if generated_prompt.startswith("Error:"): raise Exception(generated_prompt)
        return jsonify({'prompt': generated_prompt.strip()})
    except Exception as e: print(f"[ERROR] Prompt idea generation failed: {e}"); return jsonify({'error': 'Failed to generate prompt idea.'}), 500

@app.route('/generate-image-from-image', methods=['POST'])
@login_required
def generate_image_from_image_api():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    try:
        # 1. Save the uploaded (original) image
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(original_path)
        original_image_url = f"/uploads/{unique_filename}"

        # 2. Use Gemini to generate a prompt *from* this image
        replication_prompt = (
            "Analyze this image and generate a highly detailed, comma-separated "
            "Stable Diffusion prompt that would recreate it. Focus on subject, "
            "setting, art style (e.g., 'photorealistic', 'oil painting', 'anime'), "
            "colors, lighting, and composition. The prompt should be a single, "
            "long string of keywords. Do not include any other text, "
            "explanation, or preamble. Just return the prompt."
        )
        
        generated_prompt = get_gemini_analysis(original_path, replication_prompt)
        
        if generated_prompt.startswith("Error:"):
            raise Exception(f"Gemini failed to create a prompt: {generated_prompt}")

        cleaned_prompt = generated_prompt.strip().replace('\n', ', ').replace('*', '')
        print(f"[INFO] Generated replication prompt: {cleaned_prompt}")

        # 3. Use the new prompt to generate an image
        generated_filename = generate_image_from_prompt(
            cleaned_prompt, 
            app.config['GENERATED_FOLDER']
        )
        
        generated_image_url = f"/generated/{generated_filename}"
        
        predictions_data = {
            "source": "generation-i2i",
            "prompt": cleaned_prompt,
            "gemini": { "caption": "AI Image-to-Image" }
        }
        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    "INSERT INTO upload_history (filename, predictions) VALUES (?, ?)",
                    (generated_filename, json.dumps(predictions_data))
                )
                conn.commit()
            except Exception as e:
                print(f"[ERROR] Failed to save generated i2i to history: {e}")
                conn.rollback()
            finally:
                conn.close()

        # 4. Return both URLs to the frontend
        return jsonify({
            'original_image_url': original_image_url,
            'generated_image_url': generated_image_url
        })

    except Exception as e:
        print(f"[ERROR] Image-to-image generation failed: {e}")
        return jsonify({'error': str(e)}), 500


# --- Advanced Editing API ---

def _get_file_paths_from_urls(data):
    if 'original_url' not in data or 'mask_url' not in data:
        raise Exception("Missing original_url or mask_url in request.")
    original_filename = os.path.basename(data['original_url'])
    mask_filename = os.path.basename(data['mask_url'])
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    mask_path = os.path.join(app.config['PROCESSED_FOLDER'], mask_filename)
    if not os.path.exists(original_path):
        raise Exception(f"Original file not found on server: {original_path}")
    if not os.path.exists(mask_path):
        raise Exception(f"Mask file not found on server: {mask_path}")
    return original_path, mask_path

def _save_and_get_url(pil_image: Image.Image, base_filename: str, effect_name: str) -> dict:
    ext = ".png" if pil_image.mode == 'RGBA' else ".jpg"
    new_filename = f"{os.path.splitext(base_filename)[0]}_{effect_name}{ext}"
    save_path = os.path.join(app.config['PROCESSED_FOLDER'], new_filename)
    if ext == ".jpg":
        pil_image.convert('RGB').save(save_path, "JPEG", quality=95)
    else:
        pil_image.save(save_path, "PNG")
    return {
        'status': 'success',
        'processed_image_url': f"/processed/{new_filename}",
        'filename': new_filename
    }

@app.route('/edit/remove-bg', methods=['POST'])
@login_required
def edit_remove_bg():
    try:
        data = request.get_json()
        original_path, mask_path = _get_file_paths_from_urls(data)
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
        
        # --- NEW: Get intensity from request, default to 50 ---
        intensity = int(data.get('intensity', 50)) 
        
        # --- NEW: Pass intensity to the processor ---
        pil_image = image_editor_processor.apply_blur_background(original_path, mask_path, intensity)
        
        base_filename = os.path.basename(original_path)
        return jsonify(_save_and_get_url(pil_image, base_filename, "bg_blurred"))
    except Exception as e:
        print(f"[ERROR] /edit/blur-bg failed: {e}")
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
        cursor.execute("SELECT filename, predictions FROM upload_history WHERE id = ?", (history_id,))
        record = cursor.fetchone()
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
            
        original_filename = record['filename']
        predictions_json = json.loads(record['predictions'])

        cursor.execute("DELETE FROM upload_history WHERE id = ?", (history_id,))
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

# Inside projectp10/app.py

@app.route('/add_custom_tag', methods=['POST'])
@login_required
def add_custom_tag():
    data = request.get_json()
    tag_name = data.get('tag')
    filename = data.get('filename')
    
    if not tag_name or not filename:
        return jsonify({'error': 'Missing data'}), 400
        
    # Find the image entry in history
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
        
    try:
        cursor = conn.cursor()
        # Get image ID
        cursor.execute("SELECT id FROM upload_history WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        
        if row:
            image_id = row['id']
            # Save the new Manual tag
            cursor.execute(
                "INSERT INTO image_tags (image_id, tag_name, source, confidence) VALUES (?, ?, ?, ?)",
                (image_id, tag_name, 'Manual', 1.0)
            )
            conn.commit()
            return jsonify({'status': 'success', 'tag': tag_name})
        else:
            return jsonify({'error': 'Image not found in history'}), 404
            
    except Exception as e:
        print(f"[ERROR] Failed to add manual tag: {e}")
        return jsonify({'error': str(e)}), 500
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