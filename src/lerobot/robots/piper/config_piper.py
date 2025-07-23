 
from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig


@dataclass
class PiperHostConfig:
    # Network Configuration
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    # For how long the robot should stay in host mode.
    connection_time_s: int = 3600  # 1 hour
    # Timeout after which the robot will stop moving if no command is received.
    watchdog_timeout_ms: int = 500
    # The max frequency of the host loop.
    max_loop_freq_hz: int = 60


@RobotConfig.register_subclass("piper_client")
@dataclass
class PiperClientConfig(RobotConfig):
    # Network Configuration
    remote_ip: str
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    polling_timeout_ms: int = 15
    connect_timeout_s: int = 5 