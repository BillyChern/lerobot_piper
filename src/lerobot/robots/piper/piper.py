# Implementation of Piper robot for LeRobot

from dataclasses import dataclass, field
from typing import Any

from lerobot.cameras import CameraConfig, make_cameras_from_configs
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.robots import Robot, RobotConfig

from .piper_sdk_interface import PiperSDKInterface
from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError


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
        self.config = config
        self.sdk = None
        self._is_connected = False
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
        return self._is_connected

    def connect(self, calibrate: bool = True) -> None:
        if self._is_connected:
            raise DeviceAlreadyConnectedError(f"{self} is already connected.")
        self.sdk = PiperSDKInterface(port=self.config.port)
        self._is_connected = True
        for cam in self.cameras.values():
            cam.connect()
        self.configure()

    def disconnect(self) -> None:
        if not self._is_connected:
            return
        self.sdk.disconnect()
        for cam in self.cameras.values():
            cam.disconnect()
        self._is_connected = False

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    def get_observation(self) -> dict[str, Any]:
        if not self._is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        obs_dict = self.sdk.get_status()

        for cam_key, cam in self.cameras.items():
            obs_dict[cam_key] = cam.async_read()
        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self._is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        # map the action from the leader to joints for the follower
        # This will handle both key styles.
        # For teleop, action.get('shoulder_pan.pos') will work. For stop(), action.get('joint_0.pos') will work.
        # The second get() acts as a fallback.
        positions = [
            action.get("shoulder_pan.pos", action.get("joint_0.pos", 0)),
            action.get("shoulder_lift.pos", action.get("joint_1.pos", 0)),
            action.get("elbow_flex.pos", action.get("joint_2.pos", 0)),
            action.get("joint_3.pos", 0),
            action.get("wrist_flex.pos", action.get("joint_4.pos", 0)),
            action.get("wrist_roll.pos", action.get("joint_5.pos", 0)),
            action.get("gripper.pos", action.get("joint_6.pos", 0)),
        ]

        self.sdk.set_joint_positions(positions)
        return action

    def stop(self):
        if not self._is_connected:
            return
        current_pos = self.sdk.get_status()
        self.send_action(current_pos)
