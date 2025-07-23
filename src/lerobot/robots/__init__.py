from .config import RobotConfig
from .robot import Robot
from .utils import make_robot_from_config

# Import robot modules to register them
from . import hope_jr
from . import koch_follower
from . import piper
from . import so100_follower
from . import so101_follower

# This will register PiperClientConfig by importing the module where it's defined.
from .piper.piper_client import PiperClient
