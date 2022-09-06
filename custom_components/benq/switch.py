"""Use serial protocol of BenQ projector to obtain state of the projector."""
# From https://github.com/Emily9121/Serial-BenQ-Projector-Home-Assistant-Integration
#
import logging
import codecs
import re
import time

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyitachip2sl==0.1']

_LOGGER = logging.getLogger(__name__)

CONF_TIMEOUT = "timeout"
CONF_WRITE_TIMEOUT = "write_timeout"

DEFAULT_NAME = "BenQ Projector"
DEFAULT_TIMEOUT = 3
DEFAULT_WRITE_TIMEOUT = 4

LAMP_MODE = "Lamp Mode"

ICON = "mdi:projector"

INPUT_SOURCE = "Input Source"

LAMP = "Lamp"
LAMP_HOURS = "Lamp Hours"

MODEL = "Model"

# Commands known to the projector
#    STATE_OFF: "* 0 IR 002\r",
CMD_DICT = {
    LAMP: "\r*pow=?#\r",
    LAMP_HOURS: "\r*ltim=?#\r",
    INPUT_SOURCE: "\r*sour=?#\r",
    LAMP_MODE: "\r*lampm=?#\r",
    MODEL: "\r*modelname=?#\r",
    STATE_ON: "\r*pow=on#\r",
    STATE_OFF: "\r*pow=off#\r",
}

DEFAULT_PORT = 4999

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(
            CONF_WRITE_TIMEOUT, default=DEFAULT_WRITE_TIMEOUT
        ): cv.positive_int,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup BenQ Projector platform."""

    port = config[CONF_PORT]
    hostname = config[CONF_HOST]
    name = config[CONF_NAME]
    timeout = config[CONF_TIMEOUT]
    write_timeout = config[CONF_WRITE_TIMEOUT]

    from pyitachip2sl import ITachIP2SLSocketClient

    try:
        itach_serial = ITachIP2SLSocketClient(hostname, port, timeout)
    except:
        _LOGGER.error("Error connecting to iTach IP2SL")
        return

    add_entities([BenQSwitch(itach_serial, name, hostname)], True)


class BenQSwitch(SwitchEntity):
    """Represents an BenQ Projector as a switch."""

    def __init__(self, itach_serial, name, hostname, **kwargs):
        """Init of the BenQ projector."""

        self._benq = itach_serial
        self._name = name
        self._hostname = hostname
        self._state = False
        self._available = False
        self._attributes = {
            LAMP_HOURS: STATE_UNKNOWN,
            INPUT_SOURCE: STATE_UNKNOWN,
            LAMP_MODE: STATE_UNKNOWN,
        }

    def _write_read(self, msg):
        """Write to the projector via iTach/GC100 and read the response."""

        cmd = codecs.encode(str.encode(msg), "hex").decode()
        try:
            response = self._benq.send_data(cmd, True)
            return response
        except:
            _LOGGER.error("Problem communicating with %s", self._hostname)
            return None


    def _write_read_format(self, msg):
        """Write msg, obtain answer and format output."""
        # answers are formatted as ***\answer\r***
        awns = self._write_read(msg)
        _LOGGER.info("awns IN is: %s", repr(awns))
        match = re.search(r"\r\r\n(.+)=(.+)#", awns)
        if match:
            return match.group(2)
        return STATE_UNKNOWN

    @property
    def available(self):
        """Return if projector is available."""
        return self._available

    @property
    def name(self):
        """Return name of the projector."""
        return self._name

    @property
    def is_on(self):
        """Return if the projector is turned on."""
        return self._state

    @property
    def state_attributes(self):
        """Return state attributes."""
        return self._attributes

    def update(self):
        """Get the latest state from the projector."""
        msg = CMD_DICT[LAMP]
        awns = self._write_read_format(msg)
        _LOGGER.info("awns OUT is: %s", repr(awns))
        if awns == "ON":
            self._state = True
            self._available = True
        elif awns == "OFF":
            self._state = False
            self._available = True
        else:
            self._available = False

        for key in self._attributes:
            msg = CMD_DICT.get(key)
            if msg:
                awns = self._write_read_format(msg)
                self._attributes[key] = awns
                time.sleep(2)

    def turn_on(self, **kwargs):
        """Turn the projector on."""
        msg = CMD_DICT[STATE_ON]
        self._write_read(msg)
        self._state = STATE_ON

    def turn_off(self, **kwargs):
        """Turn the projector off."""
        msg = CMD_DICT[STATE_OFF]
        self._write_read(msg)
        self._state = STATE_OFF

