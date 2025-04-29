#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Declare configurable parameters
    hw_ns = LaunchConfiguration('hw_ns', default='xarm')
    dof = LaunchConfiguration('dof', default='6')
    robot_type = LaunchConfiguration('robot_type', default='xarm')
    
    return LaunchDescription([
        # Include xArm Gazebo launch
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    FindPackageShare('xarm_moveit_config'),
                    'launch',
                    'xarm6_moveit_gazebo.launch.py'
                ])
            ),
            launch_arguments={
                'hw_ns': hw_ns,
                'dof': dof,
                'robot_type': robot_type,
                'no_gui_control': 'false',
            }.items()
        ),
        
        # Hand tracking node
        Node(
            package='xarm_vision',
            executable='hand_tracker',
            name='hand_tracker',
            parameters=[{
                'publish_rate': 20.0,  # Hz
                'max_hands': 1
            }]
        ),
        
        # Arm controller node
        Node(
            package='xarm_vision',
            executable='arm_controller',
            name='arm_controller',
            parameters=[{
                'workspace_limits.x': [-1.0, 1.0],  # joint1 limits (rad)
                'workspace_limits.y': [-0.5, 0.5],  # joint2 limits
                'workspace_limits.z_angle': [-1.57, 1.57],  # joint6 limits
                'smoothing_factor': 0.2  # Low-pass filter for smoother motions
            }]
        )
    ])