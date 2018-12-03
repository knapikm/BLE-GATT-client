#!/usr/bin/python3

from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID
import time
import os
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

dev = None

def lf_flowerpot():
    global dev
    scanner = Scanner()
    devices = scanner.scan(5.0)
    finded = False
    for dev in devices:
        if dev.addr == '24:0a:c4:00:61:86':
            try:
                dev = Peripheral("24:0A:C4:00:61:86")
                time.sleep(1)
                return True
            except Exception as e:
                print(e)
                return False

    return None

def get_values(val, sql=False):
    id = val[0][1].decode('UTF-8')
    mp, si = val[1][1].decode('UTF-8').replace("(","").replace(")","").split(", ")
    hum = val[2][1].decode('UTF-8')
    red, blue = val[3][1].decode('UTF-8').replace("(","").replace(")","").split(", ")
    press = val[4][1].decode('UTF-8')
    voltage = val[5][1].decode('UTF-8')
    moist = val[6][1].decode('UTF-8')
    
    if sql:
        return (id, si, hum, press, voltage, moist, 0)
    return (id, si, hum, press, voltage, moist)

time_s = 1
while True:
    os.system('sudo hciconfig hci0 leadv 0')
    time.sleep(time_s)
    if lf_flowerpot() is False:
        time_s = 2
        continue
    if lf_flowerpot() is None:
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
            if ch.uuid.binVal[3] == 0xd7:
                respChar = ch
                continue
            val.append((ch.uuid, ch.read()))
        if (len(val)) == 8:
            print('Response...')
            respChar.write(bytes(1), withResponse=False)
    except Exception as e:
        print(e)
        time_s = 2
        continue

    val = sorted(val, key=lambda tup: tup[0].binVal)
    if os.system('ping -q -I eth0 -w 1 -c 1 8.8.8.8 > /dev/null') == 0:
        get_values(val)
    else:
        try:
            conn = sqlite3.connect('flower_pot_data.db', isolation_level=None)
            c = conn.cursor()
            sql = ''' INSERT INTO measurements(id, temperature, humidity, pressure, battery, moisture, global) VALUES (?,?,?,?,?,?,?) '''
            c.execute(sql, get_values(val, sql=True))
            conn.close()
            print('SQL done, last row id is:', c.lastrowid)
        except sqlite3.Error as e:
            print(e)

