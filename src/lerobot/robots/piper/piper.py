# Implementation of Piper robot for LeRobot

from dataclasses import dataclass, field
from typing import Any

from lerobot.cameras import CameraConfig, make_cameras_from_configs
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.robots import Robot, RobotConfig

from .piper_sdk_interface import PiperSDKInterface


@RobotConfig.register_subclass("piper")
@dataclass
class PiperConfig(RobotConfig):
    port: str
    cameras: dict[str, CameraConfig] = field(default_factory=dict)




class Piper(Robot):
    config_class = PiperConfig
    name = "piper"

    def __init__(self, config: PiperConfig):
        super().__init__(config)
        self.sdk = PiperSDKInterface(port=config.port)
        self.cameras = make_cameras_from_configs(config.cameras)

    @property
    def _motors_ft(self) -> dict[str, type]:
        return {f"joint_{i}.pos": float for i in range(7)}

    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        return {cam: (self.cameras[cam].height, self.cameras[cam].width, 3) for cam in self.cameras}

    @property
    def observation_features(self) -> dict:
        return {**self._motors_ft, **self._cameras_ft}

    @property
    def action_features(self) -> dict:
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        # Assume always connected after SDK init
        return True

    def connect(self, calibrate: bool = True) -> None:
        # Already connected in SDK init
        for cam in self.cameras.values():
            cam.connect()
        self.configure()

    def disconnect(self) -> None:
        self.sdk.disconnect()
        for cam in self.cameras.values():
            cam.disconnect()

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    def get_observation(self) -> dict[str, Any]:
        obs_dict = self.sdk.get_status()

        for cam_key, cam in self.cameras.items():
            obs_dict[cam_key] = cam.async_read()
        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        # This will handle both key styles.
        # For teleop, action.get('shoulder_pan') will work. For stop(), action.get('joint_0.pos') will work.
        # The second get() acts as a fallback.
        positions = [
            action.get("shoulder_pan", action.get("joint_0.pos")),
            action.get("shoulder_lift", action.get("joint_1.pos")),
            action.get("elbow_flex", action.get("joint_2.pos")),
            action.get("joint_3.pos", 0),
            action.get("wrist_flex", action.get("joint_4.pos")),
            action.get("wrist_roll", action.get("joint_5.pos")),
            action.get("gripper", action.get("joint_6.pos")),
        ]

        self.sdk.set_joint_positions(positions)
        return action

    def stop(self):
        current_pos = self.sdk.get_status()
        self.send_action(current_pos)
