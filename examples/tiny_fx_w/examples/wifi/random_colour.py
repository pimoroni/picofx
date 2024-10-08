import time
import network
import requests
from tiny_fx import TinyFX

"""
Press "Boot" to exit the program.
"""
# secrets.py should contain:
# WIFI_SSID = ""
# WIFI_PASSWORD = ""

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    print("Create secrets.py with your WiFi credentials")


# Constants
MONO_NAMES = ("One", "Two", "Three", "Four", "Five", "Six")
COLOUR_NAMES = ("R", "G", "B")

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board


# Connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while wlan.isconnected() == False:
    print('Waiting for connection...')
    time.sleep(1)

ip = wlan.ifconfig()[0]
print(f'Connected on {ip}')


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    while True:    
        req = requests.get("https://random-flat-colors.vercel.app/api/random?count=2").json()

        mono =  tuple(int(req['colors'][0][i:i+1], 16) / 15 for i in range(1, 7))
        colour =  tuple(int(req['colors'][1][i:i+2], 16) for i in (1, 3, 5))
        
        for i in range(len(tiny.outputs)):
            tiny.outputs[i].brightness(mono[i])
            print(f"{MONO_NAMES[i]} = {round(mono[i], 2)}", end=", ")

        tiny.rgb.set_rgb(*colour)
        for i in range(len(colour)):
            print(f"{COLOUR_NAMES[i]} = {colour[i]}", end=", ")
        
        print()
        
        time.sleep(5)
    
# Turn off all the outputs
finally:
    tiny.shutdown()
    wlan.disconnect()