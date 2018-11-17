#!/usr/bin/python3

from bluepy.btle import Scanner, DefaultDelegate
from bluepy import btle
import binascii
import time
import os
import sqlite3

dev = None

def lf_flowerpot():
    global dev
    scanner = Scanner()
    devices = scanner.scan(5.0)
    finded = False
    for dev in devices:
        if dev.addr == '24:0a:c4:00:61:86':
            try:
                dev = btle.Peripheral("24:0A:C4:00:61:86")
                time.sleep(2)
                return True
            except Exception as e:
                print(e)
                return False

    time.sleep(20)

def get_values(val):
    mp, si = val[0][1].decode('UTF-8').replace("(","").replace(")","").split(", ")
    hum = val[1][1].decode('UTF-8')
    red, blue = val[2][1].decode('UTF-8').replace("(","").replace(")","").split(", ")
    press = val[3][1].decode('UTF-8')
    voltage = val[4][1].decode('UTF-8')
    moist = val[5][1].decode('UTF-8')
    print(mp, si, hum, red, blue, press, voltage, moist)

time_s = 0
while True:
    os.system('sudo hciconfig hci0 leadv 0')
    time.sleep(time_s)
    if lf_flowerpot() is False:
        time_s = 10
        continue
    print('Connected.')
    
    val = []
    try:
        print('Services...')
        serv = dev.getServiceByUUID(uuidVal=btle.UUID(0x10e1))
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
        if (len(val) == 6):
            print('Response...')
            respChar.write(bytes(1), withResponse=False)
    except Exception as e:
        print(e)
        time_s = 0
        continue

    val = sorted(val, key=lambda tup: tup[0].binVal)
    get_values(val)
    if os.system('ping -q -I eth0 -w 1 -c 1 8.8.8.8 > /dev/null') == 0:
        print('mqtt')
    else:
        try:
            conn = sqlite3.connect('flower_pot_data.db')
            c = conn.cursor()
            sql = ''' INSERT INTO measurements(temperature_mp, temperature_si, humidity, light_r, light_b, pressure, battery, moisture, datetime, global) VALUES (?,?,?,?,?,?,?,?,?) '''
            # YYYY-MM-DD HH:MM:SS is datetime format fo sqlite
            c.execute(sql, val)
            con.close()
        except sqlite3.Error as e:
            print(e)

