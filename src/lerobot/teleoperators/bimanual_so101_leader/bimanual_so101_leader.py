import logging
from typing import Any

from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError
from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot.teleoperators.so101_leader.so101_leader import SO101Leader
from .config_bimanual_so101_leader import BimanualSO101LeaderConfig

logger = logging.getLogger(__name__)


class BimanualSO101Leader(Teleoperator):
    """
    A bimanual teleoperator composed of two SO101 leader arms.
    """

    config_class = BimanualSO101LeaderConfig
    name = "bimanual_so101_leader"

    def __init__(self, config: BimanualSO101LeaderConfig):
        super().__init__(config)
        self.config = config
        self.left_arm = SO101Leader(config.left_arm)
        self.right_arm = SO101Leader(config.right_arm)

    @property
    def action_features(self) -> dict[str, type]:
        left_action_features = self.left_arm.action_features
        right_action_features = self.right_arm.action_features
        combined_action_features = {}
        for key in left_action_features:
            combined_action_features[f"left_{key}"] = left_action_features[key]
        for key in right_action_features:
            combined_action_features[f"right_{key}"] = right_action_features[key]
        return combined_action_features

    @property
    def feedback_features(self) -> dict:
        return {}

    @property
    def is_connected(self) -> bool:
        return self.left_arm.is_connected and self.right_arm.is_connected

    def connect(self, calibrate: bool = True) -> None:
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")

        self.left_arm.connect(calibrate=calibrate)
        self.right_arm.connect(calibrate=calibrate)

        logger.info(f"{self} connected.")

    @property
    def is_calibrated(self) -> bool:
        return self.left_arm.is_calibrated and self.right_arm.is_calibrated

    def calibrate(self) -> None:
        self.left_arm.calibrate()
        self.right_arm.calibrate()

    def configure(self) -> None:
        self.left_arm.configure()
        self.right_arm.configure()

    def get_action(self) -> dict[str, Any]:
        left_action = self.left_arm.get_action()
        right_action = self.right_arm.get_action()
        combined_action = {}
        for key, value in left_action.items():
            combined_action[f"left_{key}"] = value
        for key, value in right_action.items():
            combined_action[f"right_{key}"] = value
        return combined_action

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        # Assuming feedback is prefixed with left_ or right_
        left_feedback = {k.replace("left_", ""): v for k, v in feedback.items() if k.startswith("left_")}
        right_feedback = {k.replace("right_", ""): v for k, v in feedback.items() if k.startswith("right_")}
        self.left_arm.send_feedback(left_feedback)
        self.right_arm.send_feedback(right_feedback)

    def disconnect(self) -> None:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        self.left_arm.disconnect()
        self.right_arm.disconnect()
        logger.info(f"{self} disconnected.") 