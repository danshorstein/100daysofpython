import time
from datetime import datetime, timedelta

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# 128x32 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

def update_display(last_bark_time, barks_today):

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    current_time = datetime.now().replace(microsecond=0)
    if last_bark_time is None:
        time_since_bark = None
    else:
        last_bark_time = last_bark_time.replace(microsecond=0)
        time_since_bark = current_time - last_bark_time
        last_bark_time = last_bark_time.time()

    current_time = current_time.time()

    draw.text((x, top),       "Current time {}".format(current_time),  font=font, fill=255)
    draw.text((x, top+8),     "Last bark at {}".format(last_bark_time),  font=font, fill=255)
    draw.text((x, top+16),    "Since bark    {}".format(time_since_bark),  font=font, fill=255)
    draw.text((x, top+25),    '{} barks today'.format(barks_today),  font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.display()


