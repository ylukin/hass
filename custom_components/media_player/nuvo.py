"""
Support for Nuvo Essentia E6G amplifiers via Global Cache IP2SL.

"""
import logging
import codecs
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    DOMAIN, MEDIA_PLAYER_SCHEMA, PLATFORM_SCHEMA, SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP, MediaPlayerDevice)
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_NAME, CONF_PORT, CONF_HOST, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyitachip2sl==0.1']

_LOGGER = logging.getLogger(__name__)

SUPPORT_NUVO = SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | \
                    SUPPORT_VOLUME_STEP | SUPPORT_TURN_ON | \
                    SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

ZONE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
})

SOURCE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
})

CONF_ZONES = 'zones'
CONF_SOURCES = 'sources'

DATA_NUVO = 'nuvo'

SERVICE_SNAPSHOT = 'snapshot'
SERVICE_RESTORE = 'restore'

DEFAULT_PORT = 4999

# Valid zone ids: 1-6
ZONE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=6))

# Valid source ids: 1-6
SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=6))

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_ZONES): vol.Schema({ZONE_IDS: ZONE_SCHEMA}),
    vol.Required(CONF_SOURCES): vol.Schema({SOURCE_IDS: SOURCE_SCHEMA}),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nuvo E6G 6-zone amplifier platform."""
    
    port = config.get(CONF_PORT)
    hostname = config.get(CONF_HOST)
    timeout = 1

    from pyitachip2sl import ITachIP2SLSocketClient
    
    try:
        itach_serial = ITachIP2SLSocketClient(hostname, port, timeout)
    except:
        _LOGGER.error("Error connecting to iTach IP2SL")
        return

    sources = {source_id: extra[CONF_NAME] for source_id, extra
               in config[CONF_SOURCES].items()}

    hass.data[DATA_NUVO] = []
    for zone_id, extra in config[CONF_ZONES].items():
        _LOGGER.info("Adding zone %d - %s", zone_id, extra[CONF_NAME])
        hass.data[DATA_NUVO].append(NuvoZone(
            itach_serial, sources, zone_id, extra[CONF_NAME]))

    add_entities(hass.data[DATA_NUVO], True)

    def service_handle(service):
        """Handle for services."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)

        if entity_ids:
            devices = [device for device in hass.data[DATA_NUVO]
                       if device.entity_id in entity_ids]
        else:
            devices = hass.data[DATA_NUVO]

        for device in devices:
            if service.service == SERVICE_SNAPSHOT:
                device.snapshot()
            elif service.service == SERVICE_RESTORE:
                device.restore()

    hass.services.register(
        DOMAIN, SERVICE_SNAPSHOT, service_handle, schema=MEDIA_PLAYER_SCHEMA)

    hass.services.register(
        DOMAIN, SERVICE_RESTORE, service_handle, schema=MEDIA_PLAYER_SCHEMA)


class NuvoZone(MediaPlayerDevice):
    """Representation of a Nuvo E6G amplifier zone."""

    def __init__(self, itach_serial, sources, zone_id, zone_name):
        """Initialize new zone."""
        self._nuvo = itach_serial
        # dict source_id -> source name
        self._source_id_name = sources
        # dict source name -> source_id
        self._source_name_id = {v: k for k, v in sources.items()}
        # ordered list of all source names
        self._source_names = sorted(self._source_name_id.keys(),
                                    key=lambda v: self._source_name_id[v])
        self._zone_id = zone_id
        self._name = zone_name

        self._snapshot = None
        self._state = None
        self._volume = 0
        self._source = None
        self._mute = None

    def zone_status(self):
        """Retrieve zone status from Nuvo amplifier."""
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "STATUS?\r"), "hex").decode()
        response = self._nuvo.send_data(cmd, True)
        status = {}
        if response:
            if ("Z" + str(self._zone_id) + ",ON") in response:
                status["power"] = True
                try:
                    status["volume"] = re.search("(VOL)(\d+)",response).group(2)
                except:
                    status["volume"] = 0
                    status["mute"] = True
                status["source"] = re.search("(SRC)(\d+)",response).group(2)
                status["mute"] = False
                return status
            elif ("Z" + str(self._zone_id) + ",OFF") in response:
                status["power"] = False
                return status
        else:
            return None

    def update(self):
        """Update zone state in Home Assistant."""
        state = self.zone_status()
        if not state:
            _LOGGER.error("Unable to update state for Zone ID: " + str(self._zone_id))
            return False
        self._state = STATE_ON if state["power"] else STATE_OFF
        if self._state == STATE_ON:
            self._volume = int(state["volume"])
            self._mute = state["mute"]
            idx = int(state["source"])
            if idx in self._source_id_name:
                self._source = self._source_id_name[idx]
            else:
                self._source = None
        return True

    @property
    def name(self):
        """Return the name of the zone."""
        return self._name

    @property
    def state(self):
        """Return the state of the zone."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is None:
            return None
        return 1 - (self._volume / 80.0)

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._mute

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_NUVO

    @property
    def media_title(self):
        """Return the current source as medial title."""
        return self._source

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_names

    def snapshot(self):
        """Save zone's current state."""
        self._snapshot = self._nuvo.zone_status(self._zone_id)

    def restore(self):
        """Restore saved state."""
        if self._snapshot:
            self._nuvo.restore_zone(self._snapshot)
            self.schedule_update_ha_state(True)

    def select_source(self, source):
        """Set input source."""
        if source not in self._source_name_id:
            return
        idx = self._source_name_id[source]
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "SRC" + str(idx) + "\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)

    def turn_on(self):
        """Turn the zone on."""
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "ON\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)

    def turn_off(self):
        """Turn the zone off."""
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "OFF\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) the zone."""
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "MUTE\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        converted_vol = int(round((1-volume) * 80))

        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "VOL" + str(converted_vol) + "\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)

    def volume_up(self):
        """Increase the volume for the zone."""
        if self._volume is None:
            return
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "VOL+\r"), "hex").decode()
        response = self._nuvo.send_data(cmd, True)

    def volume_down(self):
        """Decrease the volume for the zone."""
        if self._volume is None:
            return
        cmd = codecs.encode(str.encode("*Z" + str(self._zone_id) + "VOL-\r"), "hex").decode()
        self._nuvo.send_data(cmd, True)
