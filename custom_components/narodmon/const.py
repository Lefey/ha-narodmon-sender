"""Constants for the Narodmon integration."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "narodmon"

CONF_COORDINATES_ENTITY = "coordinates_entity"
CONF_DEVICE_MAC = "device_mac"
CONF_DEVICE_MODE = "device_mode"
CONF_DEVICE_NAME = "device_name"
CONF_GENERATE_MAC = "generate_mac"
CONF_SEND_INTERVAL_CHANGED = "send_interval_changed"
CONF_SEND_INTERVAL_FORCE = "send_interval_force"
CONF_TRANSPORT = "transport"

DEFAULT_SEND_INTERVAL_CHANGED = 360
DEFAULT_SEND_INTERVAL_FORCE = 1200
DEFAULT_VIRTUAL_DEVICE_NAME = "Home Assistant"
MAX_PACKET_SIZE = 4096

NARODMON_HOST = "narodmon.ru"
NARODMON_HTTP_URL = "http://narodmon.ru/json"
NARODMON_HTTPS_URL = "https://narodmon.ru/json"
NARODMON_PORT = 8283
SOCKET_TIMEOUT = 10


class DeviceMode(StrEnum):
    """Device grouping mode."""

    VIRTUAL = "virtual"
    HA_DEVICES = "ha_devices"


class Transport(StrEnum):
    """Supported JSON transport."""

    TCP = "tcp"
    HTTP = "http"
    HTTPS = "https"
