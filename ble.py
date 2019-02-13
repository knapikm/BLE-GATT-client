#!/usr/bin/python3

from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID
import sys
import os
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqttClient
import time
import json

dev = None

def lf_flowerpot():
    global dev
    scanner = Scanner()
    devices = scanner.scan(5.0)
    for dev in devices:
        if dev.addr == '24:0a:c4:00:61:86':
            try:
                dev = Peripheral("24:0A:C4:00:61:86")
                return True
            except Exception as e:
                print(e)
                return False

    return None

def get_values(val, sql=False):
    #resp = val[0][1].decode('UTF-8')
    id, temp = val[0][1].decode('UTF-8').split(", ")
    voltage, moist = val[1][1].decode('UTF-8').split(", ")
    print(id, temp, voltage, moist)
    if sql:
        return (id, temp, voltage, moist, 0)
    return json.dumps( { "id": id, "temperature": temp, "battery": voltage, "moisture": moist, "network": 2 } )



connected = False  # Stores the connection status
BROKER_ENDPOINT = "things.ubidots.com"
PORT = 1883
MQTT_USERNAME = "A1E-rHXnsEnsjpZKKSlf8khOxgZwnXKkE3"  # Put here your TOKEN
MQTT_PASSWORD = ""
TOPIC = "/v1.6/devices/"
DEVICE_LABEL = "sipy"
topic = "{}{}".format(TOPIC, DEVICE_LABEL)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT_INFO] Connected to broker")
        global connected  # Use global variable
        connected = True  # Signal connection

    else:
        print("[MQTT_INFO] Error, connection failed")


def on_publish(client, userdata, result):
    print("[MQTT_INFO] Published!")


def connect(mqtt_client, mqtt_username, mqtt_password, broker_endpoint, port):
    global connected

    if not connected:
        mqtt_client.username_pw_set(mqtt_username, password=mqtt_password)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_publish = on_publish
        mqtt_client.connect(broker_endpoint, port=port)
        mqtt_client.loop_start()

        attempts = 0

        while not connected and attempts < 5:  # Waits for connection
            print("[MQTT_INFO] Attempting to connect...")
            time.sleep(2)
            attempts += 1

    if not connected:
        print("[MQTT_ERROR] Could not connect to broker")
        return False

    return True


def publish(mqtt_client, topic, payload):
    print("[MQTT_INFO] Attempting to publish payload:")
    print(payload)
    try:
        mqtt_client.publish(topic, payload, qos=1)
    except Exception as e:
        print("[MQTT_ERROR] There was an error, details: \n{}".format(e))


mqtt_client = mqttClient.Client()
if not connected:  # Connects to the broker
    connect(mqtt_client, MQTT_USERNAME, MQTT_PASSWORD,
            BROKER_ENDPOINT, PORT)

time_s = 1
while True:
    os.system('sudo hciconfig hci0 leadv 0')
    time.sleep(time_s)
    lf = lf_flowerpot()
    if lf is False:
        time_s = 2
        continue
    if lf is None:
        time_s = 10
        continue
    print('Connected.')
    
    val = []
    try:
        print('Services...')
        serv = dev.getServiceByUUID(uuidVal=UUID(0x10e1))
        print('Characteristics...')
        char = serv.getCharacteristics()
        list_set = set(char) 
        char = (list(list_set)) # convert the set to the list
        print('Read...')
        val = []
        respChar = None
        for ch in char:
            if ch.uuid.binVal[3] == 0xd0:
                respChar = ch
                continue
            val.append((ch.uuid, ch.read()))
        if (len(val)) == 2:
            print('Response...')
            respChar.write(bytes(1), withResponse=False)
    except Exception as e:
        print(e)
        time_s = 2
        continue

    val = sorted(val, key=lambda tup: tup[0].binVal)
    if os.system('ping -q -I eth0 -w 1 -c 1 8.8.8.8 > /dev/null') == 0:
        publish(mqtt_client, topic, payload=get_values(val))
        time.sleep(2)
    else:
        try:
            conn = sqlite3.connect('flower_pot_data.db', isolation_level=None)
            c = conn.cursor()
            sql = ''' INSERT INTO measurements(id, temperature, battery, moisture, global) VALUES (?,?,?,?,?) '''
            c.execute(sql, get_values(val, sql=True))
            conn.close()
            print('SQL done, last row id is:', c.lastrowid)
        except sqlite3.Error as e:
            print(e)

