"""Device card support for Balena Cloud integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .coordinator import BalenaCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_device_cards(
    hass: HomeAssistant, coordinator: BalenaCloudDataUpdateCoordinator
) -> None:
    """Set up device cards for enhanced dashboard display."""
    # This is a placeholder for future device card functionality
    # Device cards would provide enhanced visualization in the dashboard
    _LOGGER.debug("Device cards setup placeholder - feature not yet implemented")
    pass
