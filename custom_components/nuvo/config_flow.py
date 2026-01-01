"""Config flow for Nuvo Multi-Zone Amplifier integration."""

from __future__ import annotations

import codecs
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import VolDictType

from .const import (
    CONF_SOURCES,
    CONF_ZONES,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    SOURCE_IDS,
    ZONE_IDS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    from pyitachip2sl import ITachIP2SLSocketClient

    host = data[CONF_HOST]
    port = data[CONF_PORT]
    timeout = 3

    try:
        # Test connection - this is sufficient verification
        connection = await hass.async_add_executor_job(
            ITachIP2SLSocketClient, host, port, timeout
        )
        _LOGGER.info("Successfully connected to iTach IP2SL at %s:%s", host, port)
    except Exception as err:
        _LOGGER.error("Error connecting to iTach IP2SL at %s:%s: %s", host, port, err)
        raise CannotConnect from err

    # Extract zone and source names from data
    # Handle both UI form data (zone_1, source_1) and import data (CONF_ZONES, CONF_SOURCES)
    if CONF_ZONES in data and isinstance(data[CONF_ZONES], dict):
        # Import path - zones/sources already in correct format
        zones = {int(k): v for k, v in data[CONF_ZONES].items()}
        sources = {int(k): v for k, v in data[CONF_SOURCES].items()}
    else:
        # UI form path - extract from zone_1, source_1 keys
        zones = {}
        for zone_id in ZONE_IDS:
            zone_key = f"zone_{zone_id}"
            if zone_key in data and data[zone_key]:
                zones[zone_id] = data[zone_key].strip()

        sources = {}
        for source_id in SOURCE_IDS:
            source_key = f"source_{source_id}"
            if source_key in data and data[source_key]:
                sources[source_id] = data[source_key].strip()

    # Return validated data
    return {
        CONF_NAME: data.get(CONF_NAME, DEFAULT_NAME).strip(),
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_ZONES: zones,
        CONF_SOURCES: sources,
    }


def _build_schema(
    name: str | None = None,
    host: str | None = None,
    port: int = DEFAULT_PORT,
    zones: dict[int, str] | None = None,
    sources: dict[int, str] | None = None,
) -> vol.Schema:
    """Build the configuration schema."""
    zones = zones or {}
    sources = sources or {}

    schema = {
        vol.Optional(CONF_NAME, default=name or DEFAULT_NAME): str,
        vol.Required(CONF_HOST, default=host or ""): str,
        vol.Required(CONF_PORT, default=port): int,
    }

    # Add zone fields
    for zone_id in ZONE_IDS:
        zone_key = f"zone_{zone_id}"
        default_value = zones.get(zone_id, "")
        schema[vol.Optional(zone_key, default=default_value)] = str

    # Add source fields
    for source_id in SOURCE_IDS:
        source_key = f"source_{source_id}"
        default_value = sources.get(source_id, "")
        schema[vol.Optional(source_key, default=default_value)] = str

    return vol.Schema(schema)


class NuvoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nuvo Multi-Zone Amplifier."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Create entry with validated data
                return self.async_create_entry(
                    title=info[CONF_NAME],
                    data=info,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NotNuvo:
                errors["base"] = "not_nuvo"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors=errors,
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        _LOGGER.info("Importing Nuvo configuration from YAML")

        # Convert YAML format to config entry format
        # YAML format: zones: {1: {name: "Patio"}}
        # Config entry format: zones: {1: "Patio"}
        zones = {}
        if CONF_ZONES in import_data:
            for zone_id, zone_config in import_data[CONF_ZONES].items():
                if isinstance(zone_config, dict) and CONF_NAME in zone_config:
                    zones[int(zone_id)] = zone_config[CONF_NAME]
                elif isinstance(zone_config, str):
                    zones[int(zone_id)] = zone_config

        sources = {}
        if CONF_SOURCES in import_data:
            for source_id, source_config in import_data[CONF_SOURCES].items():
                if isinstance(source_config, dict) and CONF_NAME in source_config:
                    sources[int(source_id)] = source_config[CONF_NAME]
                elif isinstance(source_config, str):
                    sources[int(source_id)] = source_config

        # Build data dictionary
        data = {
            CONF_NAME: DEFAULT_NAME,  # Default name for imported configs
            CONF_HOST: import_data[CONF_HOST],
            CONF_PORT: import_data.get(CONF_PORT, DEFAULT_PORT),
            CONF_ZONES: zones,
            CONF_SOURCES: sources,
        }

        # Validate connection
        try:
            await validate_input(self.hass, data)
        except Exception as err:
            _LOGGER.error("Failed to import Nuvo configuration: %s", err)
            return self.async_abort(reason="cannot_connect")

        # Create entry
        return self.async_create_entry(
            title=f"{DEFAULT_NAME} (imported)",
            data=data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NuvoOptionsFlowHandler:
        """Define the config flow to handle options."""
        return NuvoOptionsFlowHandler()


class NuvoOptionsFlowHandler(OptionsFlow):
    """Handle Nuvo options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Extract zones and sources from user input
            zones = {}
            for zone_id in ZONE_IDS:
                zone_key = f"zone_{zone_id}"
                if zone_key in user_input and user_input[zone_key]:
                    zones[zone_id] = user_input[zone_key].strip()

            sources = {}
            for source_id in SOURCE_IDS:
                source_key = f"source_{source_id}"
                if source_key in user_input and user_input[source_key]:
                    sources[source_id] = user_input[source_key].strip()

            # Update config entry data (not options, since zones/sources are core data)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME).strip(),
                    CONF_ZONES: zones,
                    CONF_SOURCES: sources,
                },
            )

            return self.async_create_entry(title="", data={})

        # Get current configuration
        current_name = self.config_entry.data.get(CONF_NAME, DEFAULT_NAME)
        current_zones = self.config_entry.data.get(CONF_ZONES, {})
        current_sources = self.config_entry.data.get(CONF_SOURCES, {})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                name=current_name,
                zones=current_zones,
                sources=current_sources,
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NotNuvo(HomeAssistantError):
    """Error to indicate device is not a Nuvo E6G."""
