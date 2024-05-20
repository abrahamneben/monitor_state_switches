#!/bin/bash

nohup python -m http.server --directory /home/aneben/monitor_state_switches/logs &

nohup ./monitor_state_switches.py &

