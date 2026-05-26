"""Narodmon sender runtime."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import timedelta
import hashlib
import json
import logging
import socket
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ENTITIES,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval

from .const import (
    CONF_COORDINATES_ENTITY,
    CONF_DEVICE_MAC,
    CONF_DEVICE_MODE,
    CONF_DEVICE_NAME,
    CONF_SEND_INTERVAL_CHANGED,
    CONF_SEND_INTERVAL_FORCE,
    CONF_TRANSPORT,
    DEFAULT_SEND_INTERVAL_CHANGED,
    DEFAULT_SEND_INTERVAL_FORCE,
    DEFAULT_VIRTUAL_DEVICE_NAME,
    DeviceMode,
    MAX_PACKET_SIZE,
    NARODMON_HOST,
    NARODMON_HTTP_URL,
    NARODMON_HTTPS_URL,
    NARODMON_PORT,
    SOCKET_TIMEOUT,
    Transport,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_TO_NARODMON_TYPE = {
    "temperature": "TEMP",
    "humidity": "H",
    "pressure": "PRESS",
    "battery": "BATCHARGE",
    "power": "W",
    "illuminance": "LIGHT",
    "signal_strength": "RSSI",
}

INVALID_STATES = {None, STATE_UNKNOWN, STATE_UNAVAILABLE, ""}


class NarodmonSender:
    """Send selected Home Assistant entities to Narodmon."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sender."""
        self.hass = hass
        self.entry = entry
        self._unsub: list[Callable[[], None]] = []
        self._last_values: dict[str, float] = {}
        self._last_send_time = None
        self._data_changed = False

    @property
    def _config(self) -> dict[str, Any]:
        """Return merged entry config."""
        return {**self.entry.data, **self.entry.options}

    @property
    def _entities(self) -> list[str]:
        """Return selected entities."""
        return list(self._config.get(CONF_ENTITIES, []))

    async def async_start(self) -> None:
        """Start tracking entities and scheduled sends."""
        self._unsub.append(async_track_state_change_event(self.hass, self._entities, self._async_state_changed))
        self._unsub.append(async_call_later(self.hass, 30, self._async_initial_send))
        self._unsub.append(async_track_time_interval(self.hass, self._async_scheduler, timedelta(seconds=60)))

        _LOGGER.info("Narodmon JSON sender started for %s entities", len(self._entities))

    async def async_unload(self) -> None:
        """Unload the sender."""
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Handle selected entity state changes."""
        new_state: State | None = event.data.get("new_state")
        if new_state is None or not self._is_valid_state(new_state.state):
            return

        value = self._state_value(new_state)
        if value is None:
            return

        if self._last_values.get(new_state.entity_id) != value:
            self._last_values[new_state.entity_id] = value
            self._data_changed = True
            _LOGGER.debug("Narodmon data changed: %s = %s", new_state.entity_id, value)

    async def _async_initial_send(self, _: Any) -> None:
        """Send initial values after Home Assistant startup settles."""
        await self._async_send_all()

    async def _async_scheduler(self, _: Any) -> None:
        """Send changed data by interval or force-send stale data."""
        now = self.hass.loop.time()
        if self._last_send_time is None:
            await self._async_send_all()
            return

        delta = now - self._last_send_time
        changed_interval = int(self._config.get(CONF_SEND_INTERVAL_CHANGED, DEFAULT_SEND_INTERVAL_CHANGED))
        force_interval = int(self._config.get(CONF_SEND_INTERVAL_FORCE, DEFAULT_SEND_INTERVAL_FORCE))

        if self._data_changed and delta >= changed_interval:
            await self._async_send_all()
            return

        if delta >= force_interval:
            await self._async_send_all()

    async def _async_send_all(self) -> None:
        """Build and send a Narodmon JSON packet."""
        packet = self._build_packet()
        if packet is None:
            _LOGGER.warning("No valid Narodmon data to send")
            return

        payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) > MAX_PACKET_SIZE:
            _LOGGER.error("Narodmon JSON packet is larger than %s bytes; reduce selected entities", MAX_PACKET_SIZE)
            return

        _LOGGER.debug("Sending Narodmon JSON data: %s", payload)

        transport = Transport(self._config.get(CONF_TRANSPORT, Transport.TCP))
        try:
            if transport == Transport.TCP:
                reply = await self.hass.async_add_executor_job(_send_tcp_payload, payload)
            else:
                reply = await self._async_send_http_payload(payload, transport)
        except (ClientError, OSError) as err:
            _LOGGER.error("Narodmon connection error: %s", err)
            return

        self._last_send_time = self.hass.loop.time()
        self._data_changed = False
        _log_server_reply(reply, transport)

    async def _async_send_http_payload(self, payload: str, transport: Transport) -> str:
        """Send payload through HTTP(S) POST."""
        url = NARODMON_HTTPS_URL if transport == Transport.HTTPS else NARODMON_HTTP_URL
        session = async_get_clientsession(self.hass)
        async with session.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}) as response:
            response.raise_for_status()
            return await response.text()

    def _build_packet(self) -> dict[str, Any] | None:
        """Build Narodmon JSON protocol packet."""
        devices = self._build_devices()
        if not devices:
            return None
        return {"devices": devices}

    def _build_devices(self) -> list[dict[str, Any]]:
        """Build JSON devices from selected entities."""
        config = self._config
        device_mode = DeviceMode(config.get(CONF_DEVICE_MODE, DeviceMode.VIRTUAL))
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        grouped: dict[str, list[State]] = defaultdict(list)
        for entity_id in self._entities:
            state = self.hass.states.get(entity_id)
            if state is None or not self._is_valid_state(state.state) or self._state_value(state) is None:
                continue

            group_id = "virtual"
            if device_mode == DeviceMode.HA_DEVICES:
                registry_entry = entity_registry.async_get(entity_id)
                if registry_entry and registry_entry.device_id:
                    group_id = registry_entry.device_id

            grouped[group_id].append(state)

        devices: list[dict[str, Any]] = []
        for group_id, states in grouped.items():
            if group_id == "virtual":
                device = {
                    "mac": config[CONF_DEVICE_MAC],
                    "name": config.get(CONF_DEVICE_NAME) or DEFAULT_VIRTUAL_DEVICE_NAME,
                }
                self._add_coordinates(device)
            else:
                registry_device = device_registry.async_get(group_id)
                device = {
                    "mac": _stable_id(group_id, "HA"),
                    "name": _device_name(registry_device, group_id),
                }

            sensors = self._build_sensors(states)
            if sensors:
                device["sensors"] = sensors
                devices.append(device)

        return devices

    def _add_coordinates(self, device: dict[str, Any]) -> None:
        """Add coordinates from a zone entity to the virtual device."""
        if coordinates_entity := self._config.get(CONF_COORDINATES_ENTITY):
            if state := self.hass.states.get(coordinates_entity):
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                if lat is not None and lon is not None:
                    device["lat"] = lat
                    device["lon"] = lon

    def _build_sensors(self, states: list[State]) -> list[dict[str, Any]]:
        """Build Narodmon sensors for a device group."""
        sensors: list[dict[str, Any]] = []

        for state in states:
            value = self._state_value(state)
            if value is None:
                continue

            sensor: dict[str, Any] = {
                "id": self._sensor_id(state),
                "name": state.name,
                "value": value,
            }
            if unit := state.attributes.get(ATTR_UNIT_OF_MEASUREMENT):
                sensor["unit"] = unit

            sensors.append(sensor)

        return sensors

    @staticmethod
    def _sensor_id(state: State) -> str:
        """Return a stable Narodmon sensor metric ID."""
        if state.entity_id.split(".", 1)[0] == "binary_sensor":
            prefix = "S"
        else:
            prefix = DEVICE_CLASS_TO_NARODMON_TYPE.get(state.attributes.get("device_class"), "SENSOR")

        digest = hashlib.sha1(state.entity_id.encode("utf-8")).hexdigest().upper()
        return f"{prefix}{digest[:4]}"

    @staticmethod
    def _is_valid_state(state: str | None) -> bool:
        """Return whether a state can be sent."""
        return state not in INVALID_STATES

    @staticmethod
    def _state_value(state: State) -> float | None:
        """Return Narodmon-compatible numeric value for a Home Assistant state."""
        if state.entity_id.split(".", 1)[0] == "binary_sensor":
            if state.state == "on":
                return 1
            if state.state == "off":
                return 0
            return None

        try:
            return float(state.state)
        except (TypeError, ValueError):
            _LOGGER.debug("Skipping non-numeric Narodmon state: %s = %s", state.entity_id, state.state)
            return None


def _stable_id(value: str, prefix: str) -> str:
    """Return a stable Narodmon-compatible ID."""
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest().upper()
    return f"{prefix}{digest[:10]}"


def _device_name(device: dr.DeviceEntry | None, fallback: str) -> str:
    """Return a display name for a Home Assistant device."""
    if device is None:
        return fallback
    return device.name_by_user or device.name or fallback


def _log_server_reply(reply: str, transport: Transport) -> None:
    """Log Narodmon server reply with actionable diagnostics."""
    cleaned_reply = reply.strip()
    try:
        parsed = json.loads(cleaned_reply)
    except ValueError:
        _LOGGER.info("Narodmon server reply: %s", cleaned_reply)
        return

    error = parsed.get("error")
    if not error:
        _LOGGER.info("Narodmon server reply: %s", cleaned_reply)
        return

    if isinstance(error, str) and error.startswith("Protocol != "):
        expected_protocol = error.removeprefix("Protocol != ").strip()
        selected_protocol = _narodmon_protocol_name(transport)
        _LOGGER.error(
            "Narodmon rejected the packet: %s. The device on narodmon.ru is configured for protocol %s, "
            "but this Home Assistant integration entry is using %s. Open narodmon.ru, go to "
            "Sensors > Configure for this device and set the protocol/type to match the transport "
            "selected in Home Assistant.",
            cleaned_reply,
            expected_protocol,
            selected_protocol,
        )
        return

    _LOGGER.error("Narodmon rejected the packet: %s", cleaned_reply)


def _narodmon_protocol_name(transport: Transport) -> str:
    """Return Narodmon protocol name for a selected transport."""
    if transport == Transport.TCP:
        return "TCP"
    return "JSON"


def _send_tcp_payload(payload: str) -> str:
    """Send JSON payload to Narodmon using the blocking socket API."""
    with socket.create_connection((NARODMON_HOST, NARODMON_PORT), timeout=SOCKET_TIMEOUT) as sock:
        sock.sendall(f"{payload}\n".encode("utf-8"))
        return sock.recv(1024).decode("utf-8", errors="ignore")
