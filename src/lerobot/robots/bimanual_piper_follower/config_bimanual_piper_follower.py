from dataclasses import dataclass, field

from lerobot.robots.config import RobotConfig
from lerobot.robots.piper.piper import PiperConfig
from lerobot.cameras import CameraConfig


@RobotConfig.register_subclass("bimanual_piper_follower")
@dataclass
class BimanualPiperFollowerConfig(RobotConfig):
    left_arm: PiperConfig = field(default_factory=lambda: PiperConfig(port="left_piper"))
    right_arm: PiperConfig = field(default_factory=lambda: PiperConfig(port="right_piper"))
    cameras: dict[str, CameraConfig] = field(default_factory=dict)


@RobotConfig.register_subclass("bimanual_piper_client")
@dataclass
class BimanualPiperClientConfig(RobotConfig):
    # Network Configuration
    remote_ip: str
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    polling_timeout_ms: int = 15
    connect_timeout_s: int = 5 