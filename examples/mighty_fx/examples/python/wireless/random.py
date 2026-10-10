import time

import network
import requests
from mighty_fx import MightyFX

"""
Show random colours obtained from the internet on MightyFX's outputs.

One colour is asked for per output, so every output shows a different one.

This example requires a secrets.py file to be on your board's file system with the credentials of your WiFi network.

Press "Boot" to exit the program.
"""

try:
    from secrets import WIFI_PASSWORD, WIFI_SSID
    if len(WIFI_SSID) == 0:
        raise ValueError("no WiFi network set. Open the 'secrets.py' file on your device to add your WiFi credentials")
except ImportError:
    raise ImportError("no module named 'secrets'. Create a 'secrets.py' file on your device with your WiFi credentials") from None


# Constants
OUTPUT_NAMES = ("One", "Two", "Three", "Four", "Five", "Six", "Seven")
CONNECTION_INTERVAL = 1.0               # The time to sleep between each connection check
REQUEST_INTERVAL = 5.0                  # The time to sleep between each internet request

# Variables
mighty = MightyFX()                     # Create a new MightyFX object to interact with the board
wlan = network.WLAN(network.STA_IF)     # Create a new network object for interacting with WiFI


# Wrap the code in a try block, to catch any exceptions (including KeyboardInterrupt)
try:
    # Connect to WLAN
    wlan.active(True)
    print(f"Connecting to network '{WIFI_SSID}'")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # Wait until the connection is established
    while not wlan.isconnected():
        print("Waiting for connection...")
        time.sleep(CONNECTION_INTERVAL)

    # Print out our IP address
    print(f"Connected on {wlan.ifconfig()[0]}")

    # Loop forever
    while True:
        # Get a colour for each output from the internet
        req = requests.get(f"https://random-flat-colors.vercel.app/api/random?count={len(mighty.outputs)}")
        json = req.json()
        req.close()

        # Set each output to its colour, and print the values
        for i in range(len(mighty.outputs)):
            colour = tuple(int(json["colors"][i][c:c + 2], 16) for c in (1, 3, 5))
            mighty.outputs[i].set_rgb(*colour)
            print(f"{OUTPUT_NAMES[i]} = {colour}", end=", ")

        print()

        time.sleep(REQUEST_INTERVAL)

# Turn off all the outputs
finally:
    mighty.shutdown()
    wlan.disconnect()
