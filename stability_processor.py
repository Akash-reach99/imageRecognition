# stability_processor.py (updated with FALLBACK support for free models)
import requests
import os
import uuid
import time
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    print("[WARNING] HF_API_KEY not found in .env file.")

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Use Hugging Face Router for inference
ROUTER_BASE = "https://router.huggingface.co/hf-inference/models"

# ============================================================
# FALLBACK MODEL CHAINS (Free alternatives on HuggingFace)
# If one model fails/rate-limits, the next one is tried automatically
# ============================================================

# Text-to-Image models (ordered by quality, all FREE on HF Inference API)
TEXT_TO_IMAGE_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",      # Primary: Stability AI SDXL
    "black-forest-labs/FLUX.1-schnell",              # FLUX.1 Schnell (fast, high quality)
    "prompthero/openjourney-v4",                     # OpenJourney (Midjourney-style)
    "dreamlike-art/dreamlike-photoreal-2.0",         # Dreamlike Photoreal
    "runwayml/stable-diffusion-v1-5",                # SD 1.5 (reliable fallback)
    "CompVis/stable-diffusion-v1-4",                 # SD 1.4 (very stable)
]

# Image-to-Image models
IMAGE_TO_IMAGE_MODELS = [
    "stabilityai/stable-diffusion-xl-refiner-1.0",   # Primary: SDXL Refiner
    "runwayml/stable-diffusion-v1-5",                # SD 1.5 img2img
    "timbrooks/instruct-pix2pix",                    # InstructPix2Pix (edit with text)
    "CompVis/stable-diffusion-v1-4",                 # SD 1.4 fallback
]

# Upscaling models
UPSCALING_MODELS = [
    "stabilityai/stable-diffusion-x4-upscaler",      # Primary: SD x4 upscaler
    "caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr", # Swin2SR (good quality)
]

# Legacy single URLs (for backward compatibility)
TEXT_TO_IMAGE_API_URL = f"{ROUTER_BASE}/{TEXT_TO_IMAGE_MODELS[0]}"
IMAGE_TO_IMAGE_API_URL = f"{ROUTER_BASE}/{IMAGE_TO_IMAGE_MODELS[0]}"
UPSCALING_API_URL = f"{ROUTER_BASE}/{UPSCALING_MODELS[0]}"

# ============================================================
# POLLINATIONS AI - UPDATED INTEGRATION (Gen.pollinations.ai)
# https://pollinations.ai - Generative AI Platform
# ============================================================
POLLINATIONS_API_URL = "https://gen.pollinations.ai/image"
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")

# Pollinations models
POLLINATIONS_MODELS = ["flux", "z-image-turbo", "kp25", ""]  # Updated model list based on new docs compatibility



def _optimize_prompt_for_pollinations(original_prompt: str, style: str = None) -> str:
    """
    Uses Gemini/Groq to optimize a prompt specifically for Pollinations AI.
    Adds quality keywords and format for better output.
    """
    try:
        from ai_provider import get_ai_text_prompt
        
        optimization_request = f"""You are an expert at writing prompts for AI image generation.
Convert this user prompt into an optimized prompt for Pollinations AI (uses FLUX/Stable Diffusion models).

User's prompt: "{original_prompt}"
{f'Style requested: {style}' if style else ''}

Rules:
1. Keep the main subject and intent
2. Add quality keywords: "highly detailed, 8k, sharp focus, professional"
3. Add lighting/atmosphere: "cinematic lighting, dramatic"
4. Make it descriptive but under 200 words
5. Output ONLY the optimized prompt, nothing else

Optimized prompt:"""
        
        optimized = get_ai_text_prompt(optimization_request)
        
        if optimized and not optimized.startswith("Error"):
            minimized = optimized.strip().strip('"').strip("'")
            print(f"[POLLINATIONS] Optimized prompt: {minimized[:100]}...")
            return minimized
        else:
            return _fallback_optimize_prompt(original_prompt, style)
            
    except Exception as e:
        print(f"[POLLINATIONS] Prompt optimization failed: {e}, using fallback")
        return _fallback_optimize_prompt(original_prompt, style)

def _fallback_optimize_prompt(prompt: str, style: str = None) -> str:
    quality_suffix = ", highly detailed, 8k resolution, sharp focus, professional quality, cinematic lighting"
    if style and style != "none":
        # Prepend style for better adherence in Flux
        return f"{style} style, {prompt}{quality_suffix}"
    else:
        return f"{prompt}{quality_suffix}"

def _generate_with_pollinations(prompt: str, save_path_dir: str, width: int = 1024, height: int = 1024, style: str = None, optimize_prompt: bool = False, model: str = None) -> str:
    """
    Generate image using the new gen.pollinations.ai API.
    Requires POLLINATIONS_API_KEY in .env for best results.
    """
    import urllib.parse
    
    if optimize_prompt:
        final_prompt = _optimize_prompt_for_pollinations(prompt, style)
    else:
        final_prompt = _fallback_optimize_prompt(prompt, style)
    
    encoded_prompt = urllib.parse.quote(final_prompt)
    
    headers = {
        "User-Agent": "ImageRecognizer/1.0"
    }
    
    if POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
        print("[POLLINATIONS] Using authenticated request")
    else:
        print("[POLLINATIONS] WARNING: No API Key found. Request might be rate-limited or fail.")

    last_error = None
    
    # Copy models list to avoid modifying global list permanently
    current_models = POLLINATIONS_MODELS.copy()
    
    # 1. Explicit Model Request (from Frontend Dropdown)
    if model:
        print(f"[POLLINATIONS] Explicit model requested: {model}")
        # Insert at front to try first
        if model in current_models:
             current_models.insert(0, current_models.pop(current_models.index(model)))
        else:
             # If not in list, just add it to front
             current_models.insert(0, model)
             
    # 2. Style-Based Auto-Selection (only if no specific model forced OR if we want smart fallbacks)
    # SPECIAL FIX: Artistic / Stylized styles work best on 'turbo' (SDXL) rather than Flux
    # Flux is great for Photorealism/Cinematic, but SDXL/Turbo is better for specific art styles.
    elif style and any(x in style.lower() for x in ['pixel', '8-bit', 'retro', 'game', 'anime', 'manga', 'illustration', 'painting', 'digital', 'oil', 'cyberpunk', 'poly']):
        print(f"[POLLINATIONS] Detected '{style}' style - Prioritizing 'z-image-turbo' (SDXL) model for better results.")
        if "z-image-turbo" in current_models:
            current_models.insert(0, current_models.pop(current_models.index("z-image-turbo")))
    
    # Try models in order
    for model in current_models:
        # Construct URL: https://gen.pollinations.ai/image/{prompt}
        # Query params: width, height, seed, model, nologo, etc.
        url = f"{POLLINATIONS_API_URL}/{encoded_prompt}"
        
        params = {
            "width": width,
            "height": height,
            "nologo": "true",
            "seed": int(time.time()), # Random seed
            "model": model or "flux"
        }

        print(f"[POLLINATIONS] Requesting: {url} (model={params['model']})...")
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=120)
            
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                filename = f"{uuid.uuid4()}.jpg"
                save_path = os.path.join(save_path_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(response.content)
                print(f"[POLLINATIONS] SUCCESS with model: {model}")
                return filename
            
            elif response.status_code == 401:
                print(f"[POLLINATIONS] Authentication failed (401). Check your API Key.")
                last_error = "Authentication failed (401)"
                # If auth fails, maybe try without auth? Unlikely to work if it's required, but we break to next model/logic
                break 

            else:
                error_msg = f"Status {response.status_code}"
                try:
                    error_msg += f": {response.text[:200]}"
                except: pass
                print(f"[POLLINATIONS] Failed: {error_msg}")
                last_error = error_msg
                continue
                
        except Exception as e:
            print(f"[POLLINATIONS] Exception: {e}")
            last_error = str(e)
            continue

    raise Exception(f"Pollinations generation failed: {last_error}")

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

def generate_image_from_prompt(prompt: str, save_path_dir: str, params: Optional[dict] = None, style: str = None, model_provider: str = "auto") -> str:
    """
    Generates an image from a text prompt using text-to-image models.
    
    model_provider options:
    - "auto": Try HuggingFace first, fallback to Pollinations
    - "huggingface": Only use HuggingFace models
    - "pollinations": Only use Pollinations (free, fast)
    """
    payload = {"inputs": prompt}
    if params:
        payload["parameters"] = params

    last_error = None
    hf_quota_exceeded = False
    
    # If user explicitly chose Pollinations, skip HuggingFace
    if model_provider and model_provider.startswith("pollinations"):
        print(f"[IMAGE GEN] Using Pollinations AI ({model_provider})...")
        
        # Explicit model selection from frontend
        kwargs = {}
        if model_provider == "pollinations_turbo":
            kwargs["model"] = "z-image-turbo"
        elif model_provider == "pollinations_flux":
            kwargs["model"] = "flux"
        # Legacy/General fallback
        elif model_provider == "pollinations":
             # Default to turbo for better style adherence as per user request
             kwargs["model"] = "z-image-turbo"

        try:
            return _generate_with_pollinations(
                prompt, 
                save_path_dir, 
                style=style,
                optimize_prompt=False, # We do our own optimization
                model=kwargs.get("model", "z-image-turbo") # Pass explicit model
            )
        except Exception as e:
            raise Exception(f"Pollinations failed: {e}")
    
    # Try HuggingFace models (if auto or huggingface)
    if model_provider in ["auto", "huggingface"]:
        for model_id in TEXT_TO_IMAGE_MODELS:
            api_url = f"{ROUTER_BASE}/{model_id}"
            try:
                print(f"[IMAGE GEN] Trying model: {model_id}")
                response = _post(api_url, headers=HEADERS, json=payload)
                
                # Success - got an image back
                if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    filename = f"{uuid.uuid4()}.jpg"
                    save_path = os.path.join(save_path_dir, filename)
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    print(f"[IMAGE GEN] SUCCESS with model: {model_id}")
                    return filename
                
                # HuggingFace quota exceeded (402) - skip to Pollinations immediately
                elif response.status_code == 402:
                    print(f"[IMAGE GEN] HuggingFace quota exceeded! Switching to FREE Pollinations AI...")
                    hf_quota_exceeded = True
                    break
                
                # Model is loading - skip to next (don't wait)
                elif response.status_code == 503:
                    error_msg = _handle_api_error(response)
                    print(f"[IMAGE GEN] Model loading/busy ({model_id})")
                    last_error = error_msg
                    continue
                
                # Rate limit or other error - try next model
                elif response.status_code in [429, 500, 502, 504]:
                    error_msg = _handle_api_error(response)
                    print(f"[IMAGE GEN] Rate limit/error ({model_id})")
                    last_error = error_msg
                    continue
                
                # Other error - still try next
                else:
                    error_msg = _handle_api_error(response)
                    print(f"[IMAGE GEN] Failed ({model_id}): {error_msg}")
                    last_error = error_msg
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"[IMAGE GEN] Timeout ({model_id})")
                last_error = f"Timeout with {model_id}"
                continue
            except Exception as e:
                print(f"[IMAGE GEN] Exception ({model_id}): {e}")
                last_error = str(e)
                continue
    
    # If user chose huggingface only and it failed, don't fallback UNLESS quota exceeded
    if model_provider == "huggingface" and not hf_quota_exceeded:
        raise Exception(f"HuggingFace generation failed: {last_error}")
    
    # FINAL FALLBACK: Pollinations AI (FREE, with simple keyword optimization!)
    print("[IMAGE GEN] Trying Pollinations AI fallback...")
    try:
        # Pass style to Pollinations - uses simple keywords, not Gemini
        return _generate_with_pollinations(prompt, save_path_dir, style=style, optimize_prompt=False)
    except Exception as pollinations_error:
        # All options failed
        raise Exception(f"All image generation failed. HuggingFace: {last_error}. Pollinations: {pollinations_error}")

def generate_image_from_image(image_path: str, prompt: str, save_path_dir: str, params: Optional[dict] = None, style: str = None, model_provider: str = "auto") -> str:
    """
    Generates an image variation (img2img) based on an input image + prompt.
    FALLBACK ORDER:
    1. HuggingFace img2img models
    2. Pollinations AI (uses Gemini to describe source image + style)
    """
    import json
    
    last_error = None
    hf_failed = False
    
    # Parse model provider to set specific Pollinations model
    kwargs = {}
    if model_provider == "pollinations_turbo":
        kwargs["model"] = "z-image-turbo"
    elif model_provider == "pollinations_flux":
        kwargs["model"] = "flux"
    elif model_provider == "pollinations": # Legacy fallback
        kwargs["model"] = "z-image-turbo"
        
    # Skip HuggingFace if Pollinations is explicitly requested
    if model_provider and model_provider.startswith("pollinations"):
         print(f"[IMG2IMG] User selected Pollinations ({model_provider}). Skipping HuggingFace.")
         hf_failed = True # Force fallback logic immediately
    else:
        # Try HuggingFace img2img models first
        for model_id in IMAGE_TO_IMAGE_MODELS:
            api_url = f"{ROUTER_BASE}/{model_id}"
            try:
                print(f"[IMG2IMG] Trying model: {model_id}")
                
                with open(image_path, "rb") as f:
                    files = {"image": (os.path.basename(image_path), f, "application/octet-stream")}
                    data = {"inputs": prompt}
                    if params:
                        data["parameters"] = json.dumps(params)
                    
                    response = _post(api_url, headers=HEADERS, files=files, data=data)
                
                # Success
                if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    filename = f"{uuid.uuid4()}.jpg"
                    save_path = os.path.join(save_path_dir, filename)
                    with open(save_path, "wb") as out:
                        out.write(response.content)
                    print(f"[IMG2IMG] SUCCESS with model: {model_id}")
                    return filename
                
                # HuggingFace quota exceeded
                elif response.status_code == 402:
                    print(f"[IMG2IMG] HuggingFace quota exceeded! Switching to Pollinations...")
                    hf_failed = True
                    break
                
                # Model loading/busy or error - try next
                elif response.status_code in [429, 500, 502, 503, 504]:
                    error_msg = _handle_api_error(response)
                    print(f"[IMG2IMG] Model busy/error ({model_id})")
                    last_error = error_msg
                    continue
                
                else:
                    error_msg = _handle_api_error(response)
                    print(f"[IMG2IMG] Failed ({model_id}): {error_msg}")
                    last_error = error_msg
                    continue
                
            except requests.exceptions.Timeout:
                print(f"[IMG2IMG] Timeout ({model_id})")
                last_error = f"Timeout with {model_id}"
                continue
            except Exception as e:
                print(f"[IMG2IMG] Exception ({model_id}): {e}")
                last_error = str(e)
                continue
    
    # FALLBACK: Use Pollinations with AI-described prompt from source image
    print("[IMG2IMG] Trying Pollinations AI fallback...")
    try:
        from ai_provider import generate_prompt_from_image
        
        # Get Gemini/Groq to describe the source image and create a prompt
        print("[IMG2IMG] Using AI to describe source image for Pollinations...")
        image_description = generate_prompt_from_image(image_path, prompt_type="recreate", target_style=style)
        
        if image_description and not image_description.startswith("Error"):
            # Combine with user's original prompt/style
            if prompt and prompt.strip():
                combined_prompt = f"{image_description}, {prompt}"
            else:
                combined_prompt = image_description
            
            # Generate with Pollinations
            pollinations_model = kwargs.get("model", None)
            
            # If provider was specific (pollinations_turbo/flux), kwargs['model'] should already be set correctly
            # by the caller (generate_image_from_prompt logic isn't fully reused here, so we must ensure consistency)
            
            return _generate_with_pollinations(combined_prompt, save_path_dir, style=style, optimize_prompt=False, model=pollinations_model)
        else:
            raise Exception(f"Could not describe source image: {image_description}")
            
    except Exception as pollinations_error:
        raise Exception(f"All img2img failed. HuggingFace: {last_error}. Pollinations: {pollinations_error}")

def upscale_image(image_path: str, save_path_dir: str, params: Optional[dict] = None) -> str:
    """
    Upscales an image using upscaler models.
    FALLBACK: Tries each model in UPSCALING_MODELS until one succeeds.
    """
    import json
    
    last_error = None
    
    for model_id in UPSCALING_MODELS:
        api_url = f"{ROUTER_BASE}/{model_id}"
        try:
            print(f"[UPSCALE] Trying model: {model_id}")
            
            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "application/octet-stream")}
                data = {}
                if params:
                    data["parameters"] = json.dumps(params)
                
                response = _post(api_url, headers=HEADERS, files=files, data=data)
            
            # Success
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                filename = f"upscaled_{uuid.uuid4()}.jpg"
                save_path = os.path.join(save_path_dir, filename)
                with open(save_path, "wb") as out:
                    out.write(response.content)
                print(f"[UPSCALE] ✓ Success with model: {model_id}")
                return filename
            
            # Model loading/busy or error - try next
            elif response.status_code in [429, 500, 502, 503, 504]:
                error_msg = _handle_api_error(response)
                print(f"[UPSCALE] Model busy/error ({model_id}): {error_msg}")
                last_error = error_msg
                continue
            
            else:
                error_msg = _handle_api_error(response)
                print(f"[UPSCALE] Failed ({model_id}): {error_msg}")
                last_error = error_msg
                continue
                
        except requests.exceptions.Timeout:
            print(f"[UPSCALE] Timeout ({model_id})")
            last_error = f"Timeout with {model_id}"
            continue
        except Exception as e:
            print(f"[UPSCALE] Exception ({model_id}): {e}")
            last_error = str(e)
            continue
    
    raise Exception(f"All upscaling models failed. Last error: {last_error}")

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
