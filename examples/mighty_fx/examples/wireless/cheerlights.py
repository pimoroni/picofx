import time

import network
import requests
from mighty_fx import MightyFX

"""
Obtain the current CheerLights colour from the internet and show it on MightyFX's RGB outputs.
For more information about CheerLights, visit: https://cheerlights.com/

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
COLOUR_NAMES = ("R", "G", "B")
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
        # Get the current CheerLights colour from the internet
        req = requests.get("http://api.thingspeak.com/channels/1417/field/2/last.json")
        json = req.json()
        req.close()

        # Use the second to get the colour components for the RGB outputs
        colour = tuple(int(json["field2"][i:i + 2], 16) for i in (1, 3, 5))

        # Set every output to that colour, and print the values
        for output in mighty.outputs:
            output.set_rgb(*colour)

        for i in range(len(colour)):
            print(f"{COLOUR_NAMES[i]} = {colour[i]}", end=", ")

        print()

        time.sleep(REQUEST_INTERVAL)

# Turn off all the outputs
finally:
    mighty.shutdown()
    wlan.disconnect()
