"""The Balena Cloud integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import BalenaCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Balena Cloud from a config entry."""
    _LOGGER.debug("Setting up Balena Cloud integration")

    hass.data.setdefault(DOMAIN, {})

    # Create and store coordinator
    coordinator = BalenaCloudDataUpdateCoordinator(
        hass, entry, dict(entry.data), dict(entry.options)
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup services
    from .services import async_setup_services

    await async_setup_services(hass)

    _LOGGER.info("Balena Cloud integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Balena Cloud integration")

    # Check if entry is actually loaded before trying to unload
    if entry.entry_id not in hass.data.get(DOMAIN, {}):
        _LOGGER.debug("Entry %s not loaded, skipping unload", entry.entry_id)
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.info("Balena Cloud integration unloaded")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow the user to remove a device that no longer exists in Balena Cloud."""
    coordinator: BalenaCloudDataUpdateCoordinator | None = hass.data.get(
        DOMAIN, {}
    ).get(config_entry.entry_id)

    if coordinator is None:
        return True

    for domain, identifier in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        if identifier.startswith("fleet_"):
            try:
                fleet_id = int(identifier.removeprefix("fleet_"))
            except ValueError:
                continue
            if fleet_id in coordinator.fleets:
                return False
        else:
            if identifier in coordinator.devices:
                return False

    return True
