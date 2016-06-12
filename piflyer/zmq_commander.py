import random
import time
import zmq
import zmq_ports as ports

from zmq_sensors import sensors
from elevons import elevons
from motor_handler import motor_handler
import commands as c
from camera import camera

MODE="M"
CONTROL="C"
HOLD="H"

ALT="T"
AUTO="A"

CAMERA="S"
RECORD="R"

MANUAL="m"
STABILIZED="s"
RESQUE="r"

DISCONNECT = "X"
SERVO_INIT = "SI"
SERVO_LIMIT = "SL"
TILT_PITCH_LIMIT = "PL"
TILT_ROLL_LIMIT = "RL"
THROTTLE_LIMIT = "TL"

class commander:
    def __init__(self):
        self.mode="m"

        self.pitch_hold=False
        #self.hdg_hold=False
        self.alt_hold=False
        self.auto_hold=False

        self.status=c.OK
        self.servos_init=False
        self.throttle_updated=False

        self.pitch=0.0
        self.roll=0.0
        self.throttle=0.0
        self.compass=0.0
        self.altittude=0.0

        self.elevons = elevons()
        self.sensors = sensors()
        self.motor=motor_handler()
        self.camera=camera()

    def getParameters(self):
        return [self.pitch,self.roll,self.throttle]

    def setMode(self,mode):
        self.mode=mode

    def setHold(self,words):
        if(words[1] == ALT):
            self.alt_hold=bool(int(words[2]))
            print("ALT_HOLD: %s" % (self.alt_hold))
        elif(words[1] == AUTO):
            self.auto_hold = bool(int(words[2]))
            print("AUTO_HOLD: %s" % (self.auto_hold))

    #process command
    def update(self,arg=""):
        self.status=c.OK
        words=arg.split(',')
        if (words[0] == MODE):
            self.setMode(words[1])
        elif(words[0] == CONTROL):
            self.servos_init=False
            self.pitch=float(words[1])
            self.roll=float(words[2])
            if(len(words)>=4):
                self.throttle=float(words[3])
                self.throttle_updated=True
        elif(words[0] == CAMERA):
            self.camera.takeShot()
        elif(words[0] == RECORD):
            self.camera.recording(words[1])
        #hold functions
        elif (words[0] == HOLD):
            self.setHold(words)
        elif (words[0] == AUTO):
            if(self.auto_hold):
                self.compass=float(words[1])
                if (self.alt_hold):
                    self.altittude=float(words[2])
                else:
                    self.pitch=words[2]
        elif (words[0] == SERVO_INIT):
            self.servos_init=True
            self.elevons.setServosUpDirection(int(words[1]), int(words[2]))
        elif(words[0] == SERVO_LIMIT):
            self.servos_init=True
            self.elevons.setServosUpDownLimit(int(words[1]), int(words[2]))
        elif (words[0] == TILT_PITCH_LIMIT):
            self.servos_init = True
            self.elevons.setPitchTiltLimits(int(words[1]), int(words[2]))
        elif (words[0] == TILT_ROLL_LIMIT):
            self.servos_init = True
            self.elevons.setRollTiltLimits(int(words[1]), int(words[2]))
        elif (words[0] == THROTTLE_LIMIT):
            self.servos_init = True
            self.motor.setThrottleLimits(int(words[1]), int(words[2]))
        else:
            self.status=c.INVALID
            print("status invalid")
        return self.status

    def control(self):
        if(not self.servos_init):
            if(self.mode == MANUAL):
                #print("Manual %f %f" % (self.pitch,self.roll))
                #constantly updated even if no change ... not ok
                self.elevons.setAngle(self.pitch,self.roll)
                #self.elevons.setRoll(self.roll)
                # not tested
                if(self.throttle_updated):
                    self.throttle_updated=False
                    self.motor.setThrottleFromInput(self.throttle)

            # not tested
            elif(self.mode == STABILIZED):
                print("Stabilized %f %f" % (self.pitch,self.roll))
                if(self.alt_hold):
                    print("Alt hold, controlling roll")
                else:
                    self.elevons.control(self.pitch,self.roll,self.sensors.pitch,self.sensors.roll)
                if (self.throttle_updated):
                    self.throttle_updated = False
                    self.motor.setThrottleFromInput(self.throttle)

            # not tested
            elif(self.mode == RESQUE):
                self.elevons.control(0,0,self.sensors.pitch,self.sensors.roll)
                #self.motor. ...

    # not tested
    def failsafe(self):
        print("failsafe")
        #TODO control in reference to altitude, speed and glide slope
        self.elevons.control(0,0,self.sensors.pitch,self.sensors.roll)
        #self.motor.control(0)


if __name__ == '__main__':
    print("Starting commander")
    # Publisher
    context = zmq.Context()
    comm_publisher = context.socket(zmq.PUB)
    comm_publisher.bind("tcp://*:%s" % ports.COMMANDER_PUB)

    # Subscribe to commander
    topic = "10001"
    comm_subscriber = context.socket(zmq.SUB)
    comm_subscriber.connect("tcp://localhost:%s" % ports.COMM_PUB)
    comm_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)

    # Subscribe to sensors
    sensors_subscriber = context.socket(zmq.SUB)
    sensors_subscriber.connect("tcp://localhost:%s" % ports.SENSORS_PUB)
    sensors_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)

    # Initiate commander
    commander=commander()

    while True:
        # send data
        #topic = random.randrange(9999, 10001)
        messagedata = random.randrange(1, 215) - 80
        #print("%d %d" % (topic, messagedata))
        #comm_publisher.send_string("%s %s" % (topic, "test"))

        while True:
            # receive data from comm
            try:
                data = comm_subscriber.recv_string(zmq.DONTWAIT)
            except zmq.Again:
                break
            # process task
            commander.update(data)
            #print("commander received:", msg)

        while True:
            # from sensors to comm, update sensors instance
            try:
                sens_data = sensors_subscriber.recv_string(zmq.DONTWAIT)
            except zmq.Again:
                break
            # process task
            sens_data = sens_data.strip(topic + " ")

            commander.sensors.setValues(sens_data)
            comm_publisher.send_string("%s %s" % (topic, sens_data))
        time.sleep(0.005)

