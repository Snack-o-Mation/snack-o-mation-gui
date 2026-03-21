import logging

from model import Coordinates

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SimConveyor:
    def __init__(self):
        self.running = False

    def is_running(self):
        return self.running

    def start(self):
        logger.info("Conveyor started")
        self.running = True

    def stop(self):
        logger.info("Conveyor stopped")
        self.running = False


class SimLightSensor:

    def __init__(self):
        self.detected = False

    def has_object(self):
        return self.detected


class SimRobot:
    HOME_COORDINATES = Coordinates(200, 0, 40)

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.current_pose = self.HOME_COORDINATES

    def calibrate(self):
        pass

    def move(self, dest: Coordinates):
        self.current_pose.set(dest.x, dest.y, dest.z)

    def wait(self, ms):
        pass

    def pickup_and_place(self, pickup_coords: Coordinates, place_coords: Coordinates, z_hover=50):
        pass

    def release(self):
        pass

    def pose(self):
        return self.current_pose

    def home(self):
        pass

    def show(self, dest: Coordinates):
        pass

    def clear_alarms(self):
        pass

    def close(self):
        pass


class SimRadioListener:
    def __init__(self):
        self.packets = [
            "1#x=119", "1#y=183", "1#z=-50",
            "2#x=6", "2#y=183", "2#z=-50",
            "3#x=266",
            "4#x=267", "4#y=27", "4#z=0",
            "6#6,6", "7#1,1",
        ]

    def get_packet(self):
        if self.packets:
            packet = self.packets[0]
            self.packets = self.packets[1:]
            return packet
        else:
            return None

    def close(self):
        pass
