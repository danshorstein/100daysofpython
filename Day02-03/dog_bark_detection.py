import time
from datetime import datetime
import importlib.util

import RPi.GPIO as GPIO

from services.lcd_screen import update_display
from services.send_push import send_push

count = 0
last_bark_time = None

ch = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(ch, GPIO.IN)



def callback(ch):
    global count, last_bark_time
    count += 1
    print('heard a sound!')
    last_bark_time = datetime.now()
    update_display(last_bark_time, count)
    send_push(last_bark_time.replace(microsecond=0), count)

        
GPIO.add_event_detect(ch, GPIO.BOTH, bouncetime=800)
GPIO.add_event_callback(ch, callback)

while True:
    update_display(last_bark_time, count)
    time.sleep(.9)

