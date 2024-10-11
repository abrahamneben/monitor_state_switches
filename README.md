# monitor_state_switches
## tl;dr
Lock or unlock your bluetooth smart lock based on time of day and whether your phone is connected to your home network.

## Background
We installed a smart lock on our back door, but ran into issues trying to automate locking/unlocking using pure HomeKit. We wanted it to be unlocked during the day while we were home, but to remain locked at night. We tried setting up a location-based automation in HomeKit, but this requires hitting "Allow" in a confirmation dialog on the iPhone every time it runs. 

This project is a sort of convoluted solution to getting around a confirmation dialog box, but it actually works quite well, and offers more flexibility than HomeKit/Automations can offer.

## Hardware prerequisites
* Bluetooth smart lock (eg, Schlage Sense)
* Raspberry Pi or any other home server
* HomePod, iPad, or Apple TV in Bluetooth range of the lock
* iPhone

## Setup
### Smart lock setup
Because we will be controlling the smart lock with a script, we must disable any auto-locking features on the smart lock.

If using a Schlage smart lock, open the Schlage app, tap the gear icon on your lock, then turn off Auto Lock Delay.

### Raspberry Pi setup
[Install Raspberry Pi OS](https://www.raspberrypi.com/software/), then SSH to it and [install Homebridge](https://github.com/homebridge/homebridge/wiki/Install-Homebridge-on-Raspbian). 

Open the Homebridge browser interface from your Raspberry Pi (you can also open it from any other computer on the network by navigating to `http://<ip_address_of_raspberry_pi>:8581`. Click Plugins, then search for Homebridge Dummy, and install that plugin. Name it `we_are_home` and click the Stateful checkbox.

## iPhone setup

Open the Home app on your iPhone, and scan the QR code for your Homebridge server. This will add the `we_are_home` dummy switch to Homekit. 

In the Home app, tap Automation, and add the below 4 automations.

 1. When your lock locks, set `we_are_home` to Off.
 2. When your lock unlocks, set `we_are_home` to One.
 3. When `we_are_home` turns On, set lock to unlocked.
 4. When `we_are_home` turns Off, set lock to locked.

You can set up each of these by tapping `+` in the Automation tab, then tap `An Accessory is Controlled`, then tap the device whose change you want to trigger on. Then tap Next, and tap the type of state change (eg, Turns On, Turns Off, Locks, or Unlocks). Then tap Next, and tap the device whose state you want to change, then set its state to whan you want it to change to. Then tap Done.

Strangely, Homekit does not require user confirmation when triggering lock/unlock actions based on other device state changes, only when the automation is triggered by a geo-fence.

## Script setup

SSH to the raspberry pi and clone this repo.

```
git clone git@github.com:abrahamneben/we_are_home.git
```

Create a `homebridge_connection.json` file from the provided template `homebridge_config_TEMPLATE.json`. `host` is the IP address os the raspberry pi, `port` and `pin` are given in the Config tab of the Homebridge browser interface.

Create a `trusted_mac_addresses.json` file from the provided template `trusted_mac_addresses_TEMPLATE.json`, containing the Wi-Fi MAC addresses of your trusted devices. I used my and my partner's iphones. These days, iOS creates a unique, random MAC address for every Wi-Fi network. This is found by tapping Wi-Fi in Settings, then tapping the (i) next to the current network.

Then set the script to run at startup with cron. Run `crontab -e` and add these lines

```
@reboot nohup python -m http.server --directory /home/aneben/monitor_state_switches/logs &
@reboot nohup /home/aneben/monitor_state_switches/monitor_state_switches.py >/home/aneben/monitor_state_switches/logs/log.txt 2>&1 &
```


