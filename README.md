[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Elecrow GrowCube integration for Home Assistant
Home Assistant integration for the [Elecrow GrowCube](https://www.elecrow.com/growcube-gardening-plants-smart-watering-kit-device.html), a smart plant watering device.

> Please note that a Growcube device can only be connected to one client at a time. That means you 
> will not be able to connect using the phone app while Home Assistant is running the integration.

## Device

![device1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/device1.png)

## Sensors 

The integration adds sensors for temperature, humidity and four sensors for moisture. It adds four controls for watering, 
this activates the pump for 5 seconds for the given channel.

![sensors1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/sensors1.png)

## Diagnostics

The diagnostics sensors includes things such as device lock, sensor disconnect warnings and pump blocked warnings.

![diagnostics1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/diagnostics1.png)

## Controls

There are controls to let you manually water a plant. 

![controls1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/controls1.png)

## Services

There are also services for manual watering and setup of automatic watering mode.

### Watering

The integration publishes a service for watering, to be used in automations.

![service1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/service1.png)

Use channel names A-D and a duration value in seconds.

### Set watering mode

The integration publishes a service for the automatic watering, to be used to setup min and max
moisture levels for the plant.

![service2.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/service2.png)

Use channel names A-D and moisture percentages for min_vale and max_value.

## Installation

Install the integration using HACS:

1. Open the Home Assistant web interface and navigate to the HACS store.
2. Click on the "Integrations" tab.
3. Click on the three dots in the top right corner and select "Custom repositories".
4. Enter the URL (`https://github.com/jonnybergdahl/HomeAssistant_Growcube_Integration`) and select "Integration" as the category.
5. Click "Add".
6. Once the repository has been added, you should see the Elecrow GrowCube integration listed in the HACS store.
7. Click on the integration and then click "Install".
8. Restart Home Assistant.

## Add a GrowCube device

1. Open the Home Assistant web interface.
2. Click on "Configuration" in the left-hand menu.
3. Click on "Integrations".
4. Click on the "+" button in the bottom right corner.
5. Search for "GrowCube" and click on it.
6. Enter the IP address (or host name) of the device.

And that's it! Once you've added your GrowCube device, you should be able to see its status and control it from the Home Assistant web interface.

## Getting help

You can reach me in [#jonnys-place](https://discord.gg/SeHKWPu9Cw) on Brian Lough's Discord.

# TODO

 - Add a `ReqSyncTime` call to set time after connecting to the device
 - Add/Rename the diagnostics sensors to adhere to the last reverse engineering findings
 - Add reconnect logic after connection lost event
