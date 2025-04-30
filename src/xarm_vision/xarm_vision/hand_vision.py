import cv2
import mediapipe as mp
import numpy as np

# Inicialización del detector de manos de MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,  # Detecta hasta 2 manos
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Definir rangos de color en el espacio HSV
# Negro: baja saturación y valor
lower_black = np.array([0, 0, 0])
upper_black = np.array([180, 255, 50])
# Azul: tonos típicos de azul
lower_blue = np.array([100, 150, 0])
upper_blue = np.array([140, 255, 255])
# Rojo: se utiliza dos rangos para cubrir el espectro
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

# Abrir la webcam
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Hacer mirror a la imagen (flip horizontal)
    frame = cv2.flip(frame, 1)
    
    # --- Detección de colores ---
    # Convertir la imagen a HSV para segmentación de color
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Crear máscaras para cada color
    mask_black = cv2.inRange(hsv, lower_black, upper_black)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    # Para rojo combinamos dos rangos
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
    
    # Función para encontrar contornos y dibujar bounding box
    def draw_color_contours(mask, color_name, box_color):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            # Filtrar pequeñas regiones
            if cv2.contourArea(cnt) > 500:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                cv2.putText(frame, color_name, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
    
    # Dibujar contornos para cada color
    draw_color_contours(mask_black, "Negro", (0, 0, 0))
    draw_color_contours(mask_blue, "Azul", (255, 0, 0))
    draw_color_contours(mask_red, "Rojo", (0, 0, 255))
    
    # --- Detección de manos con MediaPipe ---
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)
    
    if result.multi_hand_landmarks and result.multi_handedness:
        for hand_landmarks, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            # Dibujar landmarks y conexiones
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Obtener etiqueta de mano (Left o Right)
            label = handedness.classification[0].label
            
            h, w, _ = frame.shape
            # Seleccionar dos puntos: muñeca (landmark 0) y MCP del dedo medio (landmark 9)
            x0 = int(hand_landmarks.landmark[0].x * w)
            y0 = int(hand_landmarks.landmark[0].y * h)
            x9 = int(hand_landmarks.landmark[9].x * w)
            y9 = int(hand_landmarks.landmark[9].y * h)
            
            cv2.circle(frame, (x0, y0), 5, (255, 0, 0), cv2.FILLED)
            cv2.circle(frame, (x9, y9), 5, (255, 0, 0), cv2.FILLED)
            
            # Calcular el ángulo usando NumPy
            delta = np.array([x9 - x0, y9 - y0])
            # np.arctan2 devuelve el ángulo en radianes; se convierte a grados
            # Multiplicamos por -1 para invertir la orientación (así, los ángulos positivos apuntan "hacia arriba")
            angle = -np.degrees(np.arctan2(delta[1], delta[0]))
            
            cv2.putText(frame, f"Mano: {angle:.2f} deg ({label})", (x0, y0 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    cv2.imshow("Stream Webcam", frame)
    
    # Salir con la tecla ESC
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()