# imagga_processor.py
import requests
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv # <--- Add this

load_dotenv() # <--- Load variables

# 🔑 Replace with your Imagga API credentials
API_KEY = os.getenv('IMAGGA_API_KEY')
API_SECRET = os.getenv('IMAGGA_API_SECRET')

# --- THIS IS THE CORRECTED LINE ---
UPLOAD_URL = "https://api.imagga.com/v2/uploads"
TAGGING_URL = "https://api.imagga.com/v2/tags"

def get_imagga_tags(image_path: str, limit=3) -> list:
    """
    Uploads an image to Imagga and gets its top 'limit' tags.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] Imagga: Image file not found at {image_path}")
        return []

    try:
        # Step 1: Upload image
        with open(image_path, "rb") as image_file:
            response = requests.post(
                UPLOAD_URL,
                auth=HTTPBasicAuth(API_KEY, API_SECRET),
                files={"image": image_file}
            )
            response.raise_for_status() # Raise an error for bad responses
            upload_result = response.json()

        # Check if upload worked
        if "result" not in upload_result or "upload_id" not in upload_result["result"]:
            print(f"❌ Imagga upload failed: {upload_result}")
            return []
        
        upload_id = upload_result["result"]["upload_id"]
        print(f"✅ Imagga upload successful! Upload ID: {upload_id}")

        # Step 2: Get tags using the upload_id
        params = {
            "image_upload_id": upload_id,
            "limit": limit  # <-- This uses your "top 5" request
        }
        response = requests.get(TAGGING_URL, auth=HTTPBasicAuth(API_KEY, API_SECRET), params=params)
        response.raise_for_status()
        tags_result = response.json()

        # Format and return the tags
        formatted_tags = []
        if "result" in tags_result and "tags" in tags_result["result"]:
            for tag in tags_result["result"]["tags"]:
                formatted_tags.append({
                    "name": tag["tag"]["en"],
                    "confidence": round(tag["confidence"], 2)
                })
        
        return formatted_tags

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Imagga API request failed: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred in get_imagga_tags: {e}")
        return []