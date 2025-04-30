import cv2
import mediapipe as mp
import numpy as np
from collections import deque

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# Color detection ranges (unchanged from your original)
lower_black = np.array([0, 0, 0])
upper_black = np.array([180, 255, 50])
lower_blue = np.array([100, 150, 0])
upper_blue = np.array([140, 255, 255])
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

# Openness smoothing
openness_history = deque(maxlen=5)

def calculate_hand_openness(hand_landmarks, frame_shape):
    """Calculate normalized hand openness (0=closed, 1=open)"""
    h, w, _ = frame_shape
    
    # Palm center (average of wrist and MCP joints)
    palm_points = [0, 1, 5, 9, 13, 17]  # Wrist + finger bases
    palm_x = sum(hand_landmarks.landmark[i].x for i in palm_points) / len(palm_points)
    palm_y = sum(hand_landmarks.landmark[i].y for i in palm_points) / len(palm_points)
    
    # Fingertip distances to palm
    fingertip_ids = [4, 8, 12, 16, 20]  # Thumb to pinky
    distances = []
    for fid in fingertip_ids:
        fx = hand_landmarks.landmark[fid].x
        fy = hand_landmarks.landmark[fid].y
        distances.append(np.sqrt((fx - palm_x)**2 + (fy - palm_y)**2))
    
    avg_dist = np.mean(distances)
    openness = np.clip((avg_dist - 0.05) / 0.15, 0, 1)  # Adjust these values based on your hand size
    
    return openness, (int(palm_x * w), int(palm_y * h))

def count_extended_fingers(hand_landmarks):
    """Count how many fingers are extended (0-5)"""
    finger_states = []
    
    # Thumb (compare x-coordinate of tip vs MCP)
    thumb_tip = hand_landmarks.landmark[4]
    thumb_mcp = hand_landmarks.landmark[2]
    finger_states.append(thumb_tip.x < thumb_mcp.x)  # True if extended
    
    # Other fingers (compare y-coordinate of tip vs PIP)
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        tip_point = hand_landmarks.landmark[tip]
        pip_point = hand_landmarks.landmark[pip]
        finger_states.append(tip_point.y < pip_point.y)  # True if extended
    
    return sum(finger_states)

def draw_color_contours(frame, mask, color_name, box_color):
    """Draw bounding boxes for color detection"""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > 500:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
            cv2.putText(frame, color_name, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

# Main loop
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        continue
    
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    # Color detection (unchanged from your original)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_black = cv2.inRange(hsv, lower_black, upper_black)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
    
    draw_color_contours(frame, mask_black, "Negro", (0, 0, 0))
    draw_color_contours(frame, mask_blue, "Azul", (255, 0, 0))
    draw_color_contours(frame, mask_red, "Rojo", (0, 0, 255))
    
    # Hand detection
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)
    
    if result.multi_hand_landmarks and result.multi_handedness:
        for hand_landmarks, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            # Get basic info
            label = handedness.classification[0].label
            x0 = int(hand_landmarks.landmark[0].x * w)
            y0 = int(hand_landmarks.landmark[0].y * h)
            
            # Calculate hand angle
            x9 = int(hand_landmarks.landmark[9].x * w)
            y9 = int(hand_landmarks.landmark[9].y * h)
            delta = np.array([x9 - x0, y9 - y0])
            angle = -np.degrees(np.arctan2(delta[1], delta[0]))
            
            # Calculate hand openness
            openness, palm_center = calculate_hand_openness(hand_landmarks, frame.shape)
            openness_history.append(openness)
            smoothed_openness = np.mean(openness_history)
            
            # Count extended fingers
            extended_fingers = count_extended_fingers(hand_landmarks)
            
            # Visualizations
            cv2.circle(frame, palm_center, 10, (0, 255, 0), -1)  # Palm center
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Display info
            y_offset = 20
            cv2.putText(frame, f"{label} Hand", (x0, y0 - y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            y_offset += 20
            cv2.putText(frame, f"Angle: {angle:.1f} deg", (x0, y0 - y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            y_offset += 20
            cv2.putText(frame, f"Openness: {smoothed_openness:.2f}", (x0, y0 - y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            y_offset += 20
            cv2.putText(frame, f"Fingers: {extended_fingers}", (x0, y0 - y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            # Color code based on openness
            if smoothed_openness > 0.7:
                color = (0, 255, 0)  # Green = open
            elif smoothed_openness < 0.3:
                color = (0, 0, 255)  # Red = closed
            else:
                color = (255, 0, 0)  # Blue = mid
            
            cv2.circle(frame, (x0, y0), 8, color, -1)
            cv2.circle(frame, (x9, y9), 8, color, -1)
    
    cv2.imshow("Hand Tracking", frame)
    if cv2.waitKey(1) == 27:  # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()