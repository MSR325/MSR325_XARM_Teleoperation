import cv2 # OpenCV for camera capture and image processing
import mediapipe as mp # For pose and hand tracking
import numpy as np # Numerical operations
from collections import deque # For smoothing hand openness values
import rclpy # ROS2 Python client
from rclpy.node import Node # Base class for ROS nodes
from geometry_msgs.msg import PoseArray, Pose # ROS messages for poses
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint # For robot motion
from control_msgs.action import FollowJointTrajectory # ROS action for trajectory control
import rclpy.action # ROS2 action handling

# MediaPipe Initialization
mp_pose = mp.solutions.pose # Pose estimation for shoulders, elbow and wrist
mp_hands = mp.solutions.hands # Hand tracking for gripper control
pose = mp_pose.Pose(
    static_image_mode=False, # Real-time tracking mode
    model_complexity=2, # Higher accuracy
    enable_segmentation=False,
    min_detection_confidence=0.7) # Only detect if confidence is high
hands = mp_hands.Hands(
    static_image_mode=False, # Real-time tracking mode
    max_num_hands=1, # Only track one hand
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7) # Smooth tracking
mp_draw = mp.solutions.drawing_utils # For visualizing landmarks
# A landmark is a point of correspondence on each object that matches between and within populations

# ROS2 Arm Controller Node
class ArmController(Node):
    def __init__(self):
        super().__init__('robot_arm_controller')
        self.publisher = self.create_publisher(PoseArray, '/arm_control_poses', 10)
        
        # Action client that sends goal to action server control the robot arm
        # It receives the stream of feedback and the result from the action server
        self.client = rclpy.action.ActionClient(
            self, # Action client added to self
            FollowJointTrajectory, # FollowJointTrajectory action type to control trajectory
            '/xarm6_traj_controller/follow_joint_trajectory' # Action name
            )
        
        # 6-DOF robot joint names
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        self.openness_history = deque(maxlen=5) # Smoothes hand openness values
        self.get_logger().info("Arm controller ready")

    # Measure how open the hand is (for gripper control)
    def calculate_hand_openness(self, hand_landmarks, frame_shape):
        """Calculate normalized hand openness (0=closed, 1=open)"""
        h, w, _ = frame_shape # Height and width of frame
        # Finds the center of the palm by averaging key landmarks
        palm_points = [0, 1, 5, 9, 13, 17] # Key palm landmarks
        palm_x = sum(hand_landmarks.landmark[i].x for i in palm_points) / len(palm_points)
        palm_y = sum(hand_landmarks.landmark[i].y for i in palm_points) / len(palm_points)
        
        # Measure distance from palm to fingertips
        fingertip_ids = [4, 8, 12, 16, 20] # Tips of thumb, index, middle, ring, pinky
        # Calculates Euclidean distance from palm center to fingertips
        distances = []
        for fid in fingertip_ids:
            fx = hand_landmarks.landmark[fid].x
            fy = hand_landmarks.landmark[fid].y
            distances.append(np.sqrt((fx - palm_x)**2 + (fy - palm_y)**2))
        
        avg_dist = np.mean(distances) # Calculates average distance
        openness = np.clip((avg_dist - 0.05) / 0.15, 0, 1) # Normalizes to [0,1]
        self.openness_history.append(openness) # Appends to deque for smooth values
        return np.mean(self.openness_history) # Returns average of normalized average distances history

    def send_arm_command(self, shoulder_angle, elbow_angle, wrist_angle, hand_openness):
        """Convert human joint angles to robot joint commands"""
        # Map human angles to robot joints and scales human angles to safe robot ranges
        target_joints = [
            shoulder_angle * 0.5,    # joint1 (reduced range for safety)
            elbow_angle * 0.7,       # joint2 
            -elbow_angle * 0.3,      # joint3 (coupled motion)
            wrist_angle,             # joint4
            0.0,                     # joint5 (fixed)
            (hand_openness - 0.5) * 2.0  # joint6 (gripper) maps [0,1] openness -> [-1, 1]
        ]
        
        # Create action goal
        goal_msg = FollowJointTrajectory.Goal()
        # Define trajectory parameter of goal
        trajectory = goal_msg.trajectory
        # Assign joint names to joint names parameter of trajectory
        trajectory.joint_names = self.joint_names
        
        # Defines 1-second motion plan for the arm
        point = JointTrajectoryPoint() # Defines trajectory point message
        point.positions = target_joints # Target joints passed as positions of the trajectory point
        point.time_from_start.sec = 1 # Reach target in 1 second
        trajectory.points.append(point) # Append the newly defined trajectory point to the points parameter of the trajectory parameter of the goal
        
        self.client.wait_for_server() # Waits for section server to be available 
        self.client.send_goal_async(goal_msg) # Goal of target positions sent to action server

def main():
    rclpy.init() # Initialize ROS2
    arm_controller = ArmController() # Create node
    cap = cv2.VideoCapture(0) # Open webcam

    try:
        while rclpy.ok():
            ret, frame = cap.read() # Capture frame
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1) # Mirror effect
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # RGB color codification
            
            # Process pose and hands by running MediaPipe detection
            pose_results = pose.process(frame_rgb) # Body landmarks results
            hand_results = hands.process(frame_rgb) # Hand landmarks results
            
            # If detection of arm segments and hand is successful
            if pose_results.pose_landmarks and hand_results.multi_hand_landmarks:
                # Get body landmarks
                landmarks = pose_results.pose_landmarks.landmark
                
                # Calculate shoulder angle (joint1) by measuring angle between shoulder and hip (vertical movement)
                shoulder = np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, 
                                    landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y])
                hip = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP].x,
                                landmarks[mp_pose.PoseLandmark.LEFT_HIP].y])
                shoulder_angle = np.degrees(np.arctan2(shoulder[1]-hip[1], shoulder[0]-hip[0]))
                
                # Calculate elbow angle (joint2) by computing angle between elbow and shoulder
                elbow = np.array([landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x,
                                  landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y])
                elbow_angle = np.degrees(np.arctan2(elbow[1]-shoulder[1], elbow[0]-shoulder[0]))
                
                # Calculate wrist angle (joint4) by computing angle between wrist and elbow
                wrist = np.array([landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x,
                                  landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y])
                wrist_angle = np.degrees(np.arctan2(wrist[1]-elbow[1], wrist[0]-elbow[0]))
                
                # Calculate hand openness (joint6) by measuring hand openness of only one hand
                hand_openness = arm_controller.calculate_hand_openness(
                    hand_results.multi_hand_landmarks[0], frame.shape)
                
                # Send commands to arm converting the detected angles to radians and the normalized hand openness
                arm_controller.send_arm_command(
                    np.radians(shoulder_angle),
                    np.radians(elbow_angle),
                    np.radians(wrist_angle),
                    hand_openness)
                
                # Visualization of landmarks and angles on the frame
                mp_draw.draw_landmarks(
                    frame, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                mp_draw.draw_landmarks(
                    frame, hand_results.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
                
                # Display angles
                cv2.putText(frame, f"Shoulder: {shoulder_angle:.1f} deg", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(frame, f"Elbow: {elbow_angle:.1f} deg", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Wrist: {wrist_angle:.1f} deg", (10, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"Hand Openness: {hand_openness:.2f}", (10, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow("Arm Control", frame)
            if cv2.waitKey(1) == 27:  # ESC to exit
                break
            
            # Process ROS callbacks
            rclpy.spin_once(arm_controller, timeout_sec=0.001)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        arm_controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()