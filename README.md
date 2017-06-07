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
* a PL2303-type USB2Serial Adapter

# Known Limitations

The current state of this program is 'proof-of-concept', therefore it lacks many import aspects:

* proper error handling
* configuration via arguments/config file
* clean code :-)
* you can not disable mqtt
* no virtualenv

# REST API Examples

Query the current power state:
```
curl http://example.host:3333/nad/c368/v1.0/Main/Power
{
  "command": "main.power", 
  "error": 0, 
  "value": "on"
}
```

Set the current power:
```
curl -X PUT http://example.host:3333/nad/c368/v1.0/Main/Power/on
{
  "command": "main.power", 
  "error": 0, 
  "value": "on"
}
```
