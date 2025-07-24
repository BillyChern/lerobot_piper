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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import TeleoperatorConfig
    from .teleoperator import Teleoperator


def make_teleoperator_from_config(config: "TeleoperatorConfig") -> "Teleoperator":  # noqa: F821
    """Make a teleoperator from a `TeleoperatorConfig` object."""
    from .teleoperator import Teleoperator

    subclasses = Teleoperator.__subclasses__()
    logging.info(f"Available Teleoperator subclasses: {subclasses}")

    for teleop_cls in subclasses:
        logging.info(f"Checking teleop class: {teleop_cls} with config_class: {getattr(teleop_cls, 'config_class', None)}")
        if getattr(teleop_cls, "config_class", None) == config.__class__:
            logging.info(f"Found matching teleop class by config_class: {teleop_cls}")
            return teleop_cls(config)

    for teleop_cls in subclasses:
        logging.info(f"Checking teleop class: {teleop_cls} with name: {getattr(teleop_cls, 'name', None)}")
        if getattr(teleop_cls, "name", None) == config.type:
            logging.info(f"Found matching teleop class by name: {teleop_cls}")
            return teleop_cls(config)

    logging.error(f"No matching teleop class found for type: {config.type}")
    raise ValueError(config.type)
