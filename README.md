# Bus routes on the map 
Map with Moscow bus routes. \
Project uses web sockets based on [Trio](https://github.com/python-trio/trio) async implementation. \
![](pics/buses.gif)
# How to install
Python version required: 3.7+
1. Recomended use venv or virtualenv for better isolation.\
   Venv setup example: \
   `python3 -m venv myenv`\
   `source myenv/bin/activate`
2. Install requirements: \
   `pip3 install -r requirements.txt` (alternatively try add `sudo` before command)

# How to launch
1) open on your browser `frontend\index.html`.
2) Second you need run `server.py`. \
This ws server will listen incoming messages `127.0.0.1:8080` and send messages to `127.0.0.1:8080`
3) For simulate the movement of buses you have to run the script `fake_bus.py`. You can use some CLI args:
```
Options:
  -r, --routes_number INTEGER    Number of routes.  [default: 10]
  -b, --buses_per_route INTEGER  Number of buses per one route  [default: 5]
  -s, --sockets_count INTEGER    Count of websockets.  [default: 5]
  -e, --emulator_id TEXT         ID for buses
  -rt, --refresh_timeout FLOAT   Timeout for refresh (in secs)  [default: 0.1]
  -l, --log                      Enable logging  [default: False]
  -h, --host TEXT                Destination host  [default: 127.0.0.1]
  -p, --port TEXT                Destination port  [default: 8080]
  --help                         Show this message and exit.
```



# Project Goals
The code is written for educational purposes. Training course for web-developers - [DVMN.org](https://dvmn.org)
