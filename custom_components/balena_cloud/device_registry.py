"""Device registry helpers for Balena Cloud integration."""

from __future__ import annotations

import inspect
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .models import BalenaDevice, BalenaFleet

_LOGGER = logging.getLogger(__name__)

# HA 2026.9 replaced the ``via_device`` identifier tuple with ``via_device_id``,
# which takes the parent device's registry id instead. Passing the old key to a
# core that has dropped it makes ``async_get_or_create`` raise whenever HA cannot
# pin the deprecated call on an integration stack frame, which silently drops the
# entity - so pick the key the running core actually accepts.
_VIA_DEVICE_ID_SUPPORTED = (
    "via_device_id"
    in inspect.signature(dr.DeviceRegistry.async_get_or_create).parameters
)


def async_get_fleet_device_info(fleet: BalenaFleet) -> DeviceInfo:
    """Get device info for a fleet."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"fleet_{fleet.id}")},
        name=fleet.display_name,
        manufacturer="Balena",
        model=fleet.device_type,
    )


async def async_ensure_fleet_device(
    hass: HomeAssistant, fleet: BalenaFleet, config_entry_id: str | None = None
) -> dr.DeviceEntry | None:
    """Ensure a fleet device exists in the device registry.

    Args:
        hass: Home Assistant instance
        fleet: Fleet to create device for
        config_entry_id: Config entry ID to associate with the device

    Returns None if the device registry is not available (e.g., in test environments).
    """
    try:
        device_registry = dr.async_get(hass)
        return device_registry.async_get_or_create(
            config_entry_id=config_entry_id,
            identifiers={(DOMAIN, f"fleet_{fleet.id}")},
            name=fleet.display_name,
            manufacturer="Balena",
            model=fleet.device_type,
        )
    except Exception as e:
        _LOGGER.debug("Could not create fleet device in registry: %s", e)
        return None


@callback
def async_get_balena_device_info(entity: Entity, device: BalenaDevice) -> DeviceInfo:
    """Get device info for a device, linked to the device registry fleet device.

    The fleet link is resolved here rather than baked in when the entity is
    built, because ``via_device_id`` takes the fleet device's registry id and so
    needs ``hass`` and the config entry, neither of which an entity has before it
    is added to a platform. Every platform's ``async_setup_entry`` registers the
    fleet devices before adding entities, so the lookup resolves by the time HA
    reads this.
    """
    device_info = DeviceInfo(
        identifiers={(DOMAIN, device.uuid)},
        name=device.display_name,
        manufacturer="Balena",
        model=device.device_type,
        sw_version=device.os_version,
        configuration_url=f"https://dashboard.balena-cloud.com/devices/{device.uuid}",
    )
    fleet_identifier = (DOMAIN, f"fleet_{device.fleet_id}")

    if not _VIA_DEVICE_ID_SUPPORTED:
        device_info["via_device"] = fleet_identifier
        return device_info

    config_entry = entity.platform.config_entry if entity.platform else None
    if entity.hass is None or config_entry is None:
        return device_info

    fleet_device = dr.async_get(entity.hass).async_get_device_by_identifier(
        fleet_identifier, config_entry.entry_id
    )
    if fleet_device is not None:
        device_info["via_device_id"] = fleet_device.id

    return device_info
