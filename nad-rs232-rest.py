#!/usr/bin/python

#    This file is part of nad-rs232-rest.
#
#    nad-rs232-rest is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    any later version.
#
#    nad-rs232-rest is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.


import sys
import logging
import serial
import thread
import Queue
import re
import paho.mqtt.client as mqtt
from flask import Flask
from flask import jsonify

config = {
	"serialPort": "/dev/ttyUSB0",
	"serialSpeed": 115200,
	"mqttBroker": "192.168.128.2",
	"mqttPort": 1883,
	"restBindIp": "0.0.0.0",
	"restBindPort": "3333",
	"deviceType": "C368",
	"deviceId": "LivingRoom"
}

validMainCommands = [
	"autosense",
	"autostandby",
	"balance",
	"bass",
	"brightness",
	"btworkmode",
	"controlstandby",
	"display",
	"filters",
	"listeningmode",
	"model",
	"mute",
	"polarity",
	"power",
	"preoutsub",
	"source",
	"sources",
	"speakera",
	"speakerb",
	"tonedefeat",
	"treble",
	"version",
	"volume",
	"volumedisplaymode",
]

requestQueue = Queue.Queue()
answerQueue = Queue.Queue()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

##########
#  MQTT  #
##########

def mqtt_on_connect(client, userdata, flags, rc):
	global config
	logging.debug("[MQTT] Connected to broker (result code " + str(rc) + ")")
	client.subscribe("NAD/" + config["deviceType"] + "/" + config["deviceId"] + "/Commands")

def mqtt_on_message(client, userdata, msg):
	global requestQueue
	logging.debug("[MQTT] Message on '" + str(msg.topic) + "': " + str(msg.payload))
	requestQueue.put(msg.payload)
	

##########
# SERIAL #
##########
def handleSerial(config, mqttClient, requestQueue, answerQueue):
	try:
		ser = serial.Serial(port=config["serialPort"], baudrate=config["serialSpeed"], xonxoff=False, rtscts=False, dsrdtr=False, timeout=0.5)
	except:
		logging.critical( "[SERIAL] Could not open " + config["serialPort"])
		sys.exit(1)

	logging.info("[SERIAL] Connected to " + config["serialPort"] + " with " + str(config["serialSpeed"]) + " Baud")
	
	buffer = ""
	while 1 :
		cmd = None
		try:
			cmd = requestQueue.get_nowait()
		except:
			pass

		if(cmd):
			logging.debug("[SERIAL] Sending request '" + cmd + "'")
			ser.write('\n' + cmd + '\n')
			cmd = None

		readByte = ser.read(1)
		if(readByte):
			if(ord(readByte) == 13):
				if(buffer):
					logging.debug("[SERIAL] Found a message on the wire: " + buffer)
					answerQueue.put(buffer)
					mqttClient.publish("NAD/" + config["deviceType"] + "/" + config["deviceId"] + "/Messages", buffer)
				buffer = ""
			else:
				buffer = buffer + readByte

############
# REST-API #
############
app = Flask(__name__)

def stripCommand(cmd):
	m = re.search("([a-zA-Z0-9]+\.[a-zA-Z0-9\.]+)[?=].*", cmd)
	if m:
		return m.group(1)
	else:
		return ""
	
def stripValue(cmd):
	m = re.search("[a-zA-Z0-9]+\.[a-zA-Z0-9\.]+[=](.*)", cmd)
	if m:
		return m.group(1)
	else:
		return ""

@app.route('/nad/c368/v1.0/Main/<command>', methods=['GET'])
def getMainCommand(command):
	command = command.lower()
	if command not in validMainCommands:
		answerStruct = { "error": 2, "command": "main." + command, "value": None, "errorMsg": "Command invalid" }
		return jsonify(answerStruct)
	# this is rather ugly, but...
	# since we are expecting an answer to our query, let's make sure there
	# is nothing else stuck in the answerQueue
	# TODO: optimize handleSerial() to only put answers to outstanding requests into answerQueue
	with answerQueue.mutex:
		answerQueue.queue.clear()
	requestQueue.put("main." + command + "?")
	try:
		answer = answerQueue.get(True,4).lower()
		if stripCommand(answer) == "main." + command:
			answerStruct = { "error": 0, "command": "main." + command, "value": stripValue(answer) }
			return jsonify(answerStruct)
	except:
		pass
	answerStruct = { "error": 1, "command": "main." + command, "value": None, "errorMsg": "Did not receive a valid answer withing 4 seconds" }
	return jsonify(answerStruct)

@app.route('/nad/c368/v1.0/Main/<command>/<value>', methods=['PUT'])
def putMainCommand(command, value):
	command = command.lower()
	if command not in validMainCommands:
		answerStruct = { "error": 2, "command": "main." + command, "value": value, "errorMsg": "Command invalid" }
		return jsonify(answerStruct)
	# this is rather ugly, but...
	# since we are expecting an answer to our query, let's make sure there
	# is nothing else stuck in the answerQueue
	# TODO: optimize handleSerial() to only put answers to outstanding requests into answerQueue
	with answerQueue.mutex:
		answerQueue.queue.clear()
	requestQueue.put("main." + command + "=" + value)
	try:
		answer = answerQueue.get(True,4).lower()
		if stripCommand(answer) == "main." + command:
			answerStruct = { "error": 0, "command": "main." + command, "value": stripValue(answer) }
			return jsonify(answerStruct)
	except:
		pass
	answerStruct = { "error": 1, "command": "main." + command, "value": None, "errorMsg": "Did not receive a valid answer withing 4 seconds" }
	return jsonify(answerStruct)


###############
# MAIN Thread #
###############
def main(args):
	logging.info("Starting mqtt thread")
	try:
		client = mqtt.Client()
		client.on_connect = mqtt_on_connect
		client.on_message = mqtt_on_message
		client.connect(config["mqttBroker"], config["mqttPort"], 60)
		client.loop_start()
	except:
		logging.critical("Could not setup mqtt session. Bye")
		sys.exit(1)

	logging.info("Starting serial port thread")
	try:
		thread.start_new_thread(handleSerial, (config, client, requestQueue, answerQueue))
	except Exception as e:
		logging.critical("Error spawning serial port thread: " + str(e))
		sys.exit(1)

	app.run(host=config["restBindIp"], port=config["restBindPort"])

if __name__ == '__main__':
	main(sys.argv[1:])	

