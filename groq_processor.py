# ImageRecognizer/groq_processor.py
"""
Groq API processor for image analysis and text generation.
Uses Llama 4 Scout vision model for multimodal tasks.
"""
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
groq_client = None
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

try:
    from groq import Groq
    
    API_KEY = os.getenv('GROQ_API_KEY')
    
    if not API_KEY:
        print("[WARNING] No Groq API key found in environment variables")
    else:
        groq_client = Groq(api_key=API_KEY)
        print("[INFO] Groq client configured successfully!")
        
except ImportError:
    print("[WARNING] Groq package not installed. Run: pip install groq")
except Exception as e:
    print(f"[ERROR] Failed to configure Groq: {e}")


def _encode_image_to_base64(image_path: str) -> str:
    """Encodes a local image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _get_image_mime_type(image_path: str) -> str:
    """Returns the MIME type based on file extension."""
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')


def _prepare_image(image_path: str, max_dim: int = 1536, quality: int = 85) -> bytes:
    """
    Preprocesses image for optimal API performance.
    - Resizes to max_dim if larger
    - Compresses with JPEG quality
    - Returns bytes for base64 encoding
    
    This does NOT affect metadata extraction, which happens on the original file.
    """
    from PIL import Image
    from io import BytesIO
    
    img = Image.open(image_path)
    original_size = img.size
    
    # Convert to RGB (strips alpha, ensures JPEG compatibility)
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
        print(f"[DEBUG] Groq: Resized image from {original_size[0]}x{original_size[1]} to {new_width}x{new_height}")
    
    # Compress to JPEG bytes
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    return buffer.getvalue()


def get_groq_analysis(image_path: str, prompt: str) -> str:
    """
    Analyzes an image using the Groq Llama 4 Scout vision model.
    
    Args:
        image_path: Path to the local image file
        prompt: The analysis prompt/question
        
    Returns:
        Text response from the model
    """
    if groq_client is None:
        return "Error: Groq client is not available. Check your API key and configuration."
    
    if not image_path or not os.path.exists(image_path):
        return "Error: Image file not found for analysis."
    
    try:
        # Preprocess and encode image for optimal performance
        image_bytes = _prepare_image(image_path)
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = 'image/jpeg'  # Always JPEG after preprocessing
        
        # Create chat completion with vision
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"[ERROR] Failed to process image with Groq: {e}")
        return f"An error occurred while processing the image: {e}"


def get_groq_text_prompt(prompt: str) -> str:
    """
    Gets a text-only response from the Groq model.
    
    Args:
        prompt: The text prompt
        
    Returns:
        Text response from the model
    """
    if groq_client is None:
        return "Error: Groq client is not available. Check your API key and configuration."
    
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"[ERROR] Failed to process text prompt with Groq: {e}")
        return f"An error occurred while processing the prompt: {e}"


def generate_prompt_from_image_groq(image_path: str, prompt_type: str = "describe", target_style: str = None) -> str:
    """
    Analyzes an image and generates a text prompt for image generation.
    
    Args:
        image_path: Path to the local image file
        prompt_type: Type of prompt to generate ("describe" or "recreate")
        target_style: Optional style modifier for recreation
        
    Returns:
        Generated prompt string
    """
    if groq_client is None:
        return "Error: Groq client is not available."
    
    if not image_path or not os.path.exists(image_path):
        return "Error: Image file not found."
    
    try:
        # Preprocess and encode image for optimal performance
        image_bytes = _prepare_image(image_path)
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = 'image/jpeg'  # Always JPEG after preprocessing
        
        # Build the prompt based on type
        if prompt_type == "recreate":
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
        
        # Create completion
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"[ERROR] Failed to generate prompt from image with Groq: {e}")
        return f"Error: {e}"


def is_available() -> bool:
    """Check if Groq client is properly configured and available."""
    return groq_client is not None


def generate_image_tags(image_path: str, num_tags: int = 8) -> list:
    """
    Analyzes an image and generates relevant tags for searchability.
    
    Args:
        image_path: Path to the local image file
        num_tags: Number of tags to generate (default 8)
        
    Returns:
        List of tag strings
    """
    if groq_client is None:
        print("[WARNING] Groq not available for tag generation")
        return []
    
    if not image_path or not os.path.exists(image_path):
        print(f"[WARNING] Image not found for tagging: {image_path}")
        return []
    
    try:
        # Preprocess and encode image for optimal performance
        image_bytes = _prepare_image(image_path)
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = 'image/jpeg'  # Always JPEG after preprocessing
        
        prompt = f"""Analyze this image and provide exactly {num_tags} relevant tags that describe its content.
Rules:
- Each tag should be 1-2 words maximum
- Include: main subject, style, mood, colors, setting
- Tags should be lowercase
- Return ONLY the tags, separated by commas, nothing else

Example output: sunset, mountain, landscape, orange sky, peaceful, nature, scenic, warm colors"""
        
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_completion_tokens=256,
            top_p=1,
            stream=False,
        )
        
        response = completion.choices[0].message.content.strip()
        
        # Parse the comma-separated tags
        tags = [tag.strip().lower() for tag in response.split(',') if tag.strip()]
        
        # Clean up tags - remove any that are too long or contain special characters
        clean_tags = []
        for tag in tags[:num_tags]:
            # Keep only alphanumeric and spaces
            clean_tag = ''.join(c for c in tag if c.isalnum() or c == ' ').strip()
            if clean_tag and len(clean_tag) <= 30:
                clean_tags.append(clean_tag)
        
        print(f"[INFO] Generated {len(clean_tags)} tags for image: {clean_tags}")
        return clean_tags
        
    except Exception as e:
        print(f"[ERROR] Failed to generate tags with Groq: {e}")
        return []
