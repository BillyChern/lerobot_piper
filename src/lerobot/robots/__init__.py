from .config import RobotConfig
from .robot import Robot
from .utils import make_robot_from_config

# Import robot modules to register them
from . import hope_jr
from . import koch_follower
from . import piper
from . import so100_follower
from . import so101_follower

# This will register PiperClientConfig
from .piper import PiperClient
