# project p8/image_editor_processor.py
import cv2
import numpy as np
from PIL import Image, ImageEnhance
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

def apply_filter(original_path: str, filter_type: str) -> Image.Image:
    """
    Applies color filters to the entire image.
    """
    img = cv2.imread(original_path)
    if img is None:
        raise Exception(f"Failed to read image: {original_path}")
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    if filter_type == 'bw':
        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        return Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB))
    
    elif filter_type == 'sepia':
        # Standard Sepia Matrix
        img_float = np.array(img, dtype=np.float64)
        img_sepia = np.zeros_like(img_float)
        # R = (R * .393) + (G * .769) + (B * .189)
        # G = (R * .349) + (G * .686) + (B * .168)
        # B = (R * .272) + (G * .534) + (B * .131)
        matrix = [[0.393, 0.769, 0.189],
                  [0.349, 0.686, 0.168],
                  [0.272, 0.534, 0.131]]
        
        # Apply matrix (simplified vector processing)
        img_sepia = cv2.transform(img_float, np.array(matrix))
        
        # Clip values to 255
        img_sepia = np.clip(img_sepia, 0, 255)
        return Image.fromarray(np.array(img_sepia, dtype=np.uint8))
    
    elif filter_type == 'vintage':
        # Fade + Yellow tint + Noise
        # 1. Reduce contrast (Fade)
        img_float = img.astype(float)
        img_float = img_float * 0.8 + 20 # Lift blacks
        
        # 2. Add Warmth (Yellow-ish)
        # B channel down, R channel up
        img_float[:,:,2] -= 20 # Blue down makes it yellow
        img_float[:,:,0] += 20 # Red up
        
        # 3. Vignette (Darker corners)
        rows, cols = img.shape[:2]
        # Create Gaussian kernel
        X_kernel = cv2.getGaussianKernel(cols, cols/2)
        Y_kernel = cv2.getGaussianKernel(rows, rows/2)
        kernel = Y_kernel * X_kernel.T
        mask = kernel / kernel.max()
        
        # Apply vignette
        img_vignette = img_float * mask[:, :, np.newaxis]
        
        np.clip(img_vignette, 0, 255, out=img_vignette)
        return Image.fromarray(img_vignette.astype(np.uint8))
        
    elif filter_type == 'cool':
        # Increase Blue, Decrease Red
        img_float = img.astype(float)
        img_float[:,:,0] -= 10 # Red down
        img_float[:,:,2] += 20 # Blue up
        np.clip(img_float, 0, 255, out=img_float)
        return Image.fromarray(img_float.astype(np.uint8))
        
    elif filter_type == 'warm':
        # Increase Red, Decrease Blue
        img_float = img.astype(float)
        img_float[:,:,0] += 20 # Red up
        img_float[:,:,2] -= 20 # Blue down
        np.clip(img_float, 0, 255, out=img_float)
        return Image.fromarray(img_float.astype(np.uint8))
        
    elif filter_type == 'enhance':
        # PIL ImageEnhance for better general enhancement
        # Convert numpy->PIL
        pil_img = Image.fromarray(img)
        
        # 1. Enhance Contrast
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        # 2. Enhance Color (Saturation)
        enhancer = ImageEnhance.Color(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        # 3. Enhance Sharpness
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(1.3)
        
        return pil_img
    
    else:
        # Default return original
        return Image.fromarray(img)