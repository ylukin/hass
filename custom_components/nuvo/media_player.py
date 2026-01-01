"""Support for Nuvo Essentia E6G amplifiers via Global Cache IP2SL."""

from __future__ import annotations

import codecs
import logging
import re
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NAME,
    CONF_SOURCES,
    CONF_ZONES,
    DEFAULT_NAME,
    DOMAIN,
    NUVO_CONNECTION,
    SERVICE_RESTORE,
    SERVICE_SNAPSHOT,
)

_LOGGER = logging.getLogger(__name__)

# Parallel updates must be 1 to serialize zone queries
PARALLEL_UPDATES = 1


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    """Set up Nuvo platform (for YAML import only)."""
    _LOGGER.warning(
        "Configuration of Nuvo in YAML is deprecated. "
        "Your configuration has been imported into the UI and can be safely removed. "
        "Please remove the Nuvo configuration from configuration.yaml."
    )

    # Trigger import flow
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nuvo media player from config entry."""
    connection = hass.data[DOMAIN][config_entry.entry_id][NUVO_CONNECTION]
    zones = config_entry.data[CONF_ZONES]
    sources = config_entry.data[CONF_SOURCES]

    entities = [
        NuvoZone(connection, sources, config_entry, zone_id, zone_name)
        for zone_id, zone_name in zones.items()
    ]

    async_add_entities(entities, update_before_add=True)

    # Register snapshot/restore services
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SNAPSHOT,
        {},
        "snapshot",
    )

    platform.async_register_entity_service(
        SERVICE_RESTORE,
        {},
        "async_restore",
    )


class NuvoZone(MediaPlayerEntity):
    """Representation of a Nuvo E6G amplifier zone."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )
    _attr_has_entity_name = True

    def __init__(
        self,
        connection: Any,
        sources: dict[int, str],
        config_entry: ConfigEntry,
        zone_id: int,
        zone_name: str,
    ) -> None:
        """Initialize the Nuvo zone."""
        self._connection = connection
        self._zone_id = zone_id

        # CRITICAL: Set unique_id using config_entry.entry_id
        self._attr_unique_id = f"{config_entry.entry_id}_{zone_id}"

        # Get device name from config (with fallback)
        device_name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)

        # Device info - uses custom name, NOT IP address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=device_name,
            manufacturer="Legrand (Nuvo)",
            model="Essentia E6G",
            configuration_url=f"http://{config_entry.data[CONF_HOST]}:{config_entry.data[CONF_PORT]}",
        )

        # Entity name (combined with device name)
        self._attr_name = zone_name

        # Source handling
        self._source_id_name = sources
        self._source_name_id = {v: k for k, v in sources.items()}
        self._attr_source_list = sorted(
            self._source_name_id.keys(), key=lambda v: self._source_name_id[v]
        )

        # Debug: Log configured sources
        _LOGGER.debug(
            "Zone %s initialized with sources: %s (IDs: %s)",
            zone_id,
            self._source_id_name,
            list(self._source_id_name.keys())
        )

        # Snapshot storage
        self._snapshot = None

    def _zone_status(self) -> dict[str, Any] | None:
        """Retrieve zone status from Nuvo amplifier (synchronous)."""
        # Add delay to prevent buffer overruns (protocol requires 50ms between commands)
        import time
        time.sleep(0.1)  # 100ms delay to be safe

        cmd_text = f"*Z{self._zone_id}STATUS?\r"
        cmd = codecs.encode(cmd_text.encode(), "hex").decode()

        _LOGGER.debug("Zone %s: Sending command: %s (hex: %s)", self._zone_id, repr(cmd_text), cmd)

        # Send query twice - first response may be stale from buffer
        response1 = self._connection.send_data(cmd, True)
        _LOGGER.debug("Zone %s: First response (may be stale): %r", self._zone_id, response1)

        time.sleep(0.05)  # Small delay between queries

        response2 = self._connection.send_data(cmd, True)
        _LOGGER.debug("Zone %s: Second response (fresh): %r", self._zone_id, response2)

        # Use the second response
        response = response2
        status = {}

        if not response:
            _LOGGER.error("No response received for zone %s", self._zone_id)
            return None

        _LOGGER.debug("Zone %s: Received raw response: %r", self._zone_id, response)

        # Handle multiple buffered responses - split by line breaks
        # and find the response for THIS zone
        response_lines = response.strip().split('\n')
        matching_response = None

        for line in response_lines:
            line = line.strip()
            # Check if this line is for our zone
            if f"#Z{self._zone_id}," in line or f"Z{self._zone_id}," in line:
                matching_response = line
                _LOGGER.debug("Zone %s: Found matching response: %r", self._zone_id, line)
                break
            elif "#ALLOFF" in line or "ALLOFF" in line:
                matching_response = line
                break

        if not matching_response:
            _LOGGER.error(
                "Zone %s: No matching response found in: %r",
                self._zone_id,
                response_lines
            )
            return None

        response = matching_response
        _LOGGER.debug("Zone %s: Using response: %r", self._zone_id, response)

        # Handle ALLOFF response
        if "#ALLOFF" in response or "ALLOFF" in response:
            status["power"] = False
            return status

        # Handle zone ON response (with or without # prefix)
        zone_on_pattern = f"#Z{self._zone_id},ON"
        zone_on_pattern_alt = f"Z{self._zone_id},ON"
        if zone_on_pattern in response or zone_on_pattern_alt in response:
            status["power"] = True
            try:
                vol_match = re.search(r"VOL(\d+)", response)
                if vol_match:
                    status["volume"] = vol_match.group(1)
                else:
                    status["volume"] = "0"
                    status["mute"] = True
                    _LOGGER.error("Failed to parse volume from response: %s", response)
            except Exception as err:
                status["volume"] = "0"
                status["mute"] = True
                _LOGGER.error("Error parsing volume: %s", err)

            try:
                src_match = re.search(r"SRC(\d+)", response)
                if src_match:
                    status["source"] = src_match.group(1)
                else:
                    _LOGGER.error("Failed to parse source from response: %s", response)
            except Exception as err:
                _LOGGER.error("Error parsing source: %s", err)

            status["mute"] = status.get("mute", False)
            return status

        # Handle zone OFF response (with or without # prefix)
        zone_off_pattern = f"#Z{self._zone_id},OFF"
        zone_off_pattern_alt = f"Z{self._zone_id},OFF"
        _LOGGER.debug("Checking for OFF: '%s' or '%s' in '%r'", zone_off_pattern, zone_off_pattern_alt, response)
        if zone_off_pattern in response or zone_off_pattern_alt in response:
            status["power"] = False
            return status

        # Unexpected response format
        _LOGGER.error("Unexpected response format: %r (expected zone %s patterns)", response, self._zone_id)
        return None

    def update(self) -> None:
        """Update zone state (called in executor by HA)."""
        try:
            state = self._zone_status()
            if not state:
                _LOGGER.error("Unable to update state for Zone ID: %s", self._zone_id)
                return

            self._attr_state = (
                MediaPlayerState.ON if state["power"] else MediaPlayerState.OFF
            )

            if self._attr_state == MediaPlayerState.ON:
                # Convert Nuvo volume (0-79, inverted) to HA (0.0-1.0)
                volume = int(state.get("volume", 0))
                self._attr_volume_level = 1 - (volume / 80.0)
                self._attr_is_volume_muted = state.get("mute", False)

                # Set source
                source_id = int(state.get("source", 0))
                _LOGGER.debug(
                    "Zone %s: Checking source_id %s (type: %s) against available sources: %s (key types: %s)",
                    self._zone_id,
                    source_id,
                    type(source_id),
                    list(self._source_id_name.keys()),
                    [type(k) for k in self._source_id_name.keys()]
                )
                # Try both int and str keys for compatibility
                if source_id in self._source_id_name:
                    self._attr_source = self._source_id_name[source_id]
                elif str(source_id) in self._source_id_name:
                    self._attr_source = self._source_id_name[str(source_id)]
                else:
                    _LOGGER.error(
                        "Invalid source index: %s (type: %s, available: %s with types: %s)",
                        source_id,
                        type(source_id),
                        list(self._source_id_name.keys()),
                        [type(k) for k in self._source_id_name.keys()]
                    )
                    self._attr_source = None

        except Exception as err:
            _LOGGER.error("Error updating zone %s: %s", self._zone_id, err)

    @property
    def media_title(self) -> str | None:
        """Return current source as media title."""
        return self._attr_source

    async def async_turn_on(self) -> None:
        """Turn the zone on."""
        cmd = codecs.encode(f"*Z{self._zone_id}ON\r".encode(), "hex").decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_turn_off(self) -> None:
        """Turn the zone off."""
        cmd = codecs.encode(f"*Z{self._zone_id}OFF\r".encode(), "hex").decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) the zone."""
        cmd = codecs.encode(f"*Z{self._zone_id}MUTE\r".encode(), "hex").decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        # Convert HA volume (0.0-1.0) to Nuvo (0-79, inverted)
        converted_vol = int(round((1 - volume) * 80))
        cmd = codecs.encode(
            f"*Z{self._zone_id}VOL{converted_vol}\r".encode(), "hex"
        ).decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_volume_up(self) -> None:
        """Increase the volume for the zone."""
        cmd = codecs.encode(f"*Z{self._zone_id}VOL+\r".encode(), "hex").decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_volume_down(self) -> None:
        """Decrease the volume for the zone."""
        cmd = codecs.encode(f"*Z{self._zone_id}VOL-\r".encode(), "hex").decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    async def async_select_source(self, source: str) -> None:
        """Set input source."""
        if source not in self._source_name_id:
            _LOGGER.error("Unknown source: %s", source)
            return

        source_id = self._source_name_id[source]
        cmd = codecs.encode(
            f"*Z{self._zone_id}SRC{source_id}\r".encode(), "hex"
        ).decode()
        await self.hass.async_add_executor_job(self._connection.send_data, cmd, True)

    def snapshot(self) -> None:
        """Save current state."""
        self._snapshot = {
            "power": self._attr_state == MediaPlayerState.ON,
            "volume": self._attr_volume_level,
            "source": self._attr_source,
            "mute": self._attr_is_volume_muted,
        }
        _LOGGER.debug("Snapshot saved for zone %s: %s", self._zone_id, self._snapshot)

    async def async_restore(self) -> None:
        """Restore saved state."""
        if not self._snapshot:
            _LOGGER.warning("No snapshot to restore for zone %s", self._zone_id)
            return

        _LOGGER.debug("Restoring snapshot for zone %s: %s", self._zone_id, self._snapshot)

        try:
            if self._snapshot["power"]:
                await self.async_turn_on()
                # Brief delay to let zone power up (reduced from 0.5s)
                await self.hass.async_add_executor_job(
                    __import__("time").sleep, 0.2
                )

                # Send all commands without waiting
                if self._snapshot["source"]:
                    await self.async_select_source(self._snapshot["source"])

                if self._snapshot["volume"] is not None:
                    await self.async_set_volume_level(self._snapshot["volume"])

                if self._snapshot["mute"]:
                    await self.async_mute_volume(True)
            else:
                await self.async_turn_off()

            # Schedule update without blocking (removed force_refresh)
            self.async_schedule_update_ha_state()
        except Exception as err:
            _LOGGER.error("Error restoring zone %s: %s", self._zone_id, err)
