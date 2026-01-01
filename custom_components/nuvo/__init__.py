"""The Nuvo Multi-Zone Amplifier integration."""

import logging

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_NAME, CONF_SOURCES, CONF_ZONES, DOMAIN, NUVO_CONNECTION

PLATFORMS = [Platform.MEDIA_PLAYER]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Nuvo component from YAML configuration."""
    # Trigger import flow for YAML configurations
    if DOMAIN in config:
        for entry_config in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data=entry_config,
                )
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nuvo Multi-Zone Amplifier from a config entry."""
    from pyitachip2sl import ITachIP2SLSocketClient

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    timeout = 3

    try:
        # Create connection to iTach IP2SL gateway in executor
        connection = await hass.async_add_executor_job(
            ITachIP2SLSocketClient, host, port, timeout
        )
    except Exception as err:
        _LOGGER.error("Error connecting to iTach IP2SL at %s:%s - %s", host, port, err)
        raise ConfigEntryNotReady from err

    # Register update listener for options flow changes
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    # Store connection in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        NUVO_CONNECTION: connection,
    }

    # Forward setup to media_player platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    def _cleanup(connection) -> None:
        """Clean up the connection object."""
        del connection

    # Clean up connection
    connection = hass.data[DOMAIN][entry.entry_id][NUVO_CONNECTION]
    hass.data[DOMAIN].pop(entry.entry_id)

    await hass.async_add_executor_job(_cleanup, connection)

    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
