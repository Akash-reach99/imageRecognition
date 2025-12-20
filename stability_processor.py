# stability_processor.py (updated for router.huggingface.co)
import requests
import os
import uuid
import time
from typing import Optional
from dotenv import load_dotenv  # <--- Add this

load_dotenv()  # <--- Load variables from .env

HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    # Optional: Print a warning or set a dummy value if you want, 
    # but better to fail if the key is missing.
    print("[WARNING] HF_API_KEY not found in .env file.")
# -------------------------------------------

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Use Hugging Face Router for inference: https://router.huggingface.co/hf-inference/models/<model-id>
ROUTER_BASE = "https://router.huggingface.co/hf-inference/models"

TEXT_TO_IMAGE_API_URL = f"{ROUTER_BASE}/stabilityai/stable-diffusion-xl-base-1.0"
IMAGE_TO_IMAGE_API_URL = f"{ROUTER_BASE}/stabilityai/stable-diffusion-xl-refiner-1.0"
UPSCALING_API_URL = f"{ROUTER_BASE}/stabilityai/stable-diffusion-x4-upscaler"

# small helper to do post with timeout and optional stream
def _post(url: str, headers: dict, **kwargs) -> requests.Response:
    return requests.post(url, headers=headers, timeout=120, **kwargs)

def _handle_api_error(response: requests.Response) -> str:
    """A helper function to parse API errors robustly."""
    error_message = f"API Error ({response.status_code})"
    try:
        error_data = response.json()
        api_error = error_data.get("error", "An unknown error occurred")
        # sometimes errors are lists
        if isinstance(api_error, list):
            api_error = api_error[0]
        estimated_time = error_data.get("estimated_time", 0)
        if estimated_time and estimated_time > 0:
            error_message += f": {api_error} The model is currently loading, please try again in {int(estimated_time)} seconds."
        else:
            error_message += f": {api_error}"
    except Exception:
        # fallback to raw text (often HTML or plain text)
        error_message += f": {response.text}"
    return error_message

def generate_image_from_prompt(prompt: str, save_path_dir: str, params: Optional[dict] = None) -> str:
    """
    Generates an image from a text prompt using the text-to-image model.
    Sends JSON {"inputs": prompt, "parameters": ...}
    """
    payload = {"inputs": prompt}
    if params:
        payload["parameters"] = params

    response = _post(TEXT_TO_IMAGE_API_URL, headers=HEADERS, json=payload)
    # many HF image models return binary image bytes with content-type image/*
    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
        filename = f"{uuid.uuid4()}.jpg"
        save_path = os.path.join(save_path_dir, filename)
        with open(save_path, "wb") as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(_handle_api_error(response))

def generate_image_from_image(image_path: str, prompt: str, save_path_dir: str, params: Optional[dict] = None) -> str:
    """
    Generates an image variation (img2img/refiner) based on an input image + prompt.
    Uses multipart/form-data: files={'image': open(...)} and data={'inputs': prompt, 'parameters': ...}
    """
    with open(image_path, "rb") as f:
        files = {"image": (os.path.basename(image_path), f, "application/octet-stream")}
        data = {"inputs": prompt}
        if params:
            # Hugging Face router accepts a JSON string in 'parameters' for many models
            import json
            data["parameters"] = json.dumps(params)

        # IMPORTANT: don't set Content-Type here; requests will set the multipart boundary.
        response = _post(IMAGE_TO_IMAGE_API_URL, headers=HEADERS, files=files, data=data)

    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith(("image/", "image/")):
        filename = f"{uuid.uuid4()}.jpg"
        save_path = os.path.join(save_path_dir, filename)
        with open(save_path, "wb") as out:
            out.write(response.content)
        return filename
    else:
        raise Exception(_handle_api_error(response))

def upscale_image(image_path: str, save_path_dir: str, params: Optional[dict] = None) -> str:
    """
    Upscales an image using the x4 upscaler model.
    Sends multipart form with the image file; many upscalers accept optional parameters.
    """
    with open(image_path, "rb") as f:
        files = {"image": (os.path.basename(image_path), f, "application/octet-stream")}
        data = {}
        if params:
            import json
            data["parameters"] = json.dumps(params)

        response = _post(UPSCALING_API_URL, headers=HEADERS, files=files, data=data)

    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
        filename = f"upscaled_{uuid.uuid4()}.jpg"
        save_path = os.path.join(save_path_dir, filename)
        with open(save_path, "wb") as out:
            out.write(response.content)
        return filename
    else:
        raise Exception(_handle_api_error(response))

# Example usage (do not include API key in code repos)
if __name__ == "__main__":
    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)

    # small smoke test - you'll want to run these selectively
    try:
        img_filename = generate_image_from_prompt("A fantasy castle on a cliff at sunset, ultra-detailed", out_dir)
        print("Text->Image saved to:", img_filename)
    except Exception as e:
        print("Text->Image error:", e)

    # For img2img/upscale use real local files and smaller tests
