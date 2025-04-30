from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'xarm_vision'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.[yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chrisrvt',
    maintainer_email='christianvillarrealt@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hand_tracker = xarm_vision.hand_tracker:main',
            'arm_controller = xarm_vision.arm_controller:main',
            'robot_arm_controller = xarm_vision.robot_arm_controller:main',
        ],
    },
)
