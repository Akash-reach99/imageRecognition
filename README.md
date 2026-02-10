# AI Image Recognition & Analysis Suite

## Project Overview

A comprehensive web-based AI image analysis platform that combines multiple AI models and services to provide intelligent image analysis, object detection, segmentation, color palette extraction, and AI-powered image generation capabilities.

---

## Features

### Core Functionality
- Multi-Model Image Analysis (Gemini, Groq, YOLO)
- Object Detection & Recognition
- Image Segmentation
- Color Palette Extraction
- AI-Powered Image Generation
- Image Editing Tools
- Analysis History with Search
- PDF Report Generation

### User Management
- User Registration with Email OTP Verification
- Secure Login (Password + OTP Options)
- Role-Based Access Control (User/Admin)
- Session Management

### Image Processing
- Upload & Analyze Images
- Real-time Object Detection (YOLOv8)
- Semantic Segmentation
- EXIF Data Extraction (GPS, Camera Info)
- Tag Normalization & Merging

### AI Integration
- Google Gemini Vision API
- Groq LLaVA Model
- Stability AI (Image Generation)
- Imagga Tagging API
- YOLOv8 Large Models

---

## Technologies Used

### Backend
- Python 3.8+
- Flask (Web Framework)
- Flask-SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Flask-Bcrypt (Password Hashing)
- Flask-Mail (Email Verification)

### Frontend
- HTML5
- CSS3 (Vanilla CSS)
- JavaScript (ES6+)
- Responsive Design

### AI & Machine Learning
- YOLOv8 (Ultralytics)
- Google Gemini API
- Groq API
- Stability AI
- Imagga API
- OpenCV
- Scikit-learn (K-Means Clustering)

### Database
- PostgreSQL (User Management)
- SQLite (Analysis History)

---

## Installation Guide

### Prerequisites

1. Python 3.8 or higher
2. PostgreSQL Database
3. Gmail Account (for email verification)

### Step 1: Clone or Extract Source Code

Extract the project files to your desired location.

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Setup PostgreSQL Database

1. Install PostgreSQL
2. Create a new database:
   ```sql
   CREATE DATABASE image_suite;
   ```
3. Update connection string in `app.py` (line 65) if needed:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:YOUR_PASSWORD@localhost/image_suite'
   ```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# AI API Keys
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
STABILITY_API_KEY=your_stability_api_key_here
IMAGGA_API_KEY=your_imagga_api_key_here
IMAGGA_API_SECRET=your_imagga_api_secret_here

# Email Configuration (Gmail)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_gmail_app_password
```

**Note:** For Gmail, you need to generate an App Password:
1. Enable 2-Factor Authentication on your Google Account
2. Go to: https://myaccount.google.com/apppasswords
3. Generate an App Password for "Mail"
4. Use this password in the `.env` file

### Step 5: Download YOLO Models

The project requires two YOLO model files:
- `yolov8l.pt` (Detection)
- `yolov8l-seg.pt` (Segmentation)

Place these files in the project root directory.

**Download Links:**
- Visit: https://github.com/ultralytics/ultralytics
- Or the models will auto-download on first run

### Step 6: Initialize Database Tables

Run the application for the first time to create all necessary tables:

```bash
python app.py
```

The application will automatically:
- Create SQLite database for analysis history
- Create PostgreSQL tables for user management
- Create required directories (uploads, processed, generated)

### Step 7: Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

---

## Project Structure

```
imageRecognition/
│
├── static/                      # Frontend Assets
│   ├── analyzer.js             # Image analyzer functionality
│   ├── edit.js                 # Image editing tools
│   ├── generate.js             # AI image generation
│   ├── global.js               # Global utilities
│   ├── history.js              # History page functionality
│   ├── image_creator.js        # Image creation tools
│   ├── palette.js              # Color palette generator
│   ├── script.js               # Main JavaScript
│   ├── style.css               # Main stylesheet
│   ├── generated/              # AI-generated images storage
│   ├── processed/              # Processed analysis results
│   └── uploads/                # User uploaded images
│
├── templates/                   # HTML Templates
│   ├── _nav.html               # Navigation component
│   ├── about.html              # About page
│   ├── admin.html              # Admin dashboard
│   ├── analyzer.html           # Image analyzer page
│   ├── dashboard.html          # User dashboard
│   ├── edit.html               # Image editor
│   ├── generate.html           # Image generation page
│   ├── history.html            # Analysis history
│   ├── history_detail.html     # Detailed analysis view
│   ├── index.html              # Landing page
│   ├── login.html              # Login page
│   ├── palette.html            # Color palette generator
│   ├── register.html           # Registration page
│   ├── result.html             # Analysis results
│   ├── verify_otp.html         # OTP verification
│   └── verify_register.html    # Registration verification
│
├── instance/                    # Instance-specific data
│   └── users.db                # User database (auto-created)
│
├── app.py                       # Main Flask application
├── ai_provider.py               # AI provider integration
├── gemini_processor.py          # Google Gemini processor
├── groq_processor.py            # Groq API processor
├── image_editor_processor.py    # Image editing functions
├── imagga_processor.py          # Imagga API integration
├── stability_processor.py       # Stability AI integration
│
├── yolov8l.pt                   # YOLO detection model
├── yolov8l-seg.pt               # YOLO segmentation model
│
├── .env                         # Environment variables (create this)
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── analysis_history.db          # Analysis history database (auto-created)
└── README.md                    # This file
```

---

## Usage Guide

### User Registration

1. Navigate to the registration page
2. Enter username, email, and password
3. Receive OTP via email
4. Verify OTP to complete registration

### User Login

Two login methods available:
1. **Password Login:** Username/Email + Password
2. **OTP Login:** Email-based one-time password

### Image Analysis

1. Go to "Analyzer" page
2. Upload an image
3. Select analysis options:
   - AI Analysis (Gemini/Groq)
   - Object Detection (YOLO)
   - Segmentation
   - Color Palette
   - EXIF Data
4. View comprehensive analysis results
5. Download PDF report

### Image Generation

1. Navigate to "Generate" page
2. Choose generation method:
   - Text-to-Image
   - Image-to-Image
3. Enter prompt or upload reference image
4. Customize settings (style, dimensions)
5. Generate and download images

### Analysis History

1. Go to "History" page
2. View all previous analyses
3. Search by tags or keywords
4. Filter by AI-generated images
5. View detailed reports
6. Download PDF for any analysis

### Color Palette Generator

1. Navigate to "Palette Generator"
2. Upload an image
3. Select number of colors (1-20)
4. View extracted color palette
5. Copy hex codes

---

## API Keys Setup

### Required API Keys

1. **Google Gemini API**
   - Visit: https://makersuite.google.com/app/apikey
   - Create API key for Gemini Pro Vision

2. **Groq API**
   - Visit: https://console.groq.com/
   - Generate API key for LLaVA model

3. **Stability AI**
   - Visit: https://platform.stability.ai/
   - Create account and get API key

4. **Imagga API**
   - Visit: https://imagga.com/
   - Sign up for free tier
   - Get API Key and Secret

---

## Database Schema

### PostgreSQL (User Management)

**Table: user**
- id (Primary Key)
- username (Unique)
- email (Unique)
- password_hash
- is_admin (Boolean)
- created_at (Timestamp)
- otp_secret (6-digit code)
- otp_expiry (Timestamp)

### SQLite (Analysis History)

**Table: upload_history**
- id (Primary Key)
- user_id (Foreign Key)
- filename
- predictions (JSON)
- upload_timestamp

**Table: image_tags**
- id (Primary Key)
- image_id (Foreign Key)
- tag_name
- source (YOLO/Gemini/Imagga)
- confidence

---

## Configuration

### Email Settings (Gmail)

Update in `app.py`:
```python
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
```

### Database Settings

Update in `app.py`:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://USER:PASSWORD@HOST/DATABASE'
```

### File Upload Settings

Update in `app.py`:
```python
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
```

---

## Troubleshooting

### Common Issues

**1. Database Connection Error**
- Ensure PostgreSQL is running
- Verify database credentials in `app.py`
- Check if database `image_suite` exists

**2. Email Not Sending**
- Verify Gmail App Password is correct
- Enable 2-Factor Authentication on Gmail
- Check MAIL_USERNAME and MAIL_PASSWORD in `.env`

**3. YOLO Models Not Found**
- Download `yolov8l.pt` and `yolov8l-seg.pt`
- Place in project root directory
- Models will auto-download on first analysis (requires internet)

**4. API Key Errors**
- Verify all API keys are correct in `.env` file
- Check API quota limits
- Ensure `.env` file is in project root

**5. Import Errors**
- Run: `pip install -r requirements.txt`
- Ensure Python version is 3.8+

---

## Security Notes

### Important Security Practices

1. **Never commit `.env` file to version control**
2. **Change default SECRET_KEY in production**
3. **Use strong passwords for database**
4. **Enable HTTPS in production**
5. **Regularly update dependencies**
6. **Backup databases regularly**

### Default Admin Setup

To create an admin user:
1. Register a normal user account
2. Access PostgreSQL database
3. Run SQL:
   ```sql
   UPDATE "user" SET is_admin = TRUE WHERE username = 'your_username';
   ```

---

## System Requirements

### Minimum Requirements
- CPU: Dual-core processor
- RAM: 4 GB
- Storage: 2 GB free space
- Internet: Required for AI APIs

### Recommended Requirements
- CPU: Quad-core processor
- RAM: 8 GB or higher
- Storage: 5 GB free space (for model caching)
- GPU: Optional (speeds up YOLO processing)

---

## Performance Optimization

### Tips for Better Performance

1. **Image Size:** Upload images under 5 MB for faster processing
2. **Model Selection:** Use appropriate YOLO model size
3. **API Limits:** Monitor API quotas to avoid rate limits
4. **Database:** Regular vacuum/analyze for SQLite
5. **Caching:** Enable browser caching for static assets

---

## Known Limitations

1. Maximum image size: 10 MB
2. YOLO processing speed depends on CPU/GPU
3. Free-tier API limits apply for external services
4. Email OTP expires in 10 minutes
5. History search limited to tag-based queries

---

## Future Enhancements

- [ ] Add support for video analysis
- [ ] Batch image processing
- [ ] Advanced search filters
- [ ] Image comparison tool
- [ ] Export analysis to Excel/CSV
- [ ] Mobile-responsive UI improvements
- [ ] Real-time collaboration features
- [ ] Cloud storage integration

---

## Credits

### AI Services
- Google Gemini
- Groq (LLaVA)
- Stability AI
- Imagga
- Ultralytics YOLOv8

### Frameworks & Libraries
- Flask
- SQLAlchemy
- OpenCV
- ReportLab
- Pillow

---

## License

[Specify your license here - e.g., MIT, GPL, Proprietary]

---

## Contact & Support

**Developer:** [Your Name]  
**Institution:** [Your College/University]  
**Email:** [your.email@example.com]  
**Academic Year:** [2025-2026]

For issues, suggestions, or contributions, please contact the developer.

---

## Acknowledgments

Special thanks to:
- Project Guide: [Guide Name]
- Department: [Department Name]
- Institution: [Institution Name]

---

**Last Updated:** January 23, 2026  
**Version:** 1.0.0
