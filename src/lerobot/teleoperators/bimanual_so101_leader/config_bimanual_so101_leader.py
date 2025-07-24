from dataclasses import dataclass, field
from pathlib import Path

from lerobot.teleoperators.config import TeleoperatorConfig
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig


@TeleoperatorConfig.register_subclass("bimanual_so101_leader")
@dataclass
class BimanualSO101LeaderConfig(TeleoperatorConfig):
    left_arm: SO101LeaderConfig = field(default_factory=lambda: SO101LeaderConfig(port="/dev/ttyUSB0"))
    right_arm: SO101LeaderConfig = field(default_factory=lambda: SO101LeaderConfig(port="/dev/ttyUSB1"))
    calibration_dir: Path | None = None 
    # Base names (without .json) for calibration files for each arm
    left_calib_name: str = "left_arm"
    right_calib_name: str = "right_arm" 