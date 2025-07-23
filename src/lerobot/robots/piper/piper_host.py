#!/usr/bin/env python
import json
import logging
import time
from dataclasses import asdict, dataclass, field

import draccus
import zmq

from lerobot.robots.config import RobotConfig
from lerobot.robots.piper.config_piper import PiperHostConfig
from lerobot.robots.piper.piper import Piper


@dataclass
class PiperHostScriptConfig:
    robot: RobotConfig = field(default_factory=RobotConfig)
    host: PiperHostConfig = field(default_factory=PiperHostConfig)


class PiperHost:
    def __init__(self, config: PiperHostConfig):
        self.zmq_context = zmq.Context()
        self.zmq_cmd_socket = self.zmq_context.socket(zmq.PULL)
        self.zmq_cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_cmd_socket.bind(f"tcp://*:{config.port_zmq_cmd}")

        self.zmq_observation_socket = self.zmq_context.socket(zmq.PUSH)
        self.zmq_observation_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_observation_socket.bind(f"tcp://*:{config.port_zmq_observations}")

        self.connection_time_s = config.connection_time_s
        self.watchdog_timeout_ms = config.watchdog_timeout_ms
        self.max_loop_freq_hz = config.max_loop_freq_hz

    def disconnect(self):
        self.zmq_observation_socket.close()
        self.zmq_cmd_socket.close()
        self.zmq_context.term()


@draccus.wrap()
def main(cfg: PiperHostScriptConfig):
    logging.info("Configuring Piper")
    robot = Piper(cfg.robot)

    logging.info("Connecting Piper")
    robot.connect()

    logging.info("Starting HostAgent")
    host = PiperHost(cfg.host)

    first_command_received = False
    last_cmd_time = time.time()
    watchdog_active = False
    logging.info("Waiting for commands...")
    try:
        # Business logic
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
                _action_sent = robot.send_action(data)

            except zmq.Again:
                pass  # No command received yet, just continue waiting.
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Message parsing failed: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")

            now = time.time()
            if first_command_received and (now - last_cmd_time > host.watchdog_timeout_ms / 1000) and not watchdog_active:
                logging.warning(
                    f"Command not received for more than {host.watchdog_timeout_ms} milliseconds. Stopping the robot."
                )
                watchdog_active = True
                robot.stop()

            last_observation = robot.get_observation()
            serializable_observation = {}
            for key, value in last_observation.items():
                try:
                    json.dumps(value)
                    serializable_observation[key] = value
                except TypeError:
                    serializable_observation[key] = str(value)

            # Send the observation to the remote agent
            try:
                host.zmq_observation_socket.send_string(
                    json.dumps(serializable_observation), flags=zmq.NOBLOCK
                )
            except zmq.Again:
                logging.info("Dropping observation, no client connected")
            except TypeError as e:
                logging.error(f"Observation serialization failed: {e}")

            # Ensure a short sleep to avoid overloading the CPU.
            elapsed = time.time() - loop_start_time

            time.sleep(max(1 / host.max_loop_freq_hz - elapsed, 0))

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    finally:
        print("Shutting down Piper Host.")
        robot.disconnect()
        host.disconnect()

    logging.info("Finished Piper cleanly")


if __name__ == "__main__":
    main() 