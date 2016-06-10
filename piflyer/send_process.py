from multiprocessing import Process, Queue
import threading
import time
from random import randint
from selenium import webdriver
import sys
#pi
from pyvirtualdisplay import Display

SEND=0
RCV=1
END=2
##comm class
class comm1():
    def __init__(self):
        #pi
        self.display = Display(visible=0, size=(480, 320))
        self.display.start()

        firefox_profile = webdriver.FirefoxProfile()
        # firefox_profile = DesiredCapabilities.FIREFOX()
        firefox_profile.set_preference('permissions.default.stylesheet', 2)
        firefox_profile.set_preference('permissions.default.image', 2)
        firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
        firefox_profile.set_preference("media.navigator.permission.disabled", True);
        self.datadriver = webdriver.Firefox(firefox_profile=firefox_profile)
        self.datadriver.get('http://peerclient.cloudapp.net/peer1.html')
        self.receiver = self.datadriver.find_element_by_id('receiver')
        self.connection = self.datadriver.find_element_by_id('connected')
        self.text = self.receiver.text
    def read(self):
        #print("read",receivetext)
        text = self.receiver.text
        print("rcv:",text)

    def send(self,data):
        #print("send",data)
        self.datadriver.execute_script('sendstr("' + data[0] + '")')
    def connected(self):
        text = self.connected.text

#global com object
if __name__ != '__main__':
    com = comm1()
#process class
class process(Process):
    def __init__(self,q):
        super(process, self).__init__()
        self.q=q
        self.start()
    def run(self):
        end = False
        t = 0
        DELAY = 0.02
        while True:
            if (not self.q.empty()):
                data = self.q.get()
                if (data[0] == SEND):
                    com.send(data[1:])
                elif (data[0] == RCV):
                    com.read()
                elif (data[0] == END):
                    break;
            time.sleep(DELAY)
        com.display.stop()

def joinDelimiter(arr):
    tmp = [None] * len(arr)
    for i in range(len(arr)):
        tmp[i] = str(arr[i])
    return ",".join(tmp)

if __name__ == '__main__':
    q = Queue()
    dataprocess=process(q)
    #p = Process(target=dataprocess.run,args=(q,))
    if __name__ == '__main__':
        while(1):
            print("thread:", threading.get_ident())
            #0-send
            #1-read
            pitch = randint(3, 5)
            roll = randint(3, 5)
            yaw = randint(0, 2)
            compass = randint(240, 241)
            temp = randint(19, 20)
            humidity = randint(43, 46)
            pressure = randint(983, 985)
            ax = 0.1
            ay = 0.1
            az = 0.1
            altitude = 286
            q.put([SEND,joinDelimiter([pitch, roll, yaw, compass, temp, humidity,pressure, ax, ay,
                                   az, altitude])])
            #q.put([0,joinDelimiter([randint(0, 180), randint(0, 180), randint(0, 180)])])
            #q.put([0,joinDelimiter([randint(0, 180), randint(0, 180), randint(0, 180)])])
            #q.put([0,joinDelimiter([randint(0, 180), randint(0, 180), randint(0, 180)])])
            #q.put([0,joinDelimiter([randint(0, 180), randint(0, 180), randint(0, 180)])])
            #q.put([0,randint(0, 180), randint(0, 180), randint(0, 180)])
            q.put([1])
            time.sleep(0.05)
        #p.join()
        sys.exit()