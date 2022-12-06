#!/usr/bin/python

# monitor_state_switches.py 
# 

from subprocess import check_output
from homebridge import HomeBridgeController
from datetime import datetime
import json
import time

verbose_logging = True
sleep_time_sec = 15
idle_timeout_mins = 8
log_filename = 'monitor_state_switches.log'
html_filename = 'index.html'
trusted_mac_addresses_filename = "trusted_mac_addresses.json"
homebridge_connection_filename = "homebridge_connection.json"

prev_kitchen_lock = None
kitchen_unlock_time = None

homebridge_connection = json.loads(open(homebridge_connection_filename, 'r').read())
def connect_to_homebridge():
  """Return handle to homebridge instance."""
  try:
    return HomeBridgeController(
      host=homebridge_connection["host"],
      port=homebridge_connection["port"],
      auth=homebridge_connection["pin"])
  except Exception as e:
    log(f'Failed to connect to homebridge with error \n{e}')
    time.sleep(sleep_time_sec)
    return connect_to_homebridge()

recent_messages = []
def log(message):

  date_str = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")

  if len(recent_messages) > 10:
    recent_messages.pop()
  recent_messages.insert(0, (date_str, message))
  write_messages_to_html(recent_messages)

  with open(log_filename, 'a') as f:
    f.write(f'{date_str} : {message}\n')

def write_messages_to_html(messages):
  with open(html_filename,'w') as f:
    f.write('''
<html>
  <meta content="width=device-width, initial-scale=1, minimum-scale=1, user-scalable=no" name="viewport">
<style>
.green {background-color:#BDE7BD}
.red {background-color:#FFB6B3}
</style>
<body>
''')

    for m in messages:
      date_str,message = m
      classname = 'green' if 'True' in message else 'red'
      f.write(f'<div class={classname}>h3>{date_str}</h3><p>{message}</p></div>\n')

    f.write('''
</body>
</html>
''')

def is_daytime():
  return 7 <= datetime.now().hour < 21

def is_nighttime():
  return not is_daytime()

# Load trusted MAC addresses
trusted_devices = json.loads(open(trusted_mac_addresses_filename, 'r').read())

# Initialize dictionary of when trusted MAC addresses were last
# seen on the network.
last_seen_times = {mac_addr: datetime(1970,1,1,1,1,1) for mac_addr in trusted_devices.keys()}

log('Beginning monitoring')

while True:

  # Load all connected MAC addresses
  cmd = "sudo arp-scan --plain --interface=eth0 --localnet | awk 'BEGIN {FS=\"\t\"}; {print $2}'"
  cmd_output = check_output(cmd, shell=True).decode()
  connected_mac_addresses = cmd_output.strip().split('\n')

  # Update last seen times
  for mac_addr in connected_mac_addresses:
    if mac_addr in trusted_devices:
      last_seen_times[mac_addr] = datetime.now()

  # Calculate when any trusted device was last seen
  mins_since_trusted_device_seen = min(
    (datetime.now()-t).total_seconds() / 60.
     for t in last_seen_times.values())

  # Connect to homebridge instance.
  # (Must reconnect on each loop iteration to pick up state changes
  # to devices made outside of this script.)
  controller = connect_to_homebridge()
  we_are_home = bool(controller.get_value('we_are_home'))
  kitchen_lock = bool(controller.get_value('kitchen_lock'))

  ## Update we_are_home
  log(f'[we_are_home] Setting to {we_are_home}')
  controller.set_value('we_are_home', mins_since_trusted_device_seen < idle_timeout_mins)

  ## Update kitchen_lock

  # Calculate how long kitchen lock has been set
  if kitchen_lock and kitchen_unlock_time is None:
    kitchen_unlock_time = datetime.now()
  elif not kitchen_lock:
    kitchen_unlock_time = None

  mins_unlocked = (datetime.now()-kitchen_unlock_time).total_seconds()/60 if kitchen_unlock_time is not None else None

  # During the day, set kitchen_lock to True as long as a trusted device is on the network. If it
  # disconnects, then set kitchen_lock to False after a timeout.
  if is_daytime():
    log(f'[kitchen_lock] Daytime. Setting to {mins_since_trusted_device_seen < idle_timeout_mins}, trusted device last seen for {mins_since_trusted_device_seen:.2f} min ago')
    controller.set_value('kitchen_lock', mins_since_trusted_device_seen < idle_timeout_mins)

  # At night, set we_are_home to False. If it is manually changed outside this script, then 
  # re-set it to false after a timeout.
  elif is_nighttime():
    should_unlock = mins_unlocked < idle_timeout_mins if kitchen_lock else False
    mins_unlocked_str = f'and has been unlocked for {mins_unlocked:.2f} mins' if mins_unlocked is not None else ''
    log(f'[kitchen_lock] Nighttime. Setting to {should_unlock} because currently {kitchen_lock} {mins_unlocked_str}.')
    controller.set_value('kitchen_lock', should_unlock)

  time.sleep(sleep_time_sec)
  


