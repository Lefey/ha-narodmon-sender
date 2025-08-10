"""Config flow for Narodmon Sender."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector

from .const import CONF_DEVICE_ID, CONF_INTERVAL, CONF_SENSORS, DOMAIN


class NarodmonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Narodmon Sender."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step of the config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            data = {
                CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
            }
            if api_key := user_input.get(CONF_API_KEY):
                data[CONF_API_KEY] = api_key
            options = {
                CONF_SENSORS: user_input.get(CONF_SENSORS, []),
                CONF_INTERVAL: user_input.get(CONF_INTERVAL, 300),
            }
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_ID], data=data, options=options
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): selector.TextSelector(),
                vol.Optional(CONF_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", multiple=True)
                ),
                vol.Optional(CONF_INTERVAL, default=300): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=60, max=3600, step=60, unit="s")
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NarodmonOptionsFlowHandler:
        """Return the options flow handler."""
        return NarodmonOptionsFlowHandler(config_entry)


class NarodmonOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Narodmon Sender options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        """Manage the options for the integration."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SENSORS,
                    default=self.config_entry.options.get(CONF_SENSORS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", multiple=True)
                ),
                vol.Optional(
                    CONF_INTERVAL,
                    default=self.config_entry.options.get(CONF_INTERVAL, 300),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=60, max=3600, step=60, unit="s")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
