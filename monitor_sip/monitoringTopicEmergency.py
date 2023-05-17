#!/usr/bin/python

import ssl, sys, json, time, signal, getopt
import os
import paho.mqtt.client as paho
from datetime import datetime

#HOST = 'localhost'
HOST = 'mqtt.tago.io'
#HOST = '13.77.65.102'
#PORT = 2883
PORT = 1883
QOS = 1

class MonitoringTopicMQTT(paho.Client):
    
    TOPIC_RCVD = 'IPHEALTH/0x5c0272fffee9b0e2/single'

    def __init__(self):
        self.client = paho.Client(client_id='client_1', clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set("andrey", "dbd6ad7e-9e15-4d91-9d8f-d5720e568d73")
        self.client.connect(HOST, 1883)

       # self.client.on_subscribe = self.on_subscribe
#        self.is_connected = False
        self.is_subscribed = False
        self.is_config = 0
        self._id = 0
        self.port = 1883
        self.QOS = QOS
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            print('1 Connected (as %s)' % client._client_id)
        else:
            print('Failed to connect, return code %d\n',rc)
           
    def on_message(self,client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if "single" in msg.payload.decode():
            os.system("bash /usr/local/sbin/test_autodial.sh")


    def run(self):
        print('Connecting to broker...')
        try:
            self.client.connect(host=HOST, port=PORT)
            ### start loop
            self.client.loop_start()
            
            while not self.is_connected:
                time.sleep(0.1)
            
            self.client.subscribe(self.TOPIC_RCVD, self.QOS)
            while not self.is_subscribed:
                time.sleep(0.1)
        
        except Exception as e:
            print(e)
            self.stop()

    def stop(self):
        self.client.loop_stop()
    
if __name__ == '__main__':
    server = MonitoringTopicMQTT()
    server.run() 
sys.exit(0)
