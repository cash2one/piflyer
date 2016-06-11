import zmq
import random
import time
import zmq_ports as ports
from selenium import webdriver

SEND_DELAY=0.02
RCV_DELAY=0.02

class comm():
    def __init__(self):
        #self.display = Display(visible=0, size=(480, 320))
        #self.display.start()
        print("Starting firefox")

        firefox_profile = webdriver.FirefoxProfile()
        #firefox_profile = DesiredCapabilities.FIREFOX()
        firefox_profile.set_preference('permissions.default.stylesheet', 2)
        firefox_profile.set_preference('permissions.default.image', 2)
        firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
        firefox_profile.set_preference("media.navigator.permission.disabled", True);

        firefox_profile1 = webdriver.FirefoxProfile()
        # firefox_profile = DesiredCapabilities.FIREFOX()
        firefox_profile1.set_preference('permissions.default.stylesheet', 2)
        firefox_profile1.set_preference('permissions.default.image', 2)
        firefox_profile1.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
        firefox_profile1.set_preference("media.navigator.permission.disabled", True);

        self.datadriver = webdriver.Firefox(firefox_profile=firefox_profile)
        self.datadriver.set_window_size(480, 320)

        self.videodriver=webdriver.Firefox(firefox_profile=firefox_profile1)
        self.videodriver.set_window_size(480, 320)
        self.start()
        self.streaming=False
        self.lastmsg= ""
        self.connchecktime=0
        self.sendtimer=0
        self.rcvtimer=0
        self.isConnected=False

    def start(self):
        self.datadriver.get('http://peerclient.cloudapp.net/peer1.html')
        self.videodriver.get('http://peerclient.cloudapp.net/peer1.html')
        try:
            time.sleep(3)
            self.msg = self.datadriver.find_element_by_id('msg')
            self.sender = self.datadriver.find_element_by_id('sender')
            self.receiver = self.datadriver.find_element_by_id('receiver')
            self.connection = self.datadriver.find_element_by_id('connected')
            print(self.connection)
            self.videoswitch = self.videodriver.find_element_by_id('videoswitch')
        except:
            pass


    def reset(self):
        try:
            if (self.datadriver.find_element_by_id('refresh').text != 'false'):
                print("refreshing")
                self.datadriver.refresh()
                self.videodriver.refresh()
                self.start()
                self.streaming = False
        except:
            pass

    def connected(self):
        # print("check-connected")
        t = round(time.time(), 1)
        if (t - self.connchecktime > 1 and t - self.rcvtimer > 3):
            self.connchecktime = round(t, 1)
            text = ""
            try:
                text = self.connection.text
            except:
                pass

            if (text != "true"):
                self.isConnected = False
                self.reset()
                return False
        self.isConnected = True
        return True

    def readMsg(self):
        result = None
        t0 = time.time()
        if (t0 - self.rcvtimer > RCV_DELAY):
            try:
                text = self.receiver.text
                if (text != self.lastmsg):
                    t = time.time()
                    dt = t - t0
                    self.rcvtimer = t
                    self.lastmsg = text
                    result = text
                    #print("comm:readMsg", dt)
            except:
                pass
        return result

    def sendMsg(self, msg):
        t = time.time()
        if (t - self.sendtimer > SEND_DELAY):
            #try:
            self.datadriver.execute_script('sendstr("' + msg + '")')
            self.sendtimer = t
            return True
            #except:


    def startVideoStream(self):
        if (self.isConnected and not self.streaming):
            try:
                self.updateIsStreaming()
                self.videodriver.execute_script('document.getElementById("videoswitch").click()')
                time.sleep(1)
            except:
                print("mediastreamopen error")

    def updateIsStreaming(self):
        print("updateIsStreaming")
        try:
            x = self.videodriver.execute_script('return isMediaStreamOpen()')
        except:
            return
        self.streaming = x

    def close(self):
        self.datadriver.close()
        self.videodriver.close()
        #self.display.stop()

if __name__ == '__main__':
    # Publisher
    context = zmq.Context()
    commander_publisher = context.socket(zmq.PUB)
    commander_publisher.bind("tcp://*:%s" % ports.COMM_PUB)

    # Subscribe to commander
    commander_subscriber = context.socket(zmq.SUB)
    commander_subscriber.connect("tcp://localhost:%s" % ports.COMMANDER_PUB)
    commander_subscriber.setsockopt_string(zmq.SUBSCRIBE, "10001")

    xcomm=comm()
    topic = 10001
    while True:
        if(xcomm.connected()):
            xcomm.startVideoStream()
            # from browser to commander
            """topic = random.randrange(9999, 10005)
            messagedata = random.randrange(1, 215) - 80
            print("%d %d" % (topic, messagedata))"""
            messagedata = xcomm.readMsg()
            if messagedata != None:
                commander_publisher.send_string("%d %s" % (topic, messagedata))

            # from commander to browser
            while True:
                try:
                    msg = commander_subscriber.recv_string(zmq.DONTWAIT)
                    xcomm.sendMsg(msg)
                except zmq.Again:
                    break
                # process task
                #print("comm received:", msg)

            time.sleep(0.005)