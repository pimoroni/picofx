import time
import network
import requests
from tiny_fx import TinyFX

"""
Show random colours and patterns obtained from the internet on TinyFX's outputs.

This example requires a secrets.py file to be on your board's file system with the credentials of your WiFi network.

Press "Boot" to exit the program.
"""

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD
    if len(WIFI_SSID) == 0:
        raise ValueError("no WiFi network set. Open the 'secrets.py' file on your device to add your WiFi credentials")
except ImportError:
    raise ImportError("no module named 'secrets'. Create a 'secrets.py' file on your device with your WiFi credentials")


# Constants
MONO_NAMES = ("One", "Two", "Three", "Four", "Five", "Six")
COLOUR_NAMES = ("R", "G", "B")
CONNECTION_INTERVAL = 1.0               # The time to sleep between each connection check
REQUEST_INTERVAL = 5.0                  # The time to sleep between each internet request

# Variables
tiny = TinyFX()                         # Create a new TinyFX object to interact with the board
wlan = network.WLAN(network.STA_IF)     # Create a new network object for interacting with WiFI


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Connect to WLAN
    wlan.active(True)
    print(f"Connecting to network '{WIFI_SSID}'")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # Wait until the connection is established
    while not wlan.isconnected():
        print('Waiting for connection...')
        time.sleep(CONNECTION_INTERVAL)

    # Print out our IP address
    print(f'Connected on {wlan.ifconfig()[0]}')

    # Loop forever
    while True:
        # Get two colours from the internet
        req = requests.get("https://random-flat-colors.vercel.app/api/random?count=2")
        json = req.json()
        req.close()

        # Use the first to get brightness values for the six mono outputs
        mono = tuple(int(json['colors'][0][i:i + 1], 16) / 15 for i in range(1, 7))

        # Use the second to get the colour components for the RGB output
        colour = tuple(int(json['colors'][1][i:i + 2], 16) for i in (1, 3, 5))

        # Set the mono outputs, and print the values
        for i in range(len(tiny.outputs)):
            tiny.outputs[i].brightness(mono[i])
            print(f"{MONO_NAMES[i]} = {round(mono[i], 2)}", end=", ")

        # Set the colour output, and print the values
        tiny.rgb.set_rgb(*colour)
        for i in range(len(colour)):
            print(f"{COLOUR_NAMES[i]} = {colour[i]}", end=", ")

        print()

        time.sleep(REQUEST_INTERVAL)

# Turn off all the outputs
finally:
    tiny.shutdown()
    wlan.disconnect()
