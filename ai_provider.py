# ImageRecognizer/ai_provider.py
"""
Unified AI Provider Interface

This module provides a single interface for AI operations that can switch
between different providers (Gemini, Groq) based on configuration.

Configuration via .env:
    AI_PROVIDER=gemini  # Use Gemini only
    AI_PROVIDER=groq    # Use Groq only  
    AI_PROVIDER=auto    # Try Gemini first, fallback to Groq
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Get provider configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini').lower().strip()

print(f"[INFO] AI Provider configured: {AI_PROVIDER}")

# Import both processors
try:
    from gemini_processor import (
        get_gemini_analysis,
        get_gemini_text_prompt,
        generate_prompt_from_image as gemini_generate_prompt
    )
    GEMINI_AVAILABLE = True
    print("[INFO] Gemini processor loaded successfully")
except Exception as e:
    print(f"[WARNING] Gemini processor not available: {e}")
    GEMINI_AVAILABLE = False
    get_gemini_analysis = None
    get_gemini_text_prompt = None
    gemini_generate_prompt = None

try:
    from groq_processor import (
        get_groq_analysis,
        get_groq_text_prompt,
        generate_prompt_from_image_groq,
        is_available as groq_is_available
    )
    GROQ_AVAILABLE = groq_is_available()
    if GROQ_AVAILABLE:
        print("[INFO] Groq processor loaded successfully")
    else:
        print("[WARNING] Groq processor loaded but API key not configured")
except Exception as e:
    print(f"[WARNING] Groq processor not available: {e}")
    GROQ_AVAILABLE = False
    get_groq_analysis = None
    get_groq_text_prompt = None
    generate_prompt_from_image_groq = None


def _is_error_response(result: str) -> bool:
    """Check if a response is an error message."""
    if not result:
        return True
    error_prefixes = ("Error:", "An error occurred", "error:", "API Error")
    return result.startswith(error_prefixes)


def _try_gemini_analysis(image_path: str, prompt: str) -> tuple[str, bool]:
    """Try Gemini analysis, return (result, success)."""
    if not GEMINI_AVAILABLE:
        return "Gemini not available", False
    try:
        result = get_gemini_analysis(image_path, prompt)
        if result and not _is_error_response(result):
            return result, True
        return result, False
    except Exception as e:
        return f"Gemini error: {e}", False


def _try_groq_analysis(image_path: str, prompt: str) -> tuple[str, bool]:
    """Try Groq analysis, return (result, success)."""
    if not GROQ_AVAILABLE:
        return "Groq not available", False
    try:
        result = get_groq_analysis(image_path, prompt)
        if result and not _is_error_response(result):
            return result, True
        return result, False
    except Exception as e:
        return f"Groq error: {e}", False


def _try_gemini_text(prompt: str) -> tuple[str, bool]:
    """Try Gemini text prompt, return (result, success)."""
    if not GEMINI_AVAILABLE:
        return "Gemini not available", False
    try:
        result = get_gemini_text_prompt(prompt)
        if result and not _is_error_response(result):
            return result, True
        return result, False
    except Exception as e:
        return f"Gemini error: {e}", False


def _try_groq_text(prompt: str) -> tuple[str, bool]:
    """Try Groq text prompt, return (result, success)."""
    if not GROQ_AVAILABLE:
        return "Groq not available", False
    try:
        result = get_groq_text_prompt(prompt)
        if result and not _is_error_response(result):
            return result, True
        return result, False
    except Exception as e:
        return f"Groq error: {e}", False


# ============================================================================
# PUBLIC API - These are the functions that app.py should use
# ============================================================================

def get_ai_analysis(image_path: str, prompt: str) -> str:
    """
    Analyzes an image using the configured AI provider.
    
    Args:
        image_path: Path to the local image file
        prompt: The analysis prompt/question
        
    Returns:
        Text response from the AI model
    """
    if AI_PROVIDER == 'gemini':
        result, success = _try_gemini_analysis(image_path, prompt)
        return result
    
    elif AI_PROVIDER == 'groq':
        result, success = _try_groq_analysis(image_path, prompt)
        return result
    
    elif AI_PROVIDER == 'auto':
        # Try Gemini first, fallback to Groq
        result, success = _try_gemini_analysis(image_path, prompt)
        if success:
            return result
        
        print(f"[INFO] Gemini failed, falling back to Groq...")
        result, success = _try_groq_analysis(image_path, prompt)
        return result
    
    else:
        return f"Error: Unknown AI provider '{AI_PROVIDER}'. Use 'gemini', 'groq', or 'auto'."


def get_ai_text_prompt(prompt: str) -> str:
    """
    Gets a text-only response from the configured AI provider.
    
    Args:
        prompt: The text prompt
        
    Returns:
        Text response from the AI model
    """
    if AI_PROVIDER == 'gemini':
        result, success = _try_gemini_text(prompt)
        return result
    
    elif AI_PROVIDER == 'groq':
        result, success = _try_groq_text(prompt)
        return result
    
    elif AI_PROVIDER == 'auto':
        # Try Gemini first, fallback to Groq
        result, success = _try_gemini_text(prompt)
        if success:
            return result
        
        print(f"[INFO] Gemini failed, falling back to Groq...")
        result, success = _try_groq_text(prompt)
        return result
    
    else:
        return f"Error: Unknown AI provider '{AI_PROVIDER}'. Use 'gemini', 'groq', or 'auto'."


def generate_prompt_from_image(image_path: str, prompt_type: str = "describe", target_style: str = None) -> str:
    """
    Analyzes an image and generates a text prompt for image generation.
    
    Args:
        image_path: Path to the local image file
        prompt_type: Type of prompt to generate ("describe" or "recreate")
        target_style: Optional style modifier for recreation
        
    Returns:
        Generated prompt string
    """
    if AI_PROVIDER == 'gemini':
        if GEMINI_AVAILABLE:
            return gemini_generate_prompt(image_path, prompt_type, target_style)
        return "Error: Gemini not available"
    
    elif AI_PROVIDER == 'groq':
        if GROQ_AVAILABLE:
            return generate_prompt_from_image_groq(image_path, prompt_type, target_style)
        return "Error: Groq not available"
    
    elif AI_PROVIDER == 'auto':
        # Try Gemini first
        if GEMINI_AVAILABLE:
            try:
                result = gemini_generate_prompt(image_path, prompt_type, target_style)
                if result and not result.startswith("Error:"):
                    return result
            except Exception as e:
                print(f"[INFO] Gemini prompt generation failed: {e}")
        
        # Fallback to Groq
        if GROQ_AVAILABLE:
            print(f"[INFO] Falling back to Groq for prompt generation...")
            return generate_prompt_from_image_groq(image_path, prompt_type, target_style)
        
        return "Error: No AI provider available"
    
    else:
        return f"Error: Unknown AI provider '{AI_PROVIDER}'"


def get_current_provider() -> str:
    """Returns the currently configured AI provider."""
    return AI_PROVIDER


def get_available_providers() -> dict:
    """Returns availability status of all providers."""
    return {
        'gemini': GEMINI_AVAILABLE,
        'groq': GROQ_AVAILABLE,
        'configured': AI_PROVIDER
    }
