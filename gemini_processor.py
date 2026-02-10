# ImageRecognizer/gemini_processor.py
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv # <--- Add this

load_dotenv() # <--- Load variables

try:
    # --- PASTE YOUR VALID API KEY HERE ---
    API_KEY = os.getenv('GEMINI_API_KEY')
    
    if not API_KEY:
        raise ValueError("No Gemini API key found in environment variables")

    genai.configure(api_key=API_KEY)
    
    # Use a valid model name
    #model = genai.GenerativeModel('gemini-2.5-flash')

    #model = genai.GenerativeModel('gemini-2.5-flash-lite')

    #model = genai.GenerativeModel('gemma-3-12b-it')

    #model = genai.GenerativeModel('gemini-2.5-pro')

    #model = genai.GenerativeModel('gemini-2.0-flash-exp')

    # The smartest high-limit model (Recommended for detailed analysis)
    #odel = genai.GenerativeModel('gemma-3-27b-it')
    
    # Use Flash model for speed (User Requested)
    # Switched to 1.5-flash due to 2.0-flash-exp rate limits
    #model = genai.GenerativeModel('gemini-1.5-flash')

    # The fast model (Best for simple tasks or slow internet)
    model = genai.GenerativeModel('gemma-3-4b-it')

    # The lightweight model (Extremely fast, less smart)
    #model = genai.GenerativeModel('gemma-3-1b-it')
    
    print("[INFO] Gemini model configured successfully!")


except Exception as e:
    print(f"[ERROR] Failed to configure Gemini Pro: {e}")
    model = None

# --- HELPER FOR OPTIMIZATION ---
def _prepare_image(image_path, max_dim=1024):
    """
    Opens and resizes an image to optimal dimensions for Gemini.
    Reduces upload size while maintaining visual info.
    """
    img = Image.open(image_path)
    
    # Convert to RGB to ensure compatibility (strips alpha)
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    width, height = img.size
    if max(width, height) > max_dim:
        if width > height:
            new_width = max_dim
            new_height = int(height * (max_dim / width))
        else:
            new_height = max_dim
            new_width = int(width * (max_dim / height))
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # print(f"[DEBUG] Resized image from {width}x{height} to {new_width}x{new_height}")
    
    return img

def get_gemini_analysis(image_path, prompt):
    """Analyzes an image using the Gemini model."""
    if model is None:
        return "Error: Gemini model is not available. Check your API key and configuration."

    if not image_path or not os.path.exists(image_path):
        return "Error: Image file not found for analysis."

    try:
        # Optimize: Resize image before sending
        img = _prepare_image(image_path)
        
        # This function sends both the prompt AND the image
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        print(f"[ERROR] Failed to process image with Gemini: {e}")
        return f"An error occurred while processing the image: {e}"

# --- NEW FUNCTION FOR TEXT-ONLY PROMPTS ---
def get_gemini_text_prompt(prompt):
    """Gets a text-only response from the Gemini model."""
    if model is None:
        return "Error: Gemini model is not available. Check your API key and configuration."

    try:
        # This function sends ONLY the prompt
        response = model.generate_content([prompt])
        return response.text
    except Exception as e:
        print(f"[ERROR] Failed to process text prompt with Gemini: {e}")
        return f"An error occurred while processing the prompt: {e}"
# [Existing imports and setup...]

# --- ADD THIS NEW FUNCTION AT THE BOTTOM ---
def generate_prompt_from_image(image_path, prompt_type="describe", target_style=None):
    """
    Analyzes an image and generates a text prompt.
    If target_style is provided, it guides Gemini to describe the image in that specific style.
    """
    if model is None:
        return "Error: Gemini model is not available."

    if not image_path or not os.path.exists(image_path):
        return "Error: Image file not found."

    try:
        # Optimize: Resize
        img = _prepare_image(image_path)
        
        if prompt_type == "recreate":
            # If a style is selected, we change the instruction significantly
            if target_style and target_style != "none":
                prompt_text = (
                    f"Create a prompt to RECREATE this EXACT image in specified style.\n\n"
                    f"TARGET STYLE: {target_style}\n\n"
                    f"CRITICAL INSTRUCTION: Start the prompt with the style keywords.\n"
                    f"Format: '{target_style} style, [style keywords], [subject], [action], [context]'\n\n"
                    f"Requirements:\n"
                    f"1. **START** with: '{target_style} style, ' followed by 3-4 specific art style keywords (e.g. 'pixel art, 8-bit, blocky' or 'anime, clean lines, cel shaded' or 'cyberpunk, neon, futuristic' or 'oil painting, textured brushstrokes').\n"
                    f"2. Main subject with PRECISE location and ORIGINAL COLORS.\n"
                    f"3. All objects with spatial relationships.\n"
                    f"4. Background and Lighting matching original.\n"
                    f"5. NO explanations. Comma-separated keywords only.\n\n"
                    f"Example Output: {target_style} style, thick impasto strokes, expressive, golden retriever on red truck, sunset lighting, high contrast\n"
                    f"Example Output (Anime): {target_style} style, studio ghibli, vibrant colors, detailed line art, cel shaded, [subject]..."
                )
            else:
                # Default "Recreation" prompt
                prompt_text = (
                    "Create a prompt to RECREATE this EXACT image.\n\n"
                    "CRITICAL: Keep the EXACT same composition, positions, and layout.\n\n"
                    "Include:\n"
                    "1. Main subject with PRECISE location and ORIGINAL COLORS (e.g., 'golden retriever sitting ON THE HOOD of red truck', 'black cat sleeping ON green sofa')\n"
                    "2. Subject pose and facing direction (same as original)\n"
                    "3. ALL other objects with PRECISE spatial relationships and COLORS (e.g., 'yellow sunflowers SURROUNDING truck', 'blue bird perched ON brown branch')\n"
                    "4. Background description (same layout and colors)\n"
                    "5. Lighting and atmosphere (match original)\n\n"
                    "CRITICAL: Be specific about surfaces and MATCH ORIGINAL COLORS.\n"
                    "End with quality keywords: highly detailed, sharp focus, professional quality, cinematic lighting.\n"
                    "Target: ~25-30 keywords total.\n\n"
                    "CRITICAL: Output ONLY the comma-separated keywords. NO explanations, NO breakdowns, NO additional text. Just the keywords."
                )
        else:
            prompt_text = "Describe this image in detail."

        response = model.generate_content([prompt_text, img])
        return response.text
    except Exception as e:
        print(f"[ERROR] Failed to generate prompt from image: {e}")
        return f"Error: {e}"


def generate_image_tags(image_path: str, num_tags: int = 8) -> list:
    """
    Analyzes an image and generates relevant tags for searchability.
    Used as fallback when Groq is not available.
    
    Args:
        image_path: Path to the local image file
        num_tags: Number of tags to generate (default 8)
        
    Returns:
        List of tag strings
    """
    if model is None:
        print("[WARNING] Gemini not available for tag generation")
        return []
    
    if not image_path or not os.path.exists(image_path):
        print(f"[WARNING] Image not found for tagging: {image_path}")
        return []
    
    try:
        # Optimize: Resize
        img = _prepare_image(image_path)
        
        prompt = f"""Analyze this image and provide exactly {num_tags} relevant tags that describe its content.
Rules:
- Each tag should be 1-2 words maximum
- Include: main subject, style, mood, colors, setting
- Tags should be lowercase
- Return ONLY the tags, separated by commas, nothing else

Example output: sunset, mountain, landscape, orange sky, peaceful, nature, scenic, warm colors"""
        
        response = model.generate_content([prompt, img])
        response_text = response.text.strip()
        
        # Parse the comma-separated tags
        tags = [tag.strip().lower() for tag in response_text.split(',') if tag.strip()]
        
        # Clean up tags
        clean_tags = []
        for tag in tags[:num_tags]:
            clean_tag = ''.join(c for c in tag if c.isalnum() or c == ' ').strip()
            if clean_tag and len(clean_tag) <= 30:
                clean_tags.append(clean_tag)
        
        print(f"[INFO] Gemini generated {len(clean_tags)} tags: {clean_tags}")
        return clean_tags
        
    except Exception as e:
        print(f"[ERROR] Failed to generate tags with Gemini: {e}")
        return []