"""Platform for light integration."""
# Based on https://github.com/home-assistant/example-custom-config/blob/master/custom_components/example_light/light.py

import logging

import requests, json
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA, Light)
from homeassistant.const import CONF_HOST, CONF_DEVICES, CONF_ID, CONF_NAME

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
        }
    ]),
})

api_host = ''
api_url = ''

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the HAI Light platform."""

    api_host = config[CONF_HOST]
    api_url = 'https://' + str(api_host) + '/api/light/'

    # Add devices
    add_entities(HAILight(light, api_url) for light in config[CONF_DEVICES])

class HAILight(Light):
    """Representation of an HAI Light."""

    def __init__(self, light, api_url):
        """Initialize an HAI Light."""
        self._name = light['name']
        self._id = light['id']
        self._state = False
        self._brightness = 0
        self._api_url = api_url

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """

        # snapshot current brightness before attempting to update
        prev_brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            # scale from 1-255 to 1-99
            hai_level = int((self._brightness / 255)*100)
            r = requests.put(self._api_url + str(self._id), json={'is_on':True, 'brightness_level':hai_level})
            if r.status_code == 202:
                self._state = True
            else:
                self._brightness = prev_brightness
        else:
            r = requests.put(self._api_url + str(self._id), json={'is_on':True})
            if r.status_code == 202:
                self._state = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""

        r = requests.put(self._api_url + str(self._id), json={'is_on':False})
        if r.status_code == 202:
            self._state = False


    def update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """

        try:
            r = requests.get(self._api_url + str(self._id))
            current_state = r.json()
        except:
            return False

        self._state = current_state["is_on"]
        # light is currently dimmed
        if current_state["brightness_level"] > 100:
            # scale brightness level from 1-99 to 1-255
            self._brightness = int(((current_state["brightness_level"] - 100)*255)/100)
        # light is on to max brightness
        elif current_state["brightness_level"] == '001':
            self._brightness = 255
        # light is currently off
        elif current_state["brightness_level"] == '000':
            self._brightness = 0
