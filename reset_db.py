from app import app, db

# WARNING: This will delete all existing users in your PostgreSQL database.
# It will NOT affect your image history (which is stored in SQLite).

with app.app_context():
    print("Dropping existing tables...")
    db.drop_all()  # This drops the 'user' table
    
    print("Creating new tables with correct schema...")
    db.create_all() # This recreates it with email, password_hash, etc.
    
    print("✅ Database reset successfully! You can now run app.py.")