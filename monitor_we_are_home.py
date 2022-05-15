#!/usr/bin/python

# monitor_we_are_home.py 
# 

from subprocess import check_output
from homebridge import HomeBridgeController
from datetime import datetime
import json
import time

verbose_logging = True
sleep_time_sec = 10
idle_timeout_mins = 2
log_filename = 'we_are_home.log'
trusted_mac_addresses_filename = "trusted_mac_addresses.json"
homebridge_config_filename = "homebridge_config.json"

prev_we_are_home = None
we_are_home_set_time = datetime.now()

homebridge_config = json.loads(open(homebridge_config_filename, 'r').read())
def connect_to_homebridge():
  """Return handle to homebridge instance."""
  return HomeBridgeController(
    host=homebridge_config["host"],
    port=homebridge_config["port"],
    auth=homebridge_config["pin"])

def log(message):
  with open(log_filename, 'a') as f:
    date_str = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
    f.write(f'{date_str} : {message}')

def is_daytime():
  return 7 <= datetime.now().hour < 21

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

  if verbose_logging:
    log(json.dumps(last_seen_times, default=str) + '\n')

  # Calculate when any trusted device was last seen
  mins_since_trusted_device_seen = min(
    (datetime.now()-t).total_seconds() / 60.
     for t in last_seen_times.values())

  # Connect to homebridge instance.
  # (Must reconnect on each loop iteration to pick up state changes
  # to devices made outside of this script.)
  controller = connect_to_homebridge()
  we_are_home = bool(controller.get_value('we_are_home'))

  # Calculate hov long we_are_home has been in its preset state.
  if we_are_home != prev_we_are_home:
    we_are_home_set_time = datetime.now()
    prev_we_are_home = we_are_home
  mins_set = (datetime.now() - we_are_home_set_time).total_seconds() / 60.

  # During the day, set we_are_home to True as long as a trusted device is on the network. If it
  # disconnects, then set we_are_home to False after a timeout.
  if is_daytime():
    if we_are_home:  # currently unlocked
      if mins_since_trusted_device_seen > idle_timeout_mins:

        log(f'[Daytime] Locking b/c trusted device not seen for {mins_since_trusted_device_seen:.2f} min, exceeds {idle_timeout_mins} min timeout\n')
        controller.set_value('we_are_home', False)

      elif verbose_logging:
        log(f'[Daytime] No action. Currently unlocked. Last trusted device seen {mins_since_trusted_device_seen:.2f} min ago, within {idle_timeout_mins} min timeout.\n')
    elif not we_are_home:  # currently locked
      if mins_since_trusted_device_seen < idle_timeout_mins:

        log(f'[Daytime] Unlocking b/c trusted device seen {mins_since_trusted_device_seen:.2f} min ago, within {idle_timeout_mins} min timeout\n')
        controller.set_value('we_are_home', True)
    
      elif verbose_logging:
        log(f'[Daytime] No action. Currently locked. Last trusted device seen {mins_since_trusted_device_seen:.2f} min ago, exceeds {idle_timeout_mins} min timeout.\n')

  # At night, set we_are_home to False. If it is manually changed outside this script, then 
  # re-set it to false after a timeout.
  elif not is_daytime():  # Nighttime
    if we_are_home:  # currently unlocked
      if mins_set > idle_timeout_mins:
        log(f'[Nighttime] Locking b/c we_are_home has been True for {mins_set:.2f} min, exceeds {idle_timeout_mins} min timeout\n')
        controller.set_value('we_are_home', False)
      elif verbose_logging:
        log(f'[Nighttime] No action. Currently unlocked for {mins_set:.2f} min, within {idle_timeout_mins} min timeout\n')
    elif verbose_logging:
      log(f'[Nighttime] No action. Currently locked.\n')

  time.sleep(sleep_time_sec)
