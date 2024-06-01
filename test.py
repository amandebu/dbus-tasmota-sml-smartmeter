
import json
import requests

def test():
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
        "/Ac/L1/Voltage": "Volt_L1_curr",
        "/Ac/L2/Voltage": "Volt_L2_curr",
        "/Ac/L3/Voltage": "Volt_L3_curr",
        "/Ac/L1/Current": "Amperage_L1_curr",
        "/Ac/L2/Current": "Amperage_L2_curr",
        "/Ac/L3/Current": "Amperage_L3_curr"
      }

      meter_r = requests.get(url=meter_url) # request data from device
      meter_data = meter_r.json()[meter_page][meter_id] # convert JSON data and select data

      for dbus_name,rest_name in meter_value.items():
        print(dbus_name,":",meter_data[rest_name])

test()
