#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, Pose
import cv2
import mediapipe as mp
import numpy as np

class HandTracker(Node):
    def __init__(self):
        super().__init__('hand_tracker')
        self.publisher = self.create_publisher(PoseArray, '/hand_poses', 10)
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Track only one hand for control
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # Webcam setup
        self.cap = cv2.VideoCapture(0)
        self.timer = self.create_timer(0.05, self.track_hand)  # 20Hz

    def track_hand(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(frame_rgb)
        
        pose_array = PoseArray()
        pose_array.header.stamp = self.get_clock().now().to_msg()
        pose_array.header.frame_id = "camera_frame"

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                # Get wrist (joint 0) and middle finger MCP (joint 9)
                wrist = hand_landmarks.landmark[0]
                finger = hand_landmarks.landmark[9]
                
                # Create normalized pose (0-1 range)
                pose = Pose()
                pose.position.x = wrist.x  # X coordinate
                pose.position.y = wrist.y  # Y coordinate
                
                # Calculate orientation angle
                delta = np.array([finger.x - wrist.x, finger.y - wrist.y])
                angle = -np.arctan2(delta[1], delta[0])
                pose.orientation.z = np.sin(angle/2)
                pose.orientation.w = np.cos(angle/2)
                
                pose_array.poses.append(pose)
                
                # Visualization (optional)
                h, w = frame.shape[:2]
                cv2.circle(frame, (int(wrist.x*w), int(wrist.y*h)), 10, (0,255,0), -1)
        
        self.publisher.publish(pose_array)
        cv2.imshow("Hand Tracking", frame)
        cv2.waitKey(1)

def main():
    rclpy.init()
    node = HandTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()