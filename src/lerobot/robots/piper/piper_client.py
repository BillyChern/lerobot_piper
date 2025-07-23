
import json
from functools import cached_property
from typing import Any

import zmq

from lerobot.cameras import make_cameras_from_configs
from lerobot.robots.piper.config_piper import PiperClientConfig
from lerobot.robots.robot import Robot
from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError


class PiperClient(Robot):
    config_class = PiperClientConfig
    name = "piper_client"

    def __init__(self, config: PiperClientConfig):
        super().__init__(config)
        self.remote_ip = config.remote_ip
        self.port_zmq_cmd = config.port_zmq_cmd
        self.port_zmq_observations = config.port_zmq_observations
        self.connect_timeout_s = config.connect_timeout_s
        self._is_connected = False
        self.cameras = make_cameras_from_configs(config.cameras)
        self._cameras_ft = {cam: (self.cameras[cam].height, self.cameras[cam].width, 3) for cam in self.cameras}

    @cached_property
    def action_features(self) -> dict[str, type]:
        return {
            "shoulder_pan.pos": float,
            "shoulder_lift.pos": float,
            "elbow_flex.pos": float,
            "wrist_flex.pos": float,
            "wrist_roll.pos": float,
            "gripper.pos": float,
        }

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        motors_ft = {f"joint_{i}.pos": float for i in range(7)}
        return {**motors_ft, **self._cameras_ft}

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self) -> None:
        """Establishes ZMQ sockets with the remote mobile robot"""
        if self._is_connected:
            raise DeviceAlreadyConnectedError("Piper Daemon is already connected. Do not run `robot.connect()` twice.")
        self.zmq_context = zmq.Context()
        self.zmq_cmd_socket = self.zmq_context.socket(zmq.PUSH)
        zmq_cmd_locator = f"tcp://{self.remote_ip}:{self.port_zmq_cmd}"
        self.zmq_cmd_socket.connect(zmq_cmd_locator)
        self.zmq_cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_observation_socket = self.zmq_context.socket(zmq.PULL)
        zmq_observations_locator = f"tcp://{self.remote_ip}:{self.port_zmq_observations}"
        self.zmq_observation_socket.connect(zmq_observations_locator)
        self.zmq_observation_socket.setsockopt(zmq.CONFLATE, 1)
        poller = zmq.Poller()
        poller.register(self.zmq_observation_socket, zmq.POLLIN)
        socks = dict(poller.poll(self.connect_timeout_s * 1000))
        if self.zmq_observation_socket not in socks or socks[self.zmq_observation_socket] != zmq.POLLIN:
            raise DeviceNotConnectedError("Timeout waiting for Piper Host to connect expired.")
        self._is_connected = True
        for cam in self.cameras.values():
            cam.connect()

    def disconnect(self) -> None:
        self.zmq_observation_socket.close()
        self.zmq_cmd_socket.close()
        self.zmq_context.term()
        self._is_connected = False
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
        """Get an observation from the remote host."""
        raw_obs = self.zmq_observation_socket.recv_string()
        return json.loads(raw_obs)

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send an action to the remote host."""
        self.zmq_cmd_socket.send_string(json.dumps(action))
        return action 