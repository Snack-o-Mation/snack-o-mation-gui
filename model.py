import logging
import math
import struct

from pydobot import Dobot
from pydobot.enums.CommunicationProtocolIDs import CommunicationProtocolIDs
from pydobot.enums.ControlValues import ControlValues
from pydobot.message import Message
from serial import Serial

# dimensions of a Maoam Bloxx in millimeters
BLOXX_OFFSET_X = 47
BLOXX_OFFSET_Y = 29
BLOXX_OFFSET_Z = 19

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Coordinates:

    def __init__(self, x=None, y=None, z=None):
        self.x = None
        self.y = None
        self.z = None
        self.set(x, y, z)

    def is_valid(self):
        # return True if all coordinates are set
        return self.x is not None and self.y is not None and self.z is not None

    def set_x(self, x):
        self.x = x

    def set_y(self, y):
        self.y = y

    def set_z(self, z):
        self.z = z

    def set(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def clear(self):
        self.set(None, None, None)

    def __add__(self, other):
        return Coordinates(self.x + other.x, self.y + other.y, self.z + other.z)

    def __repr__(self):
        return "(%f, %f, %f)" % (self.x, self.y, self.z)


class Storage:
    DIM_X = 2
    DIM_Y = 3
    CAPACITY = DIM_X * DIM_Y

    def __init__(self, stock=0):
        self.stock = stock
        self.pos = 0

    def get_stock(self):
        return self.stock

    def get_delivered(self):
        return self.CAPACITY - self.stock

    def is_empty(self):
        return self.stock == 0

    def fill(self, value=CAPACITY):
        self.stock = value
        self.pos = 0

    def get_next_position(self):
        return self.pos

    def pop(self):
        if self.stock == 0:
            return None
        else:
            # every 3 blocks go to next row of blocks
            x = (self.pos // self.DIM_Y) * BLOXX_OFFSET_X
            y = (self.pos % self.DIM_Y) * BLOXX_OFFSET_Y
            self.stock -= 1
            self.pos += 1
            return Coordinates(-x, y, 0)


class Conveyor:
    def __init__(self, robot):
        self.running = False
        self.dobot = robot.dobot

    def is_running(self):
        return self.running

    def start(self):
        logger.info("start conveyor")
        # Calculate the speed of the conveyor belt in mm per second
        steps_per_circle = 360.0 / 1.8 * 10.0 * 16.0
        mm_per_circle = math.pi * 36.0
        speed = -60 * steps_per_circle / mm_per_circle

        # prepare message
        msg = Message()
        msg.id = 135
        msg.ctrl = ControlValues.THREE  # rw = 1, queued = 0
        # EMotor struct: { uint8_t index (0 = Stepper 1), uint8_t insEnabled (1 enable motor control), float speed}
        msg.params = bytearray(struct.pack('<BBi', 0, 1, int(speed)))
        self.dobot._send_command(msg)
        self.running = True

    def stop(self):
        logger.info("stop conveyor")
        msg = Message()
        msg.id = 135
        msg.ctrl = ControlValues.ONE  # rw = 1, queued = 0
        # EMotor struct: { uint8_t index (0 = Stepper 1), uint8_t insEnabled (0 disable motor control), float speed}
        msg.params = bytearray(struct.pack('<BBi', 0, 0, 0))
        self.dobot._send_command(msg)
        self.running = False


class LightSensor:
    # Note: light sensor needs to be connected to GP2 input as follows:
    # GND (pin 0, left), GND (blue)
    # REV (pin 1): EIO13, 5V/1A output (brown)
    # PWM (pin 2): EIO14, light sensor input signal (black)
    # ADC (pin 3, right): not connected

    def __init__(self, robot):
        self.dobot = robot.dobot
        # initialize IR light sensor
        # https://github.com/luismesas/pydobot/issues/22#issuecomment-595820711
        msg = Message()
        msg.id = 138
        msg.ctrl = ControlValues.ONE
        msg.params = bytearray([])
        msg.params.extend(bytearray([int(True)]))
        msg.params.extend(bytearray([Robot.PORT_GP2]))
        self.dobot._send_command(msg)

    def has_object(self):
        # https://github.com/luismesas/pydobot/issues/22#issuecomment-595820711
        msg = Message()
        msg.id = 138
        msg.ctrl = 0x00
        msg.params = bytearray([])
        msg.params.extend(bytearray([Robot.PORT_GP2]))
        response = self.dobot._send_command(msg)
        if response is None:
            return False
        else:
            state = struct.unpack_from('?', response.params, 0)[0]
            return state


class Robot:
    HOME_COORDINATES = Coordinates(260, 0, 40)
    # end effector offset of the suction cup
    END_EFFECTOR_OFFSET_X = 59.7
    END_EFFECTOR_OFFSET_Y = 0.0
    END_EFFECTOR_OFFSET_Z = 0.0
    # GP port configuration
    PORT_GP1 = 0x00
    PORT_GP2 = 0x01
    PORT_GP4 = 0x02
    PORT_GP5 = 0x03

    def __init__(self, port, verbose=False):
        self.dobot = Dobot(port=port, verbose=verbose)

    def calibrate(self):
        # set end effector parameters for the suction cup
        msg = Message()
        msg.id = CommunicationProtocolIDs.SET_GET_END_EFFECTOR_PARAMS
        msg.ctrl = ControlValues.ONE
        msg.params = bytearray([])
        msg.params.extend(bytearray(struct.pack('f', self.END_EFFECTOR_OFFSET_X)))
        msg.params.extend(bytearray(struct.pack('f', self.END_EFFECTOR_OFFSET_Y)))
        msg.params.extend(bytearray(struct.pack('f', self.END_EFFECTOR_OFFSET_Z)))
        self.dobot._send_command(msg)
        # move to home position
        self.move(self.HOME_COORDINATES)
        # perform calibration (homing function)
        msg = Message()
        msg.id = CommunicationProtocolIDs.SET_HOME_CMD
        msg.ctrl = ControlValues.ONE
        msg.params = bytearray([])
        msg.params.extend(bytearray(struct.pack('i', 0)))  # uint32_t reserved
        self.dobot._send_command(msg)

    def move(self, dest: Coordinates):
        self.dobot.move_to(dest.x, dest.y, dest.z, 0)

    def show(self, dest: Coordinates):
        # show the location by moving there and "tipping" on it
        hover_offset = Coordinates(0, 0, 50)
        self.move(dest + hover_offset)
        self.wait(500)
        self.move(dest)
        self.wait(1000)
        self.move(dest + hover_offset)
        self.wait(500)
        self.move(self.HOME_COORDINATES)

    def wait(self, ms):
        self.dobot.wait(ms)

    def clear_alarms(self):
        msg = Message()
        msg.id = 20
        msg.ctrl = 0x01
        self.dobot._send_command(msg)

    def home(self):
        self.move(self.HOME_COORDINATES)

    def pickup_and_place(self, pickup_coords: Coordinates, place_coords: Coordinates, z_hover=50):
        # move to the pickup coordinates (plus specified z_hover)
        self.dobot.move_to(pickup_coords.x, pickup_coords.y, pickup_coords.z + z_hover, 0)
        # wait 1 second
        self.dobot.wait(1000)
        # move down to the pickup coordinates
        self.dobot.move_to(pickup_coords.x, pickup_coords.y, pickup_coords.z, 0)
        # enable suction cup
        self.dobot.suck(True)
        # wait 1 second
        self.dobot.wait(1000)
        # move to the pickup coordinates (plus specified z_hover)
        self.dobot.move_to(pickup_coords.x, pickup_coords.y, pickup_coords.z + z_hover, 0)
        # wait 1 second
        self.dobot.wait(1000)
        # move robot arm to the place coordinates (plus specified z_hover)
        self.dobot.move_to(place_coords.x, place_coords.y, place_coords.z + z_hover, 0)
        # wait 1 second
        self.dobot.wait(1000)
        # move robot arm to the place coordinates
        self.dobot.move_to(place_coords.x, place_coords.y, place_coords.z, 0)
        # disable suction cup
        self.dobot.suck(False)
        # wait 1 second
        self.dobot.wait(1000)
        # move robot arm to the place coordinates (plus specified z_hover)
        self.dobot.move_to(place_coords.x, place_coords.y, place_coords.z + z_hover, 0)

    def pose(self):
        try:
            data = self.dobot.pose()
        except Exception as e:
            logger.error("Error reading pose: %s" % e)
            return None
        return Coordinates(data[0], data[1], data[2])

    def close(self):
        self.dobot.close()


class RadioListener:
    def __init__(self, device):
        self.device = device
        self.microbit = Serial(port=device, baudrate=115200, timeout=0.02)

    def get_packet(self):
        if self.microbit:
            try:
                packet = self.microbit.read_until()
                if packet is None or len(packet) == 0:
                    return None
                else:
                    packet = packet.decode("ascii")
                    return packet
            except Exception as e:
                logger.error("Error reading radio packet: %s" % e)
                return None
        else:
            return None

    def close(self):
        if self.microbit:
            self.close()
            self.microbit = None
