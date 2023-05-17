import os
import sys
from time import sleep
import wiringpi


wiringpi.wiringPiSetupGpio()
wiringpi.pinMode(18, 0)

while True:
    if (wiringpi.digitalRead(18)== 1 and (not os.system("linphonecsh generic 'calls'"))):
        sleep(1)
        print("button pressed")
        os.system("bash /usr/local/sbin/test_autodial.sh")

