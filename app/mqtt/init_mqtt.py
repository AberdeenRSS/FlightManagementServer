import asyncio
import threading
from time import sleep
from fastapi import FastAPI
import paho.mqtt.client as mqtt

from app.mqtt.measurments import process_measurements
from app.services.auth.jwt_auth_service import get_self_access_token

MAX_PACKETS = 2000
RETRY_DELAY = 5 # Retry delay on failed connection

packet_received = False
mqtt_stop_token = False
mqtt_thread: threading.Thread | None = None
"""
### MQTT thread:

The mqtt client is running on a seperate thread to not interfere with other server tasks
The mqtt loop repeatatly checks if the stop token has been set to true, if so it stops
the mqtt loop.

This way either new mqtt measurements are received **or** mongodb tasks are exectued. This is
useful as it creates back pressure, where if the mongodb tasks take long no new tasks are
received either
"""

def mqtt_main(host):

    global mqtt_stop_token

    while not mqtt_stop_token:

        try:
            # Initialize the MQTT client
            client = mqtt.Client()

            setup_callbacks(client)

            client.username_pw_set('server', get_self_access_token())

            client.connect(host)

            asyncio.run(mqtt_asyncio_loop(client))
        except Exception as e:
            print(f'Mqtt failed: {e}. Retrying in {RETRY_DELAY}s')
            sleep(RETRY_DELAY)
    
    print('Mqtt shutting down')

async def mqtt_asyncio_loop(client: mqtt.Client):

    global mqtt_stop_token
    global packet_received

    while not mqtt_stop_token:

        if not packet_received:
            await asyncio.sleep(0.2)

        packet_received = False

        client.loop_read(MAX_PACKETS)
        client.loop_write()
        client.loop_misc()


def start_mqtt(app: FastAPI, host):

    global mqtt_thread
    global mqtt_stop_token

    if mqtt_thread is not None:
        mqtt_stop_token = True
        mqtt_thread.join()
        
    mqtt_stop_token = False
    mqtt_thread = threading.Thread(None, mqtt_main, args=(host,))
    mqtt_thread.start()

def stop_mqtt():

    global mqtt_thread
    global mqtt_stop_token

    mqtt_stop_token = True

    if mqtt_thread is not None:
        mqtt_thread.join()

def on_message(client, userdata, msg: mqtt.MQTTMessage):

    global packet_received

    packet_received = True

    split_topic = msg.topic.split('/')

    if split_topic[1] == 'm':
        process_measurements(split_topic[0], split_topic[2], split_topic[3], msg.payload)
        return

    print(f'{msg.topic}: {msg.payload}')

# The callback for when the client receives a CONNACK response from the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to mqtt broker successfully!")
        client.subscribe('#') # Subscribe to all topics
        return
    print('connection error')
    client.username_pw_set('server', get_self_access_token())


def on_disconnect(client, properties, reason_code):
    print(f'Disconnected from mqtt broker, code: {reason_code}')


def setup_callbacks(client: mqtt.Client):

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
