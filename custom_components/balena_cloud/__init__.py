"""The Balena Cloud integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BalenaCloudDataUpdateCoordinator
from .services import get_service_handler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Balena Cloud from a config entry."""
    _LOGGER.debug("Setting up Balena Cloud integration")

    # Store configuration data
    hass.data.setdefault(DOMAIN, {})

    # Create the coordinator for API communication using balena-sdk
    coordinator = BalenaCloudDataUpdateCoordinator(
        hass,
        dict(entry.data),
        dict(entry.options),
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up services and advanced components
    await _async_setup_services(hass, entry.entry_id, coordinator)

    _LOGGER.info("Balena Cloud integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Balena Cloud integration")

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)

        # Remove services if this was the last entry
        if not hass.data[DOMAIN]:
            await _async_remove_services(hass)
        else:
            # Just unregister this coordinator from services
            service_handler = get_service_handler(hass)
            service_handler.unregister_coordinator(entry.entry_id)

    _LOGGER.info("Balena Cloud integration unloaded")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_setup_services(
    hass: HomeAssistant, entry_id: str, coordinator: BalenaCloudDataUpdateCoordinator
) -> None:
    """Set up services and advanced components for the integration."""
    # Get the global service handler
    service_handler = get_service_handler(hass)

    # Register the coordinator with the service handler
    service_handler.register_coordinator(entry_id, coordinator)

    # Set up services if this is the first integration entry
    if len(hass.data[DOMAIN]) == 1:
        await service_handler.async_setup_services()

    # Set up device cards and fleet overviews
    try:
        from .device_card import async_setup_device_cards
        from .fleet_overview import async_setup_fleet_overviews

        # Set up device cards for enhanced dashboard display
        await async_setup_device_cards(hass, coordinator)
        _LOGGER.debug("Device cards set up successfully")

        # Set up fleet overview entities
        fleet_overviews = await async_setup_fleet_overviews(hass, coordinator)
        _LOGGER.debug("Fleet overviews set up: %d fleets", len(fleet_overviews))

    except Exception as err:
        _LOGGER.warning("Failed to set up advanced components: %s", err)


async def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove services for the integration."""
    # Remove services when the last integration entry is unloaded
    service_handler = get_service_handler(hass)
    await service_handler.async_remove_services()
