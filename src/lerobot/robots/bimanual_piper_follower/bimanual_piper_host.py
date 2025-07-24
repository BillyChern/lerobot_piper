#!/usr/bin/env python
import json
import logging
import time
from dataclasses import dataclass, field

import draccus
import zmq

from lerobot.robots.bimanual_piper_follower.config_bimanual_piper_follower import BimanualPiperFollowerConfig
from lerobot.robots.bimanual_piper_follower.bimanual_piper_follower import BimanualPiperFollower
from lerobot.robots.piper.piper import PiperConfig


@dataclass
class BimanualPiperHostConfig:
    """A flat config for the bimanual piper host script to avoid draccus recursion."""
    left_arm_port: str = "left_piper"
    right_arm_port: str = "right_piper"
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556
    max_loop_freq_hz: int = 60


class BimanualPiperHost:
    def __init__(self, port_zmq_cmd, port_zmq_observations, max_loop_freq_hz):
        self.zmq_context = zmq.Context()
        self.zmq_cmd_socket = self.zmq_context.socket(zmq.PULL)
        self.zmq_cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_cmd_socket.bind(f"tcp://*:{port_zmq_cmd}")

        self.zmq_observation_socket = self.zmq_context.socket(zmq.PUSH)
        self.zmq_observation_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_observation_socket.bind(f"tcp://*:{port_zmq_observations}")

        self.max_loop_freq_hz = max_loop_freq_hz

    def disconnect(self):
        self.zmq_observation_socket.close()
        self.zmq_cmd_socket.close()
        self.zmq_context.term()


@draccus.wrap()
def main(cfg: BimanualPiperHostConfig):
    robot_config = BimanualPiperFollowerConfig(
        left_arm=PiperConfig(port=cfg.left_arm_port),
        right_arm=PiperConfig(port=cfg.right_arm_port),
        cameras={}
    )
    
    logging.info("Configuring Bimanual Piper")
    robot = BimanualPiperFollower(robot_config)

    logging.info("Connecting Bimanual Piper")
    robot.connect()

    logging.info("Starting HostAgent")
    host = BimanualPiperHost(
        port_zmq_cmd=cfg.port_zmq_cmd,
        port_zmq_observations=cfg.port_zmq_observations,
        max_loop_freq_hz=cfg.max_loop_freq_hz,
    )

    first_command_received = False
    last_cmd_time = time.time()
    watchdog_active = False
    logging.info("Waiting for commands...")
    try:
        while True:
            loop_start_time = time.time()
            try:
                msg = host.zmq_cmd_socket.recv_string(zmq.NOBLOCK)
                if not first_command_received:
                    logging.info("First command received. Starting teleoperation.")
                    first_command_received = True
                last_cmd_time = time.time()
                watchdog_active = False
                data = json.loads(msg)
                robot.send_action(data)

            except zmq.Again:
                pass
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Message parsing failed: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")

            now = time.time()
            if first_command_received and (now - last_cmd_time > 50_000_000) and not watchdog_active:
                logging.warning(
                    "Command not received for a long time. Stopping the robot."
                )
                watchdog_active = True
                # How to stop a bimanual robot? Maybe stop each arm.
                robot.left_arm.stop()
                robot.right_arm.stop()

            last_observation = robot.get_observation()
            serializable_observation = {}
            for key, value in last_observation.items():
                try:
                    json.dumps(value)
                    serializable_observation[key] = value
                except TypeError:
                    serializable_observation[key] = str(value)

            try:
                host.zmq_observation_socket.send_string(
                    json.dumps(serializable_observation), flags=zmq.NOBLOCK
                )
            except zmq.Again:
                logging.info("Dropping observation, no client connected")
            except TypeError as e:
                logging.error(f"Observation serialization failed: {e}")

            elapsed = time.time() - loop_start_time
            time.sleep(max(1 / host.max_loop_freq_hz - elapsed, 0))

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    finally:
        print("Shutting down Bimanual Piper Host.")
        robot.disconnect()
        host.disconnect()

    logging.info("Finished Bimanual Piper cleanly")


if __name__ == "__main__":
    main() 