"""Config flow for the Narodmon integration."""

from __future__ import annotations

import re
import secrets
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ENTITIES
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectOptionDict
import voluptuous as vol

from .const import (
    CONF_COORDINATES_ENTITY,
    CONF_DEVICE_MAC,
    CONF_DEVICE_MODE,
    CONF_DEVICE_NAME,
    CONF_GENERATE_MAC,
    CONF_SEND_INTERVAL_CHANGED,
    CONF_SEND_INTERVAL_FORCE,
    CONF_TRANSPORT,
    DEFAULT_SEND_INTERVAL_CHANGED,
    DEFAULT_SEND_INTERVAL_FORCE,
    DEFAULT_VIRTUAL_DEVICE_NAME,
    DeviceMode,
    DOMAIN,
    Transport,
)

MAC_RE = re.compile(r"^[0-9A-Z]{12,18}$")

ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"], multiple=True)
)

COORDINATES_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["zone"], multiple=False)
)

TRANSPORT_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        mode=selector.SelectSelectorMode.LIST,
        translation_key=CONF_TRANSPORT,
        options=[
            SelectOptionDict(value=Transport.TCP, label=Transport.TCP),
            SelectOptionDict(value=Transport.HTTP, label=Transport.HTTP),
            SelectOptionDict(value=Transport.HTTPS, label=Transport.HTTPS),
        ],
    )
)

DEVICE_MODE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        mode=selector.SelectSelectorMode.LIST,
        translation_key=CONF_DEVICE_MODE,
        options=[
            SelectOptionDict(value=DeviceMode.VIRTUAL, label=DeviceMode.VIRTUAL),
            SelectOptionDict(value=DeviceMode.HA_DEVICES, label=DeviceMode.HA_DEVICES),
        ],
    )
)


def _normalize_mac(value: str) -> str:
    """Normalize MAC-like values for Narodmon."""
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


def _generate_mac() -> str:
    """Generate a random Narodmon-compatible MAC-like ID."""
    return "HA" + secrets.token_hex(5).upper()


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the common settings schema."""
    return vol.Schema(
        {
            vol.Required(CONF_TRANSPORT, default=defaults.get(CONF_TRANSPORT, Transport.TCP)): TRANSPORT_SELECTOR,
            vol.Required(CONF_DEVICE_MODE, default=defaults.get(CONF_DEVICE_MODE, DeviceMode.VIRTUAL)): DEVICE_MODE_SELECTOR,
            vol.Optional(CONF_GENERATE_MAC, default=False): selector.BooleanSelector(),
            vol.Required(CONF_DEVICE_MAC, default=defaults.get(CONF_DEVICE_MAC, _generate_mac())): selector.TextSelector(),
            vol.Optional(
                CONF_DEVICE_NAME,
                default=defaults.get(CONF_DEVICE_NAME, DEFAULT_VIRTUAL_DEVICE_NAME),
            ): selector.TextSelector(),
            vol.Optional(CONF_COORDINATES_ENTITY, default=defaults.get(CONF_COORDINATES_ENTITY)): COORDINATES_SELECTOR,
            vol.Required(
                CONF_SEND_INTERVAL_CHANGED,
                default=defaults.get(CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=300, max=86400, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_SEND_INTERVAL_FORCE,
                default=defaults.get(CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=300, max=86400, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


def _entities_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the entities selection schema."""
    return vol.Schema({vol.Required(CONF_ENTITIES, default=defaults.get(CONF_ENTITIES, [])): ENTITY_SELECTOR})


class NarodmonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Narodmon."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = _generate_mac() if user_input.pop(CONF_GENERATE_MAC, False) else _normalize_mac(user_input[CONF_DEVICE_MAC])
            if not MAC_RE.match(mac):
                errors[CONF_DEVICE_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                self._data = {**user_input, CONF_DEVICE_MAC: mac}
                return await self.async_step_entities()

        return self.async_show_form(step_id="user", data_schema=_settings_schema(user_input or {}), errors=errors)

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose entities for Narodmon export."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_ENTITIES]:
                errors["base"] = "entities_not_selected"
            else:
                return self.async_create_entry(
                    title=self._data.get(CONF_DEVICE_NAME) or self._data[CONF_DEVICE_MAC],
                    data=self._data,
                    options={CONF_ENTITIES: sorted(user_input[CONF_ENTITIES])},
                )

        return self.async_show_form(step_id="entities", data_schema=_entities_schema(user_input or {}), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return NarodmonOptionsFlow(config_entry)


class NarodmonOptionsFlow(OptionsFlow):
    """Handle Narodmon options."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = entry
        self._settings: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit sender settings."""
        errors: dict[str, str] = {}
        defaults = {**self._entry.data, **self._entry.options}

        if user_input is not None:
            mac = _generate_mac() if user_input.pop(CONF_GENERATE_MAC, False) else _normalize_mac(user_input[CONF_DEVICE_MAC])
            if not MAC_RE.match(mac):
                errors[CONF_DEVICE_MAC] = "invalid_mac"
            else:
                self._settings = {**user_input, CONF_DEVICE_MAC: mac}
                return await self.async_step_entities()

        return self.async_show_form(step_id="init", data_schema=_settings_schema(defaults), errors=errors)

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit selected entities."""
        errors: dict[str, str] = {}
        defaults = {**self._entry.data, **self._entry.options}

        if user_input is not None:
            if not user_input[CONF_ENTITIES]:
                errors["base"] = "entities_not_selected"
            else:
                return self.async_create_entry(data={**self._settings, CONF_ENTITIES: sorted(user_input[CONF_ENTITIES])})

        return self.async_show_form(step_id="entities", data_schema=_entities_schema(defaults), errors=errors)
