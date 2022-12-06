#!/bin/bash

nohup python -m http.server &
nohup ./monitor_state_switches.py &
