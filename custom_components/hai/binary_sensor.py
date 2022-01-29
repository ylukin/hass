"""Platform for HAI Zone integration."""
# Based on https://github.com/home-assistant/core/blob/8d68f34650eb68470113127b9e1a67d2ae753a5b/homeassistant/components/abode/binary_sensor.py

import logging

import requests, json
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
# Full list https://github.com/home-assistant/core/blob/dev/homeassistant/components/binary_sensor/__init__.pys
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GARAGE_DOOR,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_WINDOW,
    DEVICE_CLASSES_SCHEMA,
    BinarySensorEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_HOST, CONF_ZONE, CONF_ID, CONF_NAME, CONF_DEVICE_CLASS

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_ZONE): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        }
    ]),
})

api_host = ''
api_url = ''

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the HAI Zones"""

    api_host = config[CONF_HOST]
    api_url = 'https://' + str(api_host) + '/api/zone/'

    # Add devices
    add_entities(HAIZone(zone, api_url) for zone in config[CONF_ZONE])

class HAIZone(BinarySensorEntity):
    """Representation of an HAI Zone."""

    def __init__(self, zone, api_url):
        """Initialize an HAI Zone."""
        self._name = zone['name']
        self._id = zone['id']
        self._device_class = zone['device_class']
        self._state = False
        self._api_url = api_url

    @property
    def name(self):
        """Return the name of the zone"""
        return self._name

    @property
    def is_on(self):
        """Return true if the zone is on/open."""
        return self._state

    def update(self):
        """
        Fetch new state data for this zone.
        Return true if zone is triggered.
        """

        try:
            r = requests.get(self._api_url + str(self._id))
            current_state = r.json()
        except:
            return False

        if current_state["zone_status"] == "Secure":
            self._state = False
        elif current_state["zone_status"] == "Not ready":
            self._state = True

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class
