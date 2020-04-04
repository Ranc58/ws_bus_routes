# Bus routes on the map 
Map with Moscow bus routes. \
Project uses web sockets based on [Trio](https://github.com/python-trio/trio) async implementation and RabbitMQ \
![](pics/buses.gif)
# How to install
Python version required: 3.7+
1. Recomended use venv or virtualenv for better isolation.\
   Venv setup example: \
   `python3 -m venv myenv`\
   `source myenv/bin/activate`
2. Install requirements: \
   `pip3 install -r requirements.txt` (alternatively try add `sudo` before command)

3. You need RabbiMQ. Docker example: `docker run -p 127.0.0.1:5672:5672/tcp  -e RABBITMQ_DEFAULT_USER="rabbitmq" -e RABBITMQ_DEFAULT_PASS="rabbitmq" rabbitmq:latest
`
# How to launch
1) Run `server.py`. \
This ws server (with default settings) will listen incoming messages `127.0.0.1:8080` and send messages to `127.0.0.1:8080`\
CLI args for `server.py`:
```
Options:
  -bp, --browser_port INTEGER  Browser port  [default: 8000]
  -l, --log                    Enable logging  [default: False]
  -ru, --rabbit_user TEXT      Login for RabbitMQ  [default: rabbitmq]
  -rpass, --rabbit_pass TEXT   Password for RabbitMQ  [default: rabbitmq]
  -rh, --rabbit_host TEXT      RabbitMQ host  [default: 127.0.0.1]
  -rp, --rabbit_port INTEGER   RabbitMQ port  [default: 5672]
  --help                       Show this message and exit.
```
2) For simulate the movement of buses you have to run the script `fake_bus.py`. \
CLI args for `fake_bus.py`:
```
Options:
  -r, --routes_number INTEGER    Number of routes.  [default: 10]
  -b, --buses_per_route INTEGER  Number of buses per one route  [default: 5]
  -e, --emulator_id TEXT         ID for buses
  -rt, --refresh_timeout FLOAT   Timeout for refresh (in secs)  [default:
                                 0.03]
  -l, --log                      Enable logging  [default: False]
  -ru, --rabbit_user TEXT        Login for RabbitMQ  [default: rabbitmq]
  -rpass, --rabbit_pass TEXT     Password for RabbitMQ  [default: rabbitmq]
  -rh, --rabbit_host TEXT        RabbitMQ host  [default: 127.0.0.1]
  -rp, --rabbit_port INTEGER     RabbitMQ port  [default: 5672]
  --help                         Show this message and exit.
```
3) Open on your browser `frontend\index.html`.



And you can use `harmful_imitator.py` for test incorrect incoming values from bus/browser to `server.py`. \
CLI args for `harmful_imitator.py`:
```
Options:
  -l, --log                  Enable logging  [default: False]
  -h, --host TEXT            Destination host  [default: 127.0.0.1]
  -p, --port TEXT            Destination port  [default: 8000]
  -it, --imitator_type TEXT  Type of imitator(client/bus)  [default: client]
  --help                     Show this message and exit.

```


# Project Goals
The code is written for educational purposes. Training course for web-developers - [DVMN.org](https://dvmn.org)
