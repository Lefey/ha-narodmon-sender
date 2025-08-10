"""Constants for Narodmon Sender integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "narodmon_sender"
API_URL = "https://narodmon.ru/post"

CONF_DEVICE_ID = "device_id"
CONF_SENSORS = "sensors"
CONF_INTERVAL = "interval"
