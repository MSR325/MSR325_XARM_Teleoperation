# MSR325_XARM_Teleloperation
---

Before trying any of the teleoperation nodes, check out the ![ROS2 developer packages for robotics products from UFACTORY](https://github.com/xArm-Developer/xarm_ros2.git) and follow all instructions for its usage in this project.

To run the **robot_arm_controller.py** node which enables the user to teleoperate an XARM6 arm manipulator in the Gazebo Classic and RViz 2 environments, launch the **robot_arm_telelop_launch.py** launch file with the following command after running **colcon_build** and sourcing with
**source install/setup.bash**:

```
ros2 launch xarm_vision robot_arm_telelop_launch.py
``` 
