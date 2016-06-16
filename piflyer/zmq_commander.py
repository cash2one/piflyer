import random
import time
import zmq

import zmq_ports as ports
import zmq_topics as topic

from zmq_sensors import sensors
from elevons import elevons
from motor_handler import motor_handler
import commands as c
from camera import camera

MODE = "M"
CONTROL = "C"
HOLD = "H"

ALT = "T"
AUTO = "A"

CAMERA = "S"
RECORD = "R"

MANUAL = "m"
STABILIZED = "s"
RESQUE = "r"

DISCONNECT = "X"
SERVO_INIT = "SI"
SERVO_LIMIT = "SL"
TILT_PITCH_LIMIT = "PL"
TILT_ROLL_LIMIT = "RL"
THROTTLE_LIMIT = "TL"


class commander:
    def __init__(self):
        self.mode = "m"

        self.pitch_hold = False
        # self.hdg_hold=False
        self.alt_hold = False
        self.auto_hold = False
        self.is_connected = 0

        self.status = c.OK
        self.servos_init = False
        self.throttle_updated = False

        self.pitch = 0.0
        self.roll = 0.0
        self.throttle = 0.0
        self.compass = 0.0
        self.altittude = 0.0

        self.elevons = elevons()
        self.sensors = sensors()
        self.motor = motor_handler()
        self.camera = camera()

    def getParameters(self):
        return [self.pitch, self.roll, self.throttle]

    def setMode(self, mode):
        self.mode = mode

    def setHold(self, words):
        if (len(words) == 3):
            if (words[1] == ALT):
                self.alt_hold = bool(int(float(words[2])))
                print("ALT_HOLD: %s" % (self.alt_hold))
            elif (words[1] == AUTO):
                self.auto_hold = bool(int(float(words[2])))
                print("AUTO_HOLD: %s" % (self.auto_hold))

    # process command
    def update(self, arg=""):
        self.status = c.OK
        words = arg.split(',')
        if (words[0] == MODE):
            if (len(words) == 2):
                self.setMode(words[1])

        elif (words[0] == CONTROL):
            if (len(words) >= 3):
                self.servos_init = False
                self.pitch = int(float(words[1]))
                self.roll = int(float(words[2]))
            if (len(words) >= 4):
                self.throttle = int(words[3])
                self.throttle_updated = True

        elif (words[0] == CAMERA):
            self.camera.takeShot()

        elif (words[0] == RECORD):
            if (len(words) == 2):
                self.camera.recording(words[1])

        # hold functions
        elif (words[0] == HOLD):
            self.setHold(words)

        elif (words[0] == AUTO):
            if (len(words) == 3 and self.auto_hold):
                self.compass = float(words[1])
                if (self.alt_hold):
                    self.altittude = float(words[2])
                else:
                    self.pitch = words[2]
        elif (words[0] == SERVO_INIT):
            if (len(words) == 3):
                self.servos_init = True
                self.elevons.setServosUpDirection(int(float(words[1])), int(float(words[2])))
        elif (words[0] == SERVO_LIMIT):
            if (len(words) == 3):
                self.servos_init = True
                self.elevons.setServosUpDownLimit(int(float(words[1])), int(float(words[2])))
        elif (words[0] == TILT_PITCH_LIMIT):
            if (len(words) == 3):
                self.servos_init = True
                self.elevons.setPitchTiltLimits(int(float(words[1])), int(float(words[2])))
        elif (words[0] == TILT_ROLL_LIMIT):
            if (len(words) == 3):
                self.servos_init = True
                self.elevons.setRollTiltLimits(int(float(words[1])), int(float(words[2])))
        elif (words[0] == THROTTLE_LIMIT):
            if (len(words) == 3):
                self.servos_init = True
                self.motor.setThrottleLimits(int(float(words[1])), int(float(words[2])))
        else:
            self.status = c.INVALID
            # print("status invalid")
        return self.status

    def control(self):
        # print("control")
        if (not self.servos_init):
            if (self.mode == MANUAL):
                # print("Manual %f %f" % (self.pitch,self.roll))
                # constantly updated even if no change ... not ok
                self.elevons.setAngle(self.pitch, self.roll)
                # self.elevons.setRoll(self.roll)
                # not tested
                if (self.throttle_updated):
                    self.throttle_updated = False
                    self.motor.setThrottleFromInput(self.throttle)

            # not tested
            elif (self.mode == STABILIZED):
                print("Stabilized %f %f" % (self.pitch, self.roll))
                if (self.alt_hold):
                    print("Alt hold, controlling roll")
                else:
                    self.elevons.control(self.pitch, self.roll, self.sensors.pitch, self.sensors.roll)
                if (self.throttle_updated):
                    self.throttle_updated = False
                    self.motor.setThrottleFromInput(self.throttle)

            # not tested
            elif (self.mode == RESQUE):
                self.elevons.control(0, 0, self.sensors.pitch, self.sensors.roll)
                # self.motor. ...

    # not tested
    def failsafe(self):
        # print("failsafe")

        # TODO control in reference to altitude, speed and glide slope
        self.elevons.control(0, 0, self.sensors.pitch, self.sensors.roll)
        # self.motor.control(0)

    def run(self):
        # print(self.is_connected)
        if (self.is_connected):
            self.control()
        else:
            self.failsafe()


if __name__ == '__main__':
    # print("Starting commander")
    # Publisher
    context = zmq.Context()
    commander_publisher = context.socket(zmq.PUB)
    commander_publisher.bind("tcp://*:%s" % ports.COMMANDER_PUB)

    # Subscribe to comm messages
    comm_subscriber = context.socket(zmq.SUB)
    comm_subscriber.connect("tcp://localhost:%s" % ports.COMM_PUB)
    comm_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic.COMMAND_TOPIC)

    # Subscrine to comm connection info
    connection_subscriber = context.socket(zmq.SUB)
    connection_subscriber.connect("tcp://localhost:%s" % ports.COMM_PUB)
    connection_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic.CONNECTION_TOPIC)

    # Subscribe to sensors
    sensors_subscriber = context.socket(zmq.SUB)
    sensors_subscriber.connect("tcp://localhost:%s" % ports.SENSORS_PUB)
    sensors_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic.SENSOR_TOPIC)

    # Initiate commander
    commander = commander()

    while True:
        # Get connection info from comm
        while True:
            try:
                connection = connection_subscriber.recv_string(zmq.DONTWAIT)
            except zmq.Again:
                break
            # process task
            print(connection[2])
            commander.is_connected = int(connection[2])

        # Receive data from comm
        while True:
            try:
                data = comm_subscriber.recv_string(zmq.DONTWAIT)
            except zmq.Again:
                break
            # process task
            data = data.strip(topic.COMMAND_TOPIC + " ")
            commander.update(data)
            # print("commander received:", msg)

        # From sensors to comm, update sensors instanceđ
        while True:
            try:
                sens_data = sensors_subscriber.recv_string(zmq.DONTWAIT)
            except zmq.Again:
                break
            # process task
            sens_data = sens_data.strip(topic.SENSOR_TOPIC + " ")
            commander.sensors.setValues(sens_data)
            commander_publisher.send_string("%s %s" % (topic.SENSOR_TOPIC, sens_data))

        commander.run()
        time.sleep(0.005)
