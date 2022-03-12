# hue-mqtt-bridge

Connect a Philips Hue bridge via MQTT. Get notified about state changes. Change the state of light and groupd viq MQTT commands. 

Features:
- Supposed to run as Linux service.
- Discover your Hue bridges.
- Create app token to access your Hue bridge.
- Switch and dims lights and groups. 
- No bridge polling. This hue-mqtt-bridge gets notified via events. 

Disclaimer:
- Sensors are not supported yet.
- Colors are not supported yet.
- Only Linux systems supported.

## Startup

### Prepare python environment

```bash
cd /opt
sudo mkdir hue-mqtt-bridge
sudo chown <user>:<user> hue-mqtt-bridge  # type in your user
git clone https://github.com/rosenloecher-it/hue-mqtt-bridge hue-mqtt-bridge

cd hue-mqtt-bridge
virtualenv -p /usr/bin/python3 venv

# activate venv
source ./venv/bin/activate

# check python version >= 3.8
python --version

# install required packages
pip install -r requirements.txt
```

### Run

```bash
# prepare a configuration. this is a partly iterative process. 
cp ./hue-mqtt-bridge.yaml.sample ./hue-mqtt-bridge.yaml
# edit your `hue-mqtt-bridge.yaml`. see also comments there.

# the embedded json schema may contain additional information
./hue-mqtt-bridge.sh --json-schema

# security concerns: make sure, no one can read the stored passwords
chmod 600 ./hue-mqtt-bridge.yaml

# see further command line options
./hue-mqtt-bridge.sh --help

# discover your Hue bridge 
./hue-mqtt-bridge.sh --discover

# create an app key to access your Hue bridge. you will have to press the Hue button.
./hue-mqtt-bridge.sh --create-app-key

# explore your lights, groups and sensors. 'explore' will also compare your configuration with the Hue items.
./hue-mqtt-bridge.sh --explore

# put all needed information with you configuration

./hue-mqtt-bridge.sh --print-logs --config-file ./hue-mqtt-bridge.yaml
# abort with ctrl+c

# testing - listing to configured topics
mosquitto_sub -h $SERVER -d -t test/hue/<your-thing>/#

# testing - switch your thing
mosquitto_pub -h $SERVER -d -t test/hue/<your-thing>/cmd -m on
mosquitto_pub -h $SERVER -d -t test/hue/<your-thing>/cmd -m off
mosquitto_pub -h $SERVER -d -t test/hue/<your-thing>/cmd -m toggle
# testing - dim your thing (%)
mosquitto_pub -h $SERVER -d -t test/hue/<your-thing>/cmd -m 50
```

## Register as systemd service
```bash
# prepare your own service script based on hue-mqtt-bridge.service.sample
cp ./hue-mqtt-bridge.service.sample ./hue-mqtt-bridge.service

# edit/adapt path's and user in hue-mqtt-bridge.service
vi ./hue-mqtt-bridge.service

# install service
sudo cp ./hue-mqtt-bridge.service /etc/systemd/system/
# alternativ: sudo cp ./hue-mqtt-bridge.service.sample /etc/systemd/system//hue-mqtt-bridge.service
# after changes
sudo systemctl daemon-reload

# start service
sudo systemctl start hue-mqtt-bridge

# check logs
journalctl -u hue-mqtt-bridge
journalctl -u hue-mqtt-bridge --no-pager --follow --since "5 minutes ago"

# enable autostart at boot time
sudo systemctl enable hue-mqtt-bridge.service
```

## Additional infos

### MQTT broker related infos

If no messages get logged check your broker.
```bash
sudo apt-get install mosquitto-clients

# prepare credentials
SERVER="<your server>"

# start listener
mosquitto_sub -h $SERVER -d -t smarthome/#

# send single message
mosquitto_pub -h $SERVER -d -t smarthome/test -m "test_$(date)"

# just as info: clear retained messages
mosquitto_pub -h $SERVER -d -t smarthome/test -n -r -d
```

## Maintainer & License

MIT © [Raul Rosenlöcher](https://github.com/rosenloecher-it)

The code is available at [GitHub][home].

[home]: https://github.com/rosenloecher-it/hue-mqtt-bridge
