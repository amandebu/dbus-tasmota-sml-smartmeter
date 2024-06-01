#!/usr/bin/env python

"""

Created by amandebu 2024

Forked from https://github.com/RalfZim/venus.dbus-fronius-smartmeter by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020.
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
Reading information from the Fronius Smart Meter via http REST API and puts the info on dbus.
"""
try:
  import gobject  # Python 2.x
except:
  from gi.repository import GLib as gobject # Python 3.x
import platform
import logging
import sys
import os
import requests # for http GET
try:
  import thread   # for daemon = True  / Python 2.x
except:
  import _thread as thread   # for daemon = True  / Python 3.x

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusService

path_UpdateIndex = '/UpdateIndex'

class DbusDummyService:
  def __init__(self, servicename, deviceinstance, paths, productname='Tasmota SML Meter', connection='Tasmota SML Meter service'):
    self._dbusservice = VeDbusService(servicename)
    self._paths = paths

    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)

    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ProductId', 16) # value used in ac_sensor_bridge.cpp of dbus-cgwacs
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/FirmwareVersion', 0.1)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Connected', 1)

    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

    gobject.timeout_add(1000, self._update) # pause 200ms before the next request

  def _update(self):
    try:
#      meter_url = "http://localhost:8880/cm?cmnd=status%208"
      meter_url = "http://192.168.178.54/cm?cmnd=status%208"
      meter_page = "StatusSNS"
      meter_id = "LK13BE"

      meter_value = {
        "/Ac/Energy/Forward": "E_in",
        "/Ac/Energy/Reverse": "E_out",
        "/Ac/Power": "Power",
        "/Ac/L1/Power": "Power_L1_curr",
        "/Ac/L2/Power": "Power_L2_curr",
        "/Ac/L3/Power": "Power_L3_curr",
        "/Ac/L1/Frequency": "HZ",
        "/Ac/L2/Frequency": "HZ",
        "/Ac/L3/Frequency": "HZ",
        "/Ac/L1/Voltage": "Volt_L1_curr",
        "/Ac/L2/Voltage": "Volt_L2_curr",
        "/Ac/L3/Voltage": "Volt_L3_curr",
        "/Ac/L1/Current": "Amperage_L1_curr",
        "/Ac/L2/Current": "Amperage_L2_curr",
        "/Ac/L3/Current": "Amperage_L3_curr"
      }

      meter_r = requests.get(url=meter_url) # request data from device 
      meter_data = meter_r.json()[meter_page][meter_id] # convert JSON data and select data

      voltages=[]
      power=0
      for dbus_name,rest_name in meter_value.items():
        if "Voltage" in dbus_name:
          min_value=80
          max_value=270
        elif "Power" in dbus_name:
          min_value=-30000
          max_value=30000
        elif "Frequency" in dbus_name:
          min_value=20
          max_value=70
        elif "Current" in dbus_name:
          min_value=-1000
          max_value=1000
        elif "Energy" in dbus_name:
          min_value=0
          max_value=100000000
        new_value=meter_data[rest_name]
        if new_value>=min_value and new_value<=max_value:
          if "/Ac/L" in dbus_name and "/Voltage" in dbus_name:
            voltages.append(new_value)
          if "/Ac/Power"==dbus_name:
            power=new_value
          self._dbusservice[dbus_name] = new_value
      if len(voltages)>0:
        voltage=sum(voltages)/len(voltages)
        self._dbusservice["/Ac/Voltage"]=round(voltage,2)
        self._dbusservice["/Ac/Current"]=round(voltage/power,2)

      logging.info("House Consumption: {:.0f}".format(meter_consumption))
    except:
      logging.info("WARNING: Could not read from tasmota-sml-device")
      #self._dbusservice['/Ac/Power'] = 0  # TODO: any better idea to signal an issue?
    # increment UpdateIndex - to show that new data is available
    index = self._dbusservice[path_UpdateIndex] + 1  # increment index
    if index > 255:   # maximum value of the index
      index = 0       # overflow from 255 to 0
    self._dbusservice[path_UpdateIndex] = index
    return True

  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change

def main():

  def _kwh(p, v):
    return str("%.2f" % v) + "kWh"

  def _a(p, v):
    return str("%.1f" % v) + "A"

  def _w(p, v):
    return str("%i" % v) + "W"

  def _v(p, v):
    return str("%.2f" % v) + "V"

  def _hz(p, v):
    return str("%.4f" % v) + "Hz"

  def _n(p, v):
    return str("%i" % v)

  logging.basicConfig(level=logging.DEBUG) # use .INFO for less logging
  thread.daemon = True # allow the program to quit

  from dbus.mainloop.glib import DBusGMainLoop
  # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
  DBusGMainLoop(set_as_default=True)

  devinstance=31

  pvac_output = DbusDummyService(
    servicename=f'com.victronenergy.grid.tasmota_sml_{devinstance}',
    deviceinstance=devinstance,
#    customname='Tasmota_SML_Grid',
    paths={
      '/Ac/Power': {'initial': 0, "textformat": _w},
      '/Ac/Current': {'initial': 0, "textformat": _a},
      '/Ac/Voltage': {'initial': 0, "textformat": _v},

      '/Ac/Energy/Forward': {'initial': 0, "textformat": _kwh}, # energy bought from the grid
      '/Ac/Energy/Reverse': {'initial': 0, "textformat": _kwh}, # energy sold to the grid

      '/Ac/L1/Voltage': {'initial': 0, "textformat": _v},
      '/Ac/L2/Voltage': {'initial': 0, "textformat": _v},
      '/Ac/L3/Voltage': {'initial': 0, "textformat": _v},

      '/Ac/L1/Current': {'initial': 0, "textformat": _a},
      '/Ac/L2/Current': {'initial': 0, "textformat": _a},
      '/Ac/L3/Current': {'initial': 0, "textformat": _a},

      '/Ac/L1/Power': {'initial': 0, "textformat": _w},
      '/Ac/L2/Power': {'initial': 0, "textformat": _w},
      '/Ac/L3/Power': {'initial': 0, "textformat": _w},

      '/Ac/L1/Frequency': {'initial': 0, "textformat": _hz},
      '/Ac/L2/Frequency': {'initial': 0, "textformat": _hz},
      '/Ac/L3/Frequency': {'initial': 0, "textformat": _hz},

      path_UpdateIndex: {'initial': 0, "textformat": _n},
    })

  logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
  mainloop = gobject.MainLoop()
  mainloop.run()

if __name__ == "__main__":
  main()
