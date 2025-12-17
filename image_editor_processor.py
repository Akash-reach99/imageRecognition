# project p8/image_editor_processor.py
import cv2
import numpy as np
from PIL import Image
from rembg import remove  # Requires: pip install rembg

def _get_mask_and_image(original_path, mask_path=None):
    """
    Helper function to load the image and generate a high-quality mask 
    using rembg (ignoring the passed YOLO mask_path).
    """
    # 1. Load Original Image
    original_image = cv2.imread(original_path)
    if original_image is None:
        raise Exception(f"Failed to read original image: {original_path}")
    
    # 2. Convert to PIL for rembg processing
    original_pil = Image.fromarray(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
    
    # 3. Use REMBG to get the image with transparent background
    # This automatically handles fur, hair, and fine details.
    try:
        result_pil = remove(original_pil)
    except Exception as e:
        print(f"Error in rembg: {e}")
        # Fallback if rembg fails (return original and full white mask)
        h, w = original_image.shape[:2]
        return original_image, np.ones((h, w), dtype=np.uint8) * 255
    
    # 4. Extract the Alpha Channel (Transparency) to serve as our new Mask
    result_np = np.array(result_pil)
    
    # Ensure it has 4 channels (RGBA)
    if result_np.shape[2] == 4:
        alpha_channel = result_np[:, :, 3] # Get the 4th channel
    else:
        # Fallback if result isn't RGBA
        alpha_channel = np.ones(result_np.shape[:2], dtype=np.uint8) * 255

    # Return the original CV2 image and the new high-quality Alpha Mask
    return original_image, alpha_channel

def apply_remove_background(original_path: str, mask_path: str = None) -> Image.Image:
    """
    Uses rembg directly to remove background.
    """
    original_image_bgr = cv2.imread(original_path)
    if original_image_bgr is None:
        raise Exception(f"Failed to read image: {original_path}")

    original_pil = Image.fromarray(cv2.cvtColor(original_image_bgr, cv2.COLOR_BGR2RGB))
    
    # rembg does the heavy lifting here
    return remove(original_pil)

def apply_blur_background(original_path: str, mask_path: str = None, intensity: int = 50) -> Image.Image:
    """
    Applies a blur using the high-quality rembg mask.
    """
    # Get image and the SUPERIOR rembg mask
    original_image, high_quality_mask = _get_mask_and_image(original_path)
    
    # Invert mask (Background is 255 where mask is 0)
    inverted_mask = cv2.bitwise_not(high_quality_mask)
    
    # Calculate Blur Strength
    intensity = max(1, min(100, int(intensity)))
    k_size = int(intensity) * 2 + 1
    if k_size % 2 == 0: k_size += 1 # Ensure odd
    
    blurred_image = cv2.GaussianBlur(original_image, (k_size, k_size), 0)
    
    # Convert masks to 3 channels (float 0.0-1.0) for soft blending
    # This preserves the semi-transparent edges of fur/hair!
    mask_3ch = cv2.cvtColor(high_quality_mask, cv2.COLOR_GRAY2BGR) / 255.0
    inv_mask_3ch = cv2.cvtColor(inverted_mask, cv2.COLOR_GRAY2BGR) / 255.0
    
    # Convert images to float for blending
    original_float = original_image.astype(float)
    blurred_float = blurred_image.astype(float)
    
    # Blend: (Original * Mask) + (Blurred * InvMask)
    combined = (original_float * mask_3ch) + (blurred_float * inv_mask_3ch)
    
    return Image.fromarray(cv2.cvtColor(combined.astype(np.uint8), cv2.COLOR_BGR2RGB))

def apply_spotlight_effect(original_path: str, mask_path: str = None, intensity: int = 50) -> Image.Image:
    """
    Spotlight effect using high-quality rembg mask.
    """
    original_image, high_quality_mask = _get_mask_and_image(original_path)
    inverted_mask = cv2.bitwise_not(high_quality_mask)
    
    # Create Grayscale Background
    grayscale = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    grayscale_bgr = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2BGR)

    # Darken Background based on intensity
    factor = 1.0 - (max(0, min(100, int(intensity))) / 100.0)
    grayscale_bgr = (grayscale_bgr * factor).astype(float)
    
    # Prepare Soft Masks
    mask_3ch = cv2.cvtColor(high_quality_mask, cv2.COLOR_GRAY2BGR) / 255.0
    inv_mask_3ch = cv2.cvtColor(inverted_mask, cv2.COLOR_GRAY2BGR) / 255.0
    
    original_float = original_image.astype(float)
    
    # Blend
    combined = (original_float * mask_3ch) + (grayscale_bgr * inv_mask_3ch)
    
    return Image.fromarray(cv2.cvtColor(combined.astype(np.uint8), cv2.COLOR_BGR2RGB))

def apply_smart_crop(original_path: str, mask_path: str = None) -> Image.Image:
    """
    Crops to the content found by rembg.
    """
    # Use the high quality remove_bg function first
    transparent_pil = apply_remove_background(original_path)
    
    # Convert to numpy to find bounds
    transparent_np = np.array(transparent_pil)
    # Check if image has alpha
    if transparent_np.shape[2] == 4:
        alpha = transparent_np[:, :, 3]
    else:
        # Should not happen with rembg, but safe fallback
        return transparent_pil
    
    y_coords, x_coords = np.where(alpha > 0)
    
    if len(y_coords) == 0:
        return transparent_pil
        
    x_min, x_max = np.min(x_coords), np.max(x_coords)
    y_min, y_max = np.min(y_coords), np.max(y_coords)
    
    padding = 10
    x_min = max(0, x_min - padding)
    y_min = max(0, y_min - padding)
    x_max = min(transparent_pil.width, x_max + padding)
    y_max = min(transparent_pil.height, y_max + padding)

    return transparent_pil.crop((x_min, y_min, x_max, y_max))