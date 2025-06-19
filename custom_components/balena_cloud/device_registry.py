"""Device registry helpers for Balena Cloud integration."""

from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .models import BalenaFleet

_LOGGER = logging.getLogger(__name__)


def async_get_fleet_device_info(fleet: BalenaFleet) -> DeviceInfo:
    """Get device info for a fleet."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"fleet_{fleet.id}")},
        name=fleet.display_name,
        manufacturer="Balena",
        model=fleet.device_type,
    )


async def async_ensure_fleet_device(
    hass: HomeAssistant, fleet: BalenaFleet
) -> dr.DeviceEntry | None:
    """Ensure a fleet device exists in the device registry.

    Returns None if the device registry is not available (e.g., in test environments).
    """
    try:
        device_registry = dr.async_get(hass)
        return device_registry.async_get_or_create(
            config_entry_id=None,  # Will be set by the config entry
            identifiers={(DOMAIN, f"fleet_{fleet.id}")},
            name=fleet.display_name,
            manufacturer="Balena",
            model=fleet.device_type,
        )
    except Exception as e:
        _LOGGER.debug("Could not create fleet device in registry: %s", e)
        return None