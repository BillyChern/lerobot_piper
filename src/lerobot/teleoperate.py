# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Simple script to control a robot from teleoperation.

Example:

```shell
python -m lerobot.teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem58760431541 \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 1920, height: 1080, fps: 30}}" \
    --robot.id=black \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem58760431551 \
    --teleop.id=blue \
    --display_data=true
```
"""

import logging
import time
from dataclasses import asdict, dataclass, field
from pprint import pformat
from pathlib import Path

import draccus
import rerun as rr

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    hope_jr,
    koch_follower,
    make_robot_from_config,
    piper,
    so100_follower,
    so101_follower,
)
from lerobot.teleoperators import (  # noqa: F401
    Teleoperator,
    TeleoperatorConfig,
    gamepad,
    homunculus,
    koch_leader,
    make_teleoperator_from_config,
    so100_leader,
    so101_leader,
)
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.utils import init_logging, move_cursor_up
from lerobot.utils.visualization_utils import _init_rerun, log_rerun_data
from lerobot.robots.bimanual_piper_follower.config_bimanual_piper_follower import BimanualPiperFollowerConfig, BimanualPiperClientConfig
from lerobot.teleoperators.bimanual_so101_leader.config_bimanual_so101_leader import BimanualSO101LeaderConfig
from lerobot.robots.piper.piper import PiperConfig
from lerobot.robots.piper.piper_client import PiperClientConfig
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig


@dataclass
class BimanualTeleoperateConfig:
    """A flat config for bimanual teleoperation to avoid draccus recursion."""
    robot_type: str = "bimanual_piper_client"
    remote_ip: str = "100.117.16.87"
    teleop_type: str = "bimanual_so101_leader"
    left_leader_port: str = "/dev/ttyACM0"
    right_leader_port: str = "/dev/ttyACM1"
    fps: int = 60
    display_data: bool = False

@dataclass
class TeleoperateConfig:
    """A flat config for the teleoperation script to avoid draccus recursion."""
    # Robot parameters
    robot_type: str = "piper"
    remote_ip: str | None = None
    left_arm_port_robot: str = "left_piper"
    right_arm_port_robot: str = "right_piper"

    # Teleop parameters
    teleop_type: str = "so101_leader"
    left_arm_port_teleop: str = "/dev/ttyACM0"
    right_arm_port_teleop: str = "/dev/ttyACM1"
    teleop_calibration_dir: Path | None = None

    # Calibration file base names (without .json) when using bimanual teleop
    left_arm_calib_name: str = "left_arm"
    right_arm_calib_name: str = "right_arm"

    # General parameters
    bimanual: bool = False
    fps: int = 60
    teleop_time_s: int | None = None
    display_data: bool = False


def teleop_loop(
    teleop: Teleoperator, robot: Robot, fps: int, display_data: bool = False, duration: int | None = None
):
    display_len = max(len(key) for key in robot.action_features)
    start = time.perf_counter()
    while True:
        loop_start = time.perf_counter()
        action = teleop.get_action()
        if not action:
            print("Waiting for teleoperator data...")
            busy_wait(1 / fps)
            continue
        if display_data:
            observation = robot.get_observation()
            log_rerun_data(observation, action)

        # Debug print of action keys each loop
        if len(action) < 10:
            print(f"DEBUG Action keys: {list(action.keys())}")
        else:
            print(f"DEBUG Action keys: {list(action.keys())[:10]} ... total {len(action)} keys")

        robot.send_action(action)
        dt_s = time.perf_counter() - loop_start
        busy_wait(1 / fps - dt_s)

        loop_s = time.perf_counter() - loop_start

        print("\n" + "-" * (display_len + 10))
        print(f"{'NAME':<{display_len}} | {'NORM':>7}")
        for motor, value in action.items():
            print(f"{motor:<{display_len}} | {value:>7.2f}")
        print(f"\ntime: {loop_s * 1e3:.2f}ms ({1 / loop_s:.0f} Hz)")

        if duration is not None and time.perf_counter() - start >= duration:
            return

        move_cursor_up(len(action) + 5)


@draccus.wrap()
def teleoperate(cfg: TeleoperateConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name="teleoperation")

    if cfg.bimanual:
        if cfg.remote_ip:
            robot_config = BimanualPiperClientConfig(remote_ip=cfg.remote_ip)
        else:
            robot_config = BimanualPiperFollowerConfig(
                left_arm=PiperConfig(port=cfg.left_arm_port_robot),
                right_arm=PiperConfig(port=cfg.right_arm_port_robot),
            )
        teleop_config = BimanualSO101LeaderConfig(
            left_arm=SO101LeaderConfig(port=cfg.left_arm_port_teleop),
            right_arm=SO101LeaderConfig(port=cfg.right_arm_port_teleop),
            calibration_dir=cfg.teleop_calibration_dir,
            left_calib_name=cfg.left_arm_calib_name,
            right_calib_name=cfg.right_arm_calib_name,
            id="bimanual",
        )
    else:
        if cfg.remote_ip:
            robot_config = PiperClientConfig(remote_ip=cfg.remote_ip)
        else:
            robot_config = PiperConfig(port=cfg.right_arm_port_robot)
        teleop_config = SO101LeaderConfig(port=cfg.right_arm_port_teleop, calibration_dir=cfg.teleop_calibration_dir)

    robot = make_robot_from_config(robot_config)
    teleop = make_teleoperator_from_config(teleop_config)

    teleop.connect()
    robot.connect()

    try:
        teleop_loop(teleop, robot, cfg.fps, display_data=cfg.display_data, duration=cfg.teleop_time_s)
    except KeyboardInterrupt:
        pass
    finally:
        if cfg.display_data:
            rr.rerun_shutdown()
        teleop.disconnect()
        robot.disconnect()


if __name__ == "__main__":
    teleoperate()
