import logging
import time
from threading import Event

from model import Coordinates, Storage, BLOXX_OFFSET_X, BLOXX_OFFSET_Z
from model import Robot, LightSensor, Conveyor, RadioListener
from sim import SimRobot, SimLightSensor, SimConveyor, SimRadioListener

# keys for the coordinates locations
STORAGE1_KEY = 'storage_1'
STORAGE2_KEY = 'storage_2'
BELT_DROPOFF_KEY = 'belt_dropoff'
BELT_PICKUP_KEY = 'belt_pickup'
DELIVERY_KEY = 'delivery'

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_coordinates(text):
    name = text[0].lower()
    value = float(text[2:])
    return name, value


def parse_numbers(text):
    parts = text.split(",")
    first = max(0, int(parts[0]))
    second = max(0, int(parts[1]))
    return first, second


class Controller:

    def __init__(self, device_left, device_right, device_microbit, num_tasks, sim=False, interval=0.005, verbose=False):
        self.parent = None
        self.exit_requested = False
        self.is_running = False
        self.isDelivering = False
        self.items_delivered = 0
        self.current_storage_key = None
        self.robot_left = None
        self.robot_right = None
        self.num_tasks = num_tasks
        self.coordinates = None
        self.storage = None
        self.orders = None
        self.tasks = None
        self.interval = interval
        self.event = Event()

        if not sim:
            logger.info("Init Robot left: %s" % device_left)
            self.robot_left = Robot(port=device_left, verbose=verbose)
            logger.info("Init Robot right: %s" % device_right)
            self.robot_right = Robot(port=device_right, verbose=verbose)
            # IR light sensor and conveyor belt are attached to the right robot
            self.sensor = LightSensor(self.robot_right)
            self.conveyor = Conveyor(self.robot_right)
            logger.info("Init microbit listener: %s" % device_microbit)
            self.sniffer = RadioListener(device_microbit)
        else:
            logger.info("Init simulated Robot left")
            self.robot_left = SimRobot(verbose=verbose)
            logger.info("Init simulated Robot right")
            self.robot_right = SimRobot(verbose=verbose)
            self.sensor = SimLightSensor()
            self.conveyor = SimConveyor()
            logger.info("Init simulated microbit listener")
            self.sniffer = SimRadioListener()


    def set_parent(self, parent):
        self.parent = parent

    def _emit_state_update(self):
        if self.parent:
            self.parent.signals.update_state.emit({
                "coordinates": self.coordinates,
                "storage": self.storage,
                "orders": self.orders,
                "tasks": self.tasks,
                "delivering": self.isDelivering
            })

    def reset_state(self):
        """
        Reset the controller state
        """
        logger.info("reset controller state")
        self.coordinates = {
            STORAGE1_KEY: Coordinates(),
            STORAGE2_KEY: Coordinates(),
            BELT_DROPOFF_KEY: Coordinates(),
            BELT_PICKUP_KEY: Coordinates(),
            DELIVERY_KEY: Coordinates()
        }
        # data structure for storage locations
        self.storage = {
            STORAGE1_KEY: Storage(),
            STORAGE2_KEY: Storage()
        }
        self.orders = {
            STORAGE1_KEY: 0,
            STORAGE2_KEY: 0
        }
        self.tasks = [False] * self.num_tasks
        self._emit_state_update()

    def set_default(self):
        """
        reset to default settings
        """
        logger.info("reset controller state to default settings")
        self.coordinates = {
            STORAGE1_KEY: Coordinates(x=119, y=183, z=-50),
            STORAGE2_KEY: Coordinates(x=6, y=183, z=-50),
            BELT_DROPOFF_KEY: Coordinates(x=266, y=91, z=5),
            BELT_PICKUP_KEY: Coordinates(x=267, y=27, z=0),
            DELIVERY_KEY: Coordinates(x=48, y=-198, z=-55)
        }
        # data structure for storage locations
        self.storage = {
            STORAGE1_KEY: Storage(6),
            STORAGE2_KEY: Storage(6)
        }
        self.orders = {
            STORAGE1_KEY: 1,
            STORAGE2_KEY: 1
        }
        self.tasks = [True] * self.num_tasks
        self._emit_state_update()

    def terminate(self):
        if self.is_running:
            self.exit_requested = True
            self.event.set()

    def set_coordinate(self, key, name, value):
        if key in self.coordinates:
            if name == 'x':
                self.coordinates[key].set_x(value)
            elif name == 'y':
                self.coordinates[key].set_y(value)
            elif name == 'z':
                self.coordinates[key].set_z(value)

    def clear_coordinates(self, key):
        if key in self.coordinates:
            self.coordinates[key].clear()

    def set_storage(self, key, value):
        if key in self.storage:
            self.storage[key].fill(value)

    def set_orders(self, key, value):
        if key in self.orders:
            self.orders[key] = value

    def start_delivery(self):
        logger.info("startDelivery requested")
        if not self.isDelivering:
            if all(self.tasks) and (self.orders[STORAGE1_KEY] > 0 or self.orders[STORAGE2_KEY] > 0) and (
                    not self.storage[STORAGE1_KEY].is_empty() or not self.storage[STORAGE2_KEY].is_empty()):
                logger.info("Starting delivery of order:", self.orders)
                self.items_delivered = 0
                self.current_storage_key = None
                self.isDelivering = True
                self._emit_state_update()
        else:
            logger.error("Already in delivery mode")

    def stop_delivery(self):
        logger.info("stopDelivery requested")
        self.isDelivering = False
        # stop the conveyor
        self.conveyor.stop()
        # go to the home position
        self.robot_left.move(Robot.HOME_COORDINATES)
        self.robot_right.move(Robot.HOME_COORDINATES)
        self._emit_state_update()

    def loop(self):
        """ main loop of the controller """
        self.is_running = True
        self.items_delivered = 0
        self.reset_state()
        logger.info("starting controller main loop")
        # initialize robots and conveyor belt
        self.conveyor.stop()
        self.robot_left.clear_alarms()
        self.robot_right.clear_alarms()
        self.robot_left.move(Robot.HOME_COORDINATES)
        self.robot_right.move(Robot.HOME_COORDINATES)

        while not self.exit_requested:
            self.event.wait(self.interval)
            if self.exit_requested:
                break

            # left robot
            if self.robot_left:
                pose_left = self.robot_left.pose()
            else:
                pose_left = None
            # right robot
            if self.robot_right:
                pose_right = self.robot_right.pose()
            else:
                pose_right = None

            # send pose to UI
            if self.parent:
                self.parent.signals.update_pose.emit([pose_left, pose_right])

            # check for radio messages
            radio_message = self.sniffer.get_packet()
            if radio_message is not None:
                logger.info("radio packet received: %s" % radio_message)
                task, data = self.parse_message(radio_message)
                if task is not None and data is not None:
                    # check for action commands
                    if task == 8:
                        command = data.strip()
                        if command == "start":
                            # start delivery
                            logger.info("starting delivery requested by radio message")
                            self.start_delivery()

            if self.isDelivering:
                # check light sensor
                if not self.sensor.has_object():
                    #  nothing in front of sensor, check if belt is running
                    if not self.conveyor.is_running():
                        # belt is not running, decide from which storage to pick up
                        if not self.storage[STORAGE1_KEY].is_empty() and self.orders[STORAGE1_KEY] > 0 and not \
                                self.storage[
                                    STORAGE2_KEY].is_empty() and self.orders[STORAGE2_KEY] > 0:
                            # both storage locations have items -> swap storage location to be used
                            if self.current_storage_key is None or self.current_storage_key == STORAGE2_KEY:
                                self.current_storage_key = STORAGE1_KEY
                            else:
                                self.current_storage_key = STORAGE2_KEY
                        elif not self.storage[STORAGE1_KEY].is_empty() and self.orders[STORAGE1_KEY] > 0:
                            # use storage 1
                            self.current_storage_key = STORAGE1_KEY
                        elif not self.storage[STORAGE2_KEY].is_empty() and self.orders[STORAGE2_KEY] > 0:
                            # use storage 2
                            self.current_storage_key = STORAGE2_KEY
                        else:
                            # both storage locations are empty
                            self.current_storage_key = None

                        if self.current_storage_key is not None:
                            # pick from storage and place on the belt
                            offset = self.storage[self.current_storage_key].pop()
                            pickup = self.coordinates[self.current_storage_key] + offset
                            place = self.coordinates[BELT_DROPOFF_KEY]
                            self.robot_right.pickup_and_place(pickup, place)
                            # start the conveyor belt
                            self.conveyor.start()
                            self.robot_right.wait(500)
                            self.robot_right.move(Robot.HOME_COORDINATES)
                            # update remaining orders
                            self.orders[self.current_storage_key] -= 1
                            # update state
                            self._emit_state_update()
                else:
                    if self.conveyor.is_running():
                        # something in front of sensor, stop belt and pick it up.
                        # wait a bit until the item is directly in front of the sensor
                        self.conveyor.stop()
                        # pick up from belt and deliver
                        # every 3 blocks go to next row of blocks
                        offset_x = (self.items_delivered // 3) * (BLOXX_OFFSET_X + 10)
                        offset_z = (self.items_delivered % 3) * BLOXX_OFFSET_Z
                        pickup = self.coordinates[BELT_PICKUP_KEY]
                        place = self.coordinates[DELIVERY_KEY] + Coordinates(-offset_x, 0, offset_z)
                        self.robot_left.pickup_and_place(pickup, place)
                        self.robot_left.move(Robot.HOME_COORDINATES)
                        self.items_delivered += 1
                        if self.orders[STORAGE1_KEY] == 0 and self.orders[STORAGE2_KEY] == 0:
                            logger.info("Delivery completed: Items delivered: %u" % self.items_delivered)
                            self.isDelivering = False
                        # update state
                        self._emit_state_update()

        # end of main controller loop -> terminated
        logger.info("main controller loop terminated")
        if self.robot_left:
            self.robot_left.close()
        if self.robot_right:
            self.robot_right.close()
        self.is_running = False

    def parse_message(self, text):
        task_to_key = {
            1: STORAGE1_KEY,
            2: STORAGE2_KEY,
            3: BELT_DROPOFF_KEY,
            4: BELT_PICKUP_KEY,
            5: DELIVERY_KEY
        }

        try:
            task, data = text.split("#")
            task = int(task)
            logger.info("Task: %u Data: %s" % (task, data))

            if 1 <= task <= 5:
                name, value = parse_coordinates(data)
                key = task_to_key[task]
                self.set_coordinate(key, name, value)
                self.tasks[task - 1] = self.coordinates[key].is_valid()
            elif task == 6:
                # storage levels
                storage_1, storage_2 = parse_numbers(data)
                self.set_storage(STORAGE1_KEY, storage_1)
                self.set_storage(STORAGE2_KEY, storage_2)
            elif task == 7:
                # orders
                order_1, order_2 = parse_numbers(data)
                self.orders[STORAGE1_KEY] = order_1
                self.orders[STORAGE2_KEY] = order_2
            elif task == 8:
                # start delivery
                pass
            else:
                # unknown task
                logger.info("Unknown task: %u" % task)
                task = None
                data = None

            # send update to the gui
            self._emit_state_update()
            if self.parent:
                self.parent.signals.update_packet.emit(text, True)
            return task, data

        except Exception as e:
            logger.error(e)
            if self.parent:
                self.parent.signals.update_packet.emit(text, False)
            return None, None