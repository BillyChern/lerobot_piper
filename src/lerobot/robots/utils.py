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

import logging
from pprint import pformat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import RobotConfig
    from .robot import Robot

from lerobot.robots import RobotConfig

from .robot import Robot


def make_robot_from_config(config: "RobotConfig") -> "Robot":  # noqa: F821
    """Make a robot from a `RobotConfig` object."""
    from .robot import Robot  # noqa: F801

    logging.info(f"Attempting to create robot from config of type: {type(config)}")
    logging.info(f"Config details: {config}")

    subclasses = Robot.__subclasses__()
    logging.info(f"Available Robot subclasses: {subclasses}")

    # This is the new way of instantiating robots.
    for robot_cls in subclasses:
        logging.info(f"Checking robot class: {robot_cls} with config_class: {getattr(robot_cls, 'config_class', None)}")
        if getattr(robot_cls, "config_class", None) == config.__class__:
            logging.info(f"Found matching robot class by config_class: {robot_cls}")
            return robot_cls(config)

    # The following is for backward compatibility with the old way of defining robots.
    # TODO(rcadene): remove this when all robots are migrated.
    for robot_cls in subclasses:
        logging.info(f"Checking robot class: {robot_cls} with name: {getattr(robot_cls, 'name', None)}")
        if getattr(robot_cls, "name", None) == config.type:
            logging.info(f"Found matching robot class by name: {robot_cls}")
            return robot_cls(config)

    logging.error(f"No matching robot class found for type: {config.type}")
    raise ValueError(config.type)


def ensure_safe_goal_position(
    goal_present_pos: dict[str, tuple[float, float]], max_relative_target: float | dict[float]
) -> dict[str, float]:
    """Caps relative action target magnitude for safety."""

    if isinstance(max_relative_target, float):
        diff_cap = dict.fromkeys(goal_present_pos, max_relative_target)
    elif isinstance(max_relative_target, dict):
        if not set(goal_present_pos) == set(max_relative_target):
            raise ValueError("max_relative_target keys must match those of goal_present_pos.")
        diff_cap = max_relative_target
    else:
        raise TypeError(max_relative_target)

    warnings_dict = {}
    safe_goal_positions = {}
    for key, (goal_pos, present_pos) in goal_present_pos.items():
        diff = goal_pos - present_pos
        max_diff = diff_cap[key]
        safe_diff = min(diff, max_diff)
        safe_diff = max(safe_diff, -max_diff)
        safe_goal_pos = present_pos + safe_diff
        safe_goal_positions[key] = safe_goal_pos
        if abs(safe_goal_pos - goal_pos) > 1e-4:
            warnings_dict[key] = {
                "original goal_pos": goal_pos,
                "safe goal_pos": safe_goal_pos,
            }

    if warnings_dict:
        logging.warning(
            "Relative goal position magnitude had to be clamped to be safe.\n"
            f"{pformat(warnings_dict, indent=4)}"
        )

    return safe_goal_positions
