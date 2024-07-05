[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Elecrow GrowCube integration for Home Assistant
Home Assistant integration for the [Elecrow GrowCube](https://www.elecrow.com/growcube-gardening-plants-smart-watering-kit-device.html), a smart plant watering device.

> Please note that a Growcube device can only be connected to one client at a time. That means you 
> will not be able to connect using the phone app while Home Assistant is running the integration, 
> or vice versa.

## Installation

### Install integration

Click the button to add this repository to HACS.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jonnybergdahl&category=Integration&repository=HomeAssistant_Growcube_Integration)

Then restart Home Assistant.

You can also do the above manually:
1. Open the Home Assistant web interface and navigate to the HACS store.
2. Click on the "Integrations" tab.
3. Click on the three dots in the top right corner and select "Custom repositories".
4. Enter the URL (`https://github.com/jonnybergdahl/HomeAssistant_Growcube_Integration`) and select "Integration" as the category.
5. Click "Add".
6. Once the repository has been added, you should see the Elecrow GrowCube integration listed in the HACS store.
7. Click on the integration and then click "Install".
8. Restart Home Assistant.

### Add a Growcube device

Click the button to add a Growcube device to Home Assistant.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=growcube)

Click OK when it asks if you want to setup the Elecrow Growcube integration.

![wizard1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/wizard1.png)

Enter the IP address of the Growcube device and click Submit.

![wizard2.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/wizard2.png)

> Remember to close down the phone app before this step to avoid connection issues.

You can also do this manually:

1. Open the Home Assistant web interface.
2. Click on "Configuration" in the left-hand menu.
3. Click on "Integrations".
4. Click on the "+" button in the bottom right corner.
5. Search for "GrowCube" and click on it.
6. Enter the IP address (or host name) of the device.

And that's it! Once you've added your GrowCube device, you should be able to see its status and control it from the Home Assistant web interface.

## Getting help

You can file bugs in the [issues section on Github](https://github.com/jonnybergdahl/HomeAssistant_Growcube_Integration/issues).

You can also reach me at [#jonnys-place](https://discord.gg/SeHKWPu9Cw) on Brian Lough's Discord.

## Sensors and services

![device1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/device1.png)

### Sensors 

The integration adds sensors for temperature, humidity and four sensors for moisture.

![sensors1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/sensors1.png)

### Diagnostics

The diagnostics sensors includes things such as device lock, sensor disconnect warnings and pump blocked warnings.

![diagnostics1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/diagnostics1.png)

### Controls

There are controls to let you manually water a plant. Thee will activate the pump for 5 seconds for a given outlet.

![controls1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/controls1.png)

### Services

There are also services for manual watering and setup of automatic watering mode.

#### Watering

The integration publishes a service for watering, to be used in automations.

![service1.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/service1.png)

Use channel names A-D and a duration value in seconds.

#### Set watering mode

The integration publishes a service for the automatic watering, to be used to setup min and max
moisture levels for the plant.

![service2.png](https://raw.githubusercontent.com/jonnybergdahl/HomeAssistant_Growcube_Integration/main/images/service2.png)

Use channel names A-D and moisture percentages for min_vale and max_value.

