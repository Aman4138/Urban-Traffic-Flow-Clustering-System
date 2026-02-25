import cv2
import numpy as np

def estimate_vehicle_density(frame):
    """
    Estimate traffic density using edge detection
    Returns: (density_score, vehicle_count)
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Blur
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        dilated = cv2.dilate(closed, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours
        min_area = 400
        max_area = 60000
        
        valid_vehicles = 0
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                valid_vehicles += 1
                total_area += area
        
        # Calculate density
        frame_area = frame.shape[0] * frame.shape[1]
        area_density = min(1.0, total_area / (frame_area * 0.25))
        count_density = min(1.0, valid_vehicles / 15.0)
        
        # Weighted average
        final_density = (area_density * 0.65) + (count_density * 0.35)
        
        return round(final_density, 3), valid_vehicles
        
    except Exception as e:
        print(f"Vision error: {e}")
        return 0.0, 0
