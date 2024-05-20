#!/usr/bin/python

# monitor_state_switches.py
#

from subprocess import check_output
from homebridge import HomeBridgeController
from datetime import datetime, timedelta
import json
import time

sleep_time_sec = 10
idle_timeout = timedelta(minutes=5)
log_filename = 'logs/monitor_state_switches.log'
switch_name = 'sherwood_locker_switch'
html_filename = 'logs/index.html'
trusted_mac_addresses_filename = "trusted_mac_addresses.json"
homebridge_connection_filename = "homebridge_connection.json"

kitchen_state_change_time = None
was_unlocked = None

def time_delta_to_str(td):
  secs = td.total_seconds()
  mins = secs / 60
  hours = mins / 60
  days = hours / 24

  if days > 1:
    return f'{int(days)} days'
  elif hours > 1:
    return f'{int(hours)} hours'
  elif mins > 1:
    return f'{int(mins)} mins'
  else:
    return f'{int(secs)} secs'

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
def get_lock_state_from_message(msg_str):
  if 'unlocked' in msg_str:
    return "unlocked"
  elif "locked" in msg_str:
    return "locked"
  return ""

def log(message):

  date_str = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
  
  # write to debug log
  with open(log_filename, 'a') as f:
    f.write(f'{date_str} : {message}\n')
  
  if len(recent_messages) > 0 and get_lock_state_from_message(message) == get_lock_state_from_message(recent_messages[0][1]):
    recent_messages[0] = (date_str, message)
  else:
    recent_messages.insert(0, (date_str, message))

  if len(recent_messages) > 2000:
    recent_messages.pop()
  
  write_messages_to_html(recent_messages)


def write_messages_to_html(messages):
  with open(html_filename,'w') as f:
    f.write('''
<html>
  <meta content="width=device-width, initial-scale=1, minimum-scale=1, user-scalable=no" name="viewport">
<style>
p {margin:0}
h3 {margin:0px 5px 0px 0px}
.green {background-color:#BDE7BD}
.red {background-color:#FFB6B3}
div{padding:5px; margin: 5px 0px;}
</style>
<body>
''')

    for m in messages:
      date_str,message = m
      classname = ''
      if ' unlocked' in message:
        classname = 'green'
      elif ' locked' in message:
        classname = 'red'

      f.write(f'''
<div class={classname}>
<h3>{date_str}</h3>
<p>{message}</p>
</div>\n''')

    f.write('''
</body>
</html>
''')

def is_daytime():
    return 7 <= datetime.now().hour < 22

# Load trusted MAC addresses
trusted_devices = json.loads(open(trusted_mac_addresses_filename, 'r').read())

# Initialize dictionary of when trusted MAC addresses were last
# seen on the network.
last_seen_times = {mac_addr: datetime(2024,1,1,1,1,1) for mac_addr in trusted_devices.keys()}

log('Beginning monitoring')

first_run = True
while True:
  
  if not first_run:
    state_str = 'unlocked' if is_unlocked else 'locked'
    time_str = "Daytime" if is_daytime() else 'Nighttime'
    log(f"[{time_str}] Switch {state_str} for {time_delta_to_str(time_in_current_state)}. Trusted device seen {time_delta_to_str(time_since_trusted_device_seen)} ago.")

  # Load all connected MAC addresses
  cmd = "sudo arp-scan --plain --interface=eth0 --localnet | awk 'BEGIN {FS=\"\t\"}; {print $2}'"
  cmd_output = check_output(cmd, shell=True).decode()
  connected_mac_addresses = cmd_output.strip().split('\n')

  # Update last seen times
  for mac_addr in connected_mac_addresses:
    if mac_addr in trusted_devices:
      last_seen_times[mac_addr] = datetime.now()

  # Calculate when any trusted device was last seen
  time_since_trusted_device_seen = min(
    (datetime.now()-t) for t in last_seen_times.values())

  # Connect to homebridge instance.
  # (Must reconnect on each loop iteration to pick up state changes
  # to devices made outside of this script.)
  controller = connect_to_homebridge()
  is_unlocked = bool(controller.get_value(switch_name))  # In Homebridge, True means unlocked, false means locked

  ## Update switch
  if is_unlocked != was_unlocked:
    kitchen_state_change_time = datetime.now()

  time_in_current_state = (datetime.now()-kitchen_state_change_time)
  sees_trusted_device = time_since_trusted_device_seen < idle_timeout

  should_unlock = \
    (sees_trusted_device and is_daytime() or \
    (is_unlocked and time_in_current_state < idle_timeout))
  
  controller.set_value(switch_name, should_unlock)

  time.sleep(sleep_time_sec)

  was_unlocked = is_unlocked

  first_run = False
