#!/usr/bin/python3

import bluepy.btle as ble
import sys
import os
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqttClient
import time
import json
import mqttApi

dev = None

def lf_flowerpot():
    global dev
    scanner = ble.Scanner()
    devices = scanner.scan(4.0)
    for dev in devices:
        if dev.addr == '24:0a:c4:00:61:86':
            try:
                dev = ble.Peripheral("24:0A:C4:00:61:86")
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


mqtt_client = mqttClient.Client()
if not mqttApi.connected:  # Connects to the broker
    mqttApi.connect(mqtt_client, mqttApi.MQTT_USERNAME, mqttApi.MQTT_PASSWORD,
            mqttApi.BROKER_ENDPOINT, mqttApi.PORT)

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
        serv = dev.getServiceByUUID(uuidVal=ble.UUID(0x10e1))
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
        try:
            mqttApi.publish(mqtt_client, mqttApi.topic, payload=get_values(val))
            time.sleep(2)

            conn = sqlite3.connect('flower_pot_data.db', isolation_level=None)
            c = conn.cursor()
            for row in c.execute('''SELECT * FROM measurements WHERE global = 0 ORDER BY id'''):
                print(row)
                data = json.dumps( { "id": row[0], "temperature": row[1], "battery": row[2], "moisture": row[3], "network": 2 } )
                if mqttApi.publish(mqtt_client, mqttApi.topic, payload=data):
                    with conn:
                        conn.execute('''UPDATE measurements SET global = 1 WHERE id = ?''', (str(row[0]),))
                time.sleep(2)
            conn.close()
        except Exception as e:
            print(e)

    else:
        try:
            conn = sqlite3.connect('flower_pot_data.db', isolation_level=None)
            with conn:
                conn.execute('''INSERT INTO measurements(id, temperature, battery, moisture, global) VALUES (?,?,?,?,?)''', get_values(val, sql=True))
            conn.close()
            print('SQL done, last row id:', c.lastrowid)
        except sqlite3.IntegrityError as e:
            print(e)
