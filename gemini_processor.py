# ImageRecognizer/gemini_processor.py
import os
import google.generativeai as genai
from PIL import Image

try:
    # --- PASTE YOUR VALID API KEY HERE ---
    API_KEY = "AIzaSyCymHx1dgjG8vZN8LdJA7UZOCuQqVu00-g" # REMEMBER TO USE YOUR KEY

    genai.configure(api_key=API_KEY)
    
    # Use a valid model name
    model = genai.GenerativeModel('gemini-flash-latest')
    
    print("[INFO] Gemini model configured successfully!")

except Exception as e:
    print(f"[ERROR] Failed to configure Gemini Pro: {e}")
    model = None

def get_gemini_analysis(image_path, prompt):
    """Analyzes an image using the Gemini model."""
    if model is None:
        return "Error: Gemini model is not available. Check your API key and configuration."

    if not image_path or not os.path.exists(image_path):
        return "Error: Image file not found for analysis."

    try:
        img = Image.open(image_path)
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