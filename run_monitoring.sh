#!/bin/bash

# NOTE: this file isn't used anymore, i now run these commands
# on startup using cron

python -m http.server --directory /home/aneben/monitor_state_switches/logs

/home/aneben/monitor_state_switches/monitor_state_switches.py >/home/aneben/monitor_state_switches/logs/log.txt 2>&1



