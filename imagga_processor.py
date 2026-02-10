# imagga_processor.py
import requests
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()

# 🔑 Replace with your Imagga API credentials
API_KEY = os.getenv('IMAGGA_API_KEY')
API_SECRET = os.getenv('IMAGGA_API_SECRET')

UPLOAD_URL = "https://api.imagga.com/v2/uploads"
TAGGING_URL = "https://api.imagga.com/v2/tags"


def _prepare_image(image_path: str, max_dim: int = 1536, quality: int = 85) -> bytes:
    """
    Preprocesses image for optimal API performance.
    - Resizes to max_dim if larger
    - Compresses with JPEG quality
    - Returns bytes for upload
    """
    img = Image.open(image_path)
    original_size = img.size
    
    # Convert to RGB (ensures JPEG compatibility)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize if needed
    width, height = img.size
    if max(width, height) > max_dim:
        if width > height:
            new_width = max_dim
            new_height = int(height * (max_dim / width))
        else:
            new_height = max_dim
            new_width = int(width * (max_dim / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"[DEBUG] Imagga: Resized image from {original_size[0]}x{original_size[1]} to {new_width}x{new_height}")
    
    # Compress to JPEG bytes
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    buffer.seek(0)
    return buffer


def get_imagga_tags(image_path: str, limit=3) -> list:
    """
    Uploads an image to Imagga and gets its top 'limit' tags.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] Imagga: Image file not found at {image_path}")
        return []

    try:
        # Step 1: Preprocess and upload image
        image_buffer = _prepare_image(image_path)
        response = requests.post(
            UPLOAD_URL,
            auth=HTTPBasicAuth(API_KEY, API_SECRET),
            files={"image": ("image.jpg", image_buffer, "image/jpeg")}
        )
        response.raise_for_status()
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
            "limit": limit
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
