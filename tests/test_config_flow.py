"""Config flow tests for Narodmon Sender integration."""

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.narodmon_sender.const import DOMAIN


@pytest.mark.asyncio
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test completing the user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM  # noqa: S101

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "device_id": "123",
            "api_key": "abc",
            "sensors": ["sensor.temp"],
            "interval": 300,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY  # noqa: S101
    assert result["data"]["device_id"] == "123"  # noqa: S101
