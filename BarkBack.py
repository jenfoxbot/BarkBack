####################################################
#Bark Back: Monitor & Interact with Pets!##
####################################################
# Code written by jenfoxbot <jenfoxbot@gmail.com>
# Code is open-source, coffee/beer-ware license.
# Please keep header + if you like the content,
# buy me a coffee and/or beer if you run into me!
#####################################################

#Libraries
import spidev
from threading import Thread
import mosquitto, os, urlparse

import subprocess
import random
import time
 

songList = ["SongFile1", #e.g. "/home/pi/Desktop/SongFile.mp3"
            "SongFile2",
            "SongFile3",
            "SongFile4"]

creds = {
    'CloudMQTT URL': 'INSERT_CLOUDMQTT_URL', #e.g. 'https://m10.cloudmqtt.com'
    'user': 'INSERT_CLOUDMQTT_USERNAME',
    'password': 'INSERT__CLOUDMQTT_PASSWORD',
    'host': 'INSERT_CLOUDMQTT_SERVER'
    'port': 'INSERT_CLOUDMQTT_PORT',
    'topic': 'INSERT_ACL_TOPIC'
    }

########################################################
#   Reading SparkFun MEMS Microphone Breakout Board
########################################################
#Step 1: Start SPI protocol.
spi = spidev.SpiDev()
spi.open(0,0) #This is the CE0 Pin (GPIO 08) on the RPi, for CE1, use (0,1)

#Function to read in CE0 channel
def read_spi(channel):
    spidata = spi.xfer2([96,0]) ##sending 2 bytes of data (96 and 0)
    data = ((spidata[0] & 3) << 8) + spidata[1]
    return data

#Function to calculate Peak to Peak Amplitude from MEMS mic
def PTPAmp():
    sampleTime = 0.05 #Sample Rate of 50 ms
    startTime = time.time()
    
    PTPAmp = 0
    maxAmp = 0
    minAmp = 1023

    while(time.time() - startTime < sampleTime):
        micOut = read_spi(0) #Read in channel CE0 
        if(micOut < 1023): #Prevent erroneous readings
            if(micOut > maxAmp):
                maxAmp = micOut
            elif(micOut < minAmp):
                minAmp = micOut

    PTPAmp = maxAmp - minAmp #Calculate peak-to-peak amp.
    return PTPAmp

#Function to map peak-to-peak amp to a volume unit between 0 and 10
def VolumeUnit(data, fromLow, fromHigh, toLow, toHigh):
    return (data - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow


########################################################
#   Class to Control OMXPlayer for Audio
########################################################
class OMXPlayer():
    def call_omxplayer(self):
        print ("playing " + self.file_path + '\n')
        pid = subprocess.Popen(['omxplayer', '-o', 'local',
                                self.file_path], stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE)
        self.is_running = False

    def play_song(self):
        if not self.is_running:
            self.song_thread = Thread(target=self.call_omxplayer, args=())
            self.song_thread.start()
            self.is_running = True

    def __init__(self, file_path):
        self.file_path = file_path
        self.is_running = False
        self.play_song()

#Function to select random song from list
def pickRandom(songList):
    return(random.choice(songList))


########################################################
#   CloudMQTT Server
########################################################
 # Define event callbacks
def on_connect(mosq, obj, rc):
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

#Call Client Server
mqttc = mosquitto.Mosquitto()
#Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe



# Uncomment to enable debug messages
#mqttc.on_log = on_log

# Parse CLOUDMQTT_URL (or fallback to localhost)
url_str = os.environ.get(creds['CloudMQTT URL'], 'mqtt://localhost:1883')
url = urlparse.urlparse(url_str)

# Connect
mqttc.username_pw_set(creds['user'], creds['password'])
mqttc.connect(creds['host'], creds['port'])

# Start subscribe, with QoS level 0
mqttc.subscribe(creds['topic'], 0)


########################################################
#   Main Function
########################################################
def main():

    while True:
        #1. Find ADC value for MEMS mic peak-to-peak amp
        PTPamp = PTPAmp()
        #2. Calculate ptp amp (Volts)
        PTPampV = round(((PTPamp*3.3) / 1024), 2)
        #3. Map ptp amp (ADC value) to Volume Unit between 0 and 10 
        VolUnit = VolumeUnit(PTPamp, 0, 1023, 0, 10)
                                                   
        #For debugging purposes
        print(PTPamp, VolUnit)
        time.sleep(.1)

        #4. If Volume Unit is greater than 8, play one of the songs
        if(VolUnit > 8):
            playBack = pickRandom(songList)
            OMXPlayer(playBack)
            time.sleep(1)

        #5. Upload data to CloudMQTT Server
        mqttc.publish(str(VolUnit), "Volume")
        rc = True
        while rc:
            rc = mqttc.loop()
            time.sleep(1)
        print("rc: " + str(rc))


    print ("Ready: !")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        GPIO.cleanup()
        myprocess.kill()


if __name__ == '__main__':
    main()
