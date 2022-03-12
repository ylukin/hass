"""HAI switch implementation."""

import logging

import requests, json
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
from homeassistant.components.switch import (
    PLATFORM_SCHEMA, SwitchEntity)
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
    """Set up the HAI Switch platform."""

    api_host = config[CONF_HOST]
    # using the light REST API endpoint because the HAI commands are the same
    api_url = 'https://' + str(api_host) + '/api/light/'

    # Add devices
    add_entities(HAISwitch(switch, api_url) for switch in config[CONF_DEVICES])

class HAISwitch(SwitchEntity):
    """Representation of an HAI Switch."""

    def __init__(self, switch, api_url):
        """Initialize an HAI Switch."""
        self._name = switch['name']
        self._id = switch['id']
        self._state = False
        self._api_url = api_url

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:toggle-switch"

    def turn_on(self, **kwargs):
        """Turn the switch on."""

        r = requests.put(self._api_url + str(self._id), json={'is_on':True})
        if r.status_code == 202:
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""

        r = requests.put(self._api_url + str(self._id), json={'is_on':False})
        if r.status_code == 202:
            self._state = False

    def update(self):
        """Fetch new state data for this switch.

        This is the only method that should fetch new data for Home Assistant.
        """

        try:
            r = requests.get(self._api_url + str(self._id))
            current_state = r.json()
        except:
            return False

        self._state = current_state["is_on"]
