"""Send Home Assistant sensor data to narodmon.ru."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from homeassistant.const import CONF_API_KEY, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    API_URL,
    CONF_DEVICE_ID,
    CONF_INTERVAL,
    CONF_SENSORS,
    DOMAIN,
    LOGGER,
)

DEFAULT_INTERVAL = 300


if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    config = {**entry.data, **entry.options}
    sender = NarodmonSender(hass, config)
    await sender.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sender
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    sender: NarodmonSender = hass.data[DOMAIN].pop(entry.entry_id)
    sender.async_unload()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class NarodmonSender:
    """Class handling sending data to narodmon.ru."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the sender."""
        self.hass = hass
        self.config = config
        self.session = async_get_clientsession(hass)
        self._unsub = None

    async def async_setup(self) -> None:
        """Register periodic update callback."""
        interval = timedelta(seconds=self.config.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self._unsub = async_track_time_interval(self.hass, self._async_send, interval)

    @callback
    def async_unload(self) -> None:
        """Cancel the periodic callback."""
        if self._unsub:
            self._unsub()

    async def _async_send(self, _now: datetime) -> None:
        """Send sensor data to narodmon.ru."""
        device_id = self.config[CONF_DEVICE_ID]
        sensors = self.config.get(CONF_SENSORS, [])
        params: dict[str, Any] = {"ID": device_id}
        if api_key := self.config.get(CONF_API_KEY):
            params["api_key"] = api_key
        for entity_id in sensors:
            state = self.hass.states.get(entity_id)
            if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue
            params[state.object_id] = state.state
        try:
            async with self.session.get(API_URL, params=params) as resp:
                await resp.text()
        except ClientError as err:  # pragma: no cover - network failures
            LOGGER.error("Failed to send data to narodmon.ru: %s", err)
