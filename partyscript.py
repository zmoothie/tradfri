import sys
import os

folder = os.path.dirname(os.path.abspath(__file__))  # noqa
sys.path.insert(0, os.path.normpath("%s/.." % folder))  # noqa

from pytradfri import Gateway
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError
from pytradfri.util import load_json, save_json

import asyncio
import uuid
import argparse

CONFIG_FILE = 'tradfri_standalone_psk.conf'

parser = argparse.ArgumentParser()
parser.add_argument('host', metavar='IP', type=str, 
                    help='IP Address of your Tradfri gateway')
parser.add_argument('-K', '--key', dest='key', required=False,
                    help='Key found on your Tradfri gateway')
args = parser.parse_args()

if args.host not in load_json(CONFIG_FILE) and args.key is None:
    print("Please provide the 'Security Code' on the back of your "
          "Tradfri gateway:", end=" ")
    key = input().strip()
    if len(key) != 16:
        raise PytradfriError("Invalid 'Security Code' provided.")
    else:
        args.key = key


async def run():
    # Assign configuration variables.
    # The configuration check takes care they are present.
    conf = load_json(CONFIG_FILE)

    try:
        identity = conf[args.host].get('identity')
        psk = conf[args.host].get('key')
        api_factory = APIFactory(host=args.host, psk_id=identity, psk=psk)
    except KeyError:
        identity = uuid.uuid4().hex
        api_factory = APIFactory(host=args.host, psk_id=identity)

        try:
            psk = await api_factory.generate_psk(args.key)
            print('Generated PSK: ', psk)

            conf[args.host] = {'identity': identity,
                               'key': psk}
            save_json(CONFIG_FILE, conf)
        except AttributeError:
            raise PytradfriError("Please provide the 'Security Code' on the "
                                 "back of your Tradfri gateway using the "
                                 "-K flag.")

    api = api_factory.request

    gateway = Gateway()

    devices_command = gateway.get_devices()
    devices_commands = await api(devices_command)
    devices = await api(devices_commands)

    lights = [dev for dev in devices if dev.has_light_control]

    # Print all lights
    print(lights)

    # Lights can be accessed by its index, so lights[1] is the second light
    if lights:
        light = lights[0]
    else:
        print("No lights found!")
        light = None


    def turnOnOff(bulb, state):
        lights[bulb].light_control.set_state(state)

    def setColor(bulb, color):
        lights[bulb].light_control.set_hex_color(color)

    turnOnOff(0, 1)

    await asyncio.sleep(30)

    await api_factory.shutdown()

asyncio.run(run())