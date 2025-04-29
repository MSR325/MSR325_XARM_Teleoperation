#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
import rclpy.action
import numpy as np

class ArmController(Node):
    def __init__(self):
        super().__init__('arm_controller')
        self.subscription = self.create_subscription(
            PoseArray,
            '/hand_poses',
            self.hand_pose_callback,
            10)
        
        self.joint_names = ['joint1', 'joint2', 'joint3', 
                          'joint4', 'joint5', 'joint6']
        
        # Action client for trajectory execution
        self.client = rclpy.action.ActionClient(
            self,
            FollowJointTrajectory,
            '/xarm6_traj_controller/follow_joint_trajectory')
        
        # Workspace limits (normalized hand coords to joint angles)
        self.workspace_limits = {
            'x': (-0.5, 0.5),    # Joint1 range (rad)
            'y': (-0.5, 0.5),    # Joint2 range
            'z_angle': (-1.57, 1.57)  # Wrist orientation
        }
        
        self.get_logger().info("Arm controller ready")

    def hand_pose_callback(self, msg):
        if not msg.poses:
            return
            
        hand_pose = msg.poses[0]  # Use first detected hand
        
        # Convert normalized coordinates to joint angles
        target_joints = [
            self.remap(hand_pose.position.x, 0, 1, *self.workspace_limits['x']),  # Joint1
            self.remap(hand_pose.position.y, 0, 1, *self.workspace_limits['y']),  # Joint2
            0.0,  # Joint3 (fixed for simplicity)
            0.0,  # Joint4
            0.0,  # Joint5
            self.get_yaw_from_quaternion(hand_pose.orientation)  # Joint6 (wrist)
        ]
        
        self.execute_trajectory(target_joints)

    def remap(self, value, in_min, in_max, out_min, out_max):
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def get_yaw_from_quaternion(self, q):
        # Simplified - assumes quaternion represents only yaw rotation
        return np.arctan2(2*(q.w*q.z), 1-2*(q.z*q.z))

    def execute_trajectory(self, target_joints, duration=1.0):
        goal_msg = FollowJointTrajectory.Goal()
        trajectory = goal_msg.trajectory
        trajectory.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = target_joints
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        trajectory.points.append(point)
        
        self.client.wait_for_server()
        future = self.client.send_goal_async(goal_msg)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected')
            return
        
        self.get_logger().info('Goal accepted')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f'Trajectory completed: {result.error_code}')

def main():
    rclpy.init()
    node = ArmController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()