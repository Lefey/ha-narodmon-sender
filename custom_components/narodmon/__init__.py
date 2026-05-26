"""Narodmon custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .sender import NarodmonSender

type NarodmonConfigEntry = ConfigEntry[NarodmonSender]


async def async_setup_entry(hass: HomeAssistant, entry: NarodmonConfigEntry) -> bool:
    """Set up Narodmon from a config entry."""
    sender = NarodmonSender(hass, entry)
    await sender.async_start()

    entry.runtime_data = sender
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NarodmonConfigEntry) -> bool:
    """Unload a Narodmon config entry."""
    await entry.runtime_data.async_unload()
    return True


async def _async_update_listener(hass: HomeAssistant, entry: NarodmonConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)

