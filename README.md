# NAD-RS232-REST

This is a small python script which does the following:

* connect via RS232 to a NAD Electronics Amplifier (tested with a C-368 model)
* connect to a MQTT broker and publish all messages from the device
* subscribe to a given topic and forward all messages as commands to the device
* implement a simple REST-API to query/configure the C-368 device

# Dependencies

This has been tested on the following setup:
* Raspberry Pi 3, running Debian Jessie
* Python 2.7 and python-pip from official packages
* the following installed via pip: paho-mqtt, pyserial, flask

# Known Limitations

The current state of this program is 'proof-of-concept', therefore it lacks many import aspects:

* proper error handling
* configuration via arguments/config file
* clean code :-)
* you can not disable mqtt
* no virtualenv

