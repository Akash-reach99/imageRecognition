import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

# Initialize engine once
engine = RapidOCR()

def get_text_and_boxes(image_path):
    """
    Scans the image and returns a list of detected items.
    """
    result, elapse = engine(image_path)
    
    if not result:
        return []

    structured_data = []
    
    for item in result:
        # RapidOCR format: [[[x1,y1], [x2,y2]...], 'text', confidence]
        box_points = item[0]
        text_content = item[1]
        raw_confidence = item[2]
        
        # --- FIX: Ensure confidence is a float before rounding ---
        try:
            confidence_val = float(raw_confidence)
        except (ValueError, TypeError):
            confidence_val = 0.0
        
        # Convert points to simple integers for easier JSON handling
        box = [[int(p[0]), int(p[1])] for p in box_points]
        
        structured_data.append({
            "text": text_content,
            "confidence": round(confidence_val, 2),
            "box": box
        })
        
    return structured_data

def draw_boxes_on_image(image_path, output_path, data):
    """
    Draws green boxes on the image and saves it to output_path.
    """
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"[ERROR] Could not read image for drawing: {image_path}")
        return

    for item in data:
        box = item['box']
        # Top-left (p1) and Bottom-right (p3)
        p1 = (box[0][0], box[0][1])
        p3 = (box[2][0], box[2][1])
        
        # Draw Green Box
        cv2.rectangle(img, p1, p3, (0, 255, 0), 2)
        
    cv2.imwrite(output_path, img)