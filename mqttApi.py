import paho.mqtt.client as mqttClient
import time

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
        return True
    except Exception as e:
        print("[MQTT_ERROR] There was an error, details: \n{}".format(e))
        return False
