"""Services for Balena Cloud integration."""

from __future__ import annotations

import logging
from typing import Dict

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (DOMAIN, SERVICE_DISABLE_DEVICE_URL,
                    SERVICE_ENABLE_DEVICE_URL, SERVICE_REBOOT_DEVICE,
                    SERVICE_RESTART_APPLICATION, SERVICE_SHUTDOWN_DEVICE,
                    SERVICE_UPDATE_ENVIRONMENT)
from .coordinator import BalenaCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
RESTART_APPLICATION_SCHEMA = vol.Schema(
    {
        vol.Required("device_uuid"): cv.string,
        vol.Optional("service_name"): cv.string,
        vol.Optional("force", default=False): cv.boolean,
    }
)

REBOOT_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_uuid"): cv.string,
        vol.Optional("force", default=False): cv.boolean,
    }
)

SHUTDOWN_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_uuid"): cv.string,
        vol.Optional("force", default=False): cv.boolean,
    }
)

UPDATE_ENVIRONMENT_SCHEMA = vol.Schema(
    {
        vol.Required("device_uuid"): cv.string,
        vol.Required("variables"): dict,
    }
)

DEVICE_URL_SCHEMA = vol.Schema(
    {
        vol.Required("device_uuid"): cv.string,
    }
)


class BalenaCloudServiceHandler:
    """Handler for Balena Cloud services."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the service handler."""
        self.hass = hass
        self._coordinators: Dict[str, BalenaCloudDataUpdateCoordinator] = {}

    def register_coordinator(
        self, entry_id: str, coordinator: BalenaCloudDataUpdateCoordinator
    ) -> None:
        """Register a coordinator for service calls."""
        self._coordinators[entry_id] = coordinator

    def unregister_coordinator(self, entry_id: str) -> None:
        """Unregister a coordinator."""
        self._coordinators.pop(entry_id, None)

    def get_coordinator_for_device(
        self, device_uuid: str
    ) -> BalenaCloudDataUpdateCoordinator | None:
        """Get the coordinator that manages a specific device."""
        for coordinator in self._coordinators.values():
            if device_uuid in coordinator.devices:
                return coordinator
        return None

    async def async_setup_services(self) -> None:
        """Set up services for the integration."""
        _LOGGER.debug("Setting up Balena Cloud services")

        # Register all services
        services = [
            (
                SERVICE_RESTART_APPLICATION,
                self._handle_restart_application,
                RESTART_APPLICATION_SCHEMA,
            ),
            (SERVICE_REBOOT_DEVICE, self._handle_reboot_device, REBOOT_DEVICE_SCHEMA),
            (
                SERVICE_SHUTDOWN_DEVICE,
                self._handle_shutdown_device,
                SHUTDOWN_DEVICE_SCHEMA,
            ),
            (
                SERVICE_UPDATE_ENVIRONMENT,
                self._handle_update_environment,
                UPDATE_ENVIRONMENT_SCHEMA,
            ),
            (
                SERVICE_ENABLE_DEVICE_URL,
                self._handle_enable_device_url,
                DEVICE_URL_SCHEMA,
            ),
            (
                SERVICE_DISABLE_DEVICE_URL,
                self._handle_disable_device_url,
                DEVICE_URL_SCHEMA,
            ),
        ]

        for service_name, handler, schema in services:
            if not self.hass.services.has_service(DOMAIN, service_name):
                self.hass.services.async_register(
                    DOMAIN, service_name, handler, schema=schema
                )

        _LOGGER.info("Balena Cloud services registered")

    async def async_remove_services(self) -> None:
        """Remove services for the integration."""
        _LOGGER.debug("Removing Balena Cloud services")

        services = [
            SERVICE_RESTART_APPLICATION,
            SERVICE_REBOOT_DEVICE,
            SERVICE_SHUTDOWN_DEVICE,
            SERVICE_UPDATE_ENVIRONMENT,
            SERVICE_ENABLE_DEVICE_URL,
            SERVICE_DISABLE_DEVICE_URL,
        ]

        for service_name in services:
            if self.hass.services.has_service(DOMAIN, service_name):
                self.hass.services.async_remove(DOMAIN, service_name)

        _LOGGER.info("Balena Cloud services removed")

    async def _handle_restart_application(self, call: ServiceCall) -> None:
        """Handle restart application service call."""
        device_uuid = call.data["device_uuid"]
        service_name = call.data.get("service_name")
        # force is not used but kept for schema compatibility

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info(
                "Restarting application on device %s (service: %s)",
                device_uuid,
                service_name or "all",
            )

            success = await coordinator.async_restart_application(
                device_uuid, service_name
            )

            if success:
                _LOGGER.info(
                    "Successfully restarted application on device %s", device_uuid
                )
            else:
                _LOGGER.error("Failed to restart application on device %s", device_uuid)

        except Exception as err:
            _LOGGER.error(
                "Error restarting application on device %s: %s", device_uuid, err
            )

    async def _handle_reboot_device(self, call: ServiceCall) -> None:
        """Handle reboot device service call."""
        device_uuid = call.data["device_uuid"]
        # force is not used but kept for schema compatibility

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info("Rebooting device %s", device_uuid)

            success = await coordinator.async_reboot_device(device_uuid)

            if success:
                _LOGGER.info("Successfully initiated reboot for device %s", device_uuid)
            else:
                _LOGGER.error("Failed to reboot device %s", device_uuid)

        except Exception as err:
            _LOGGER.error("Error rebooting device %s: %s", device_uuid, err)

    async def _handle_shutdown_device(self, call: ServiceCall) -> None:
        """Handle shutdown device service call."""
        device_uuid = call.data["device_uuid"]
        # force is not used but kept for schema compatibility

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info("Shutting down device %s", device_uuid)

            success = await coordinator.async_shutdown_device(device_uuid)

            if success:
                _LOGGER.info(
                    "Successfully initiated shutdown for device %s", device_uuid
                )
            else:
                _LOGGER.error("Failed to shutdown device %s", device_uuid)

        except Exception as err:
            _LOGGER.error("Error shutting down device %s: %s", device_uuid, err)

    async def _handle_update_environment(self, call: ServiceCall) -> None:
        """Handle update environment variables service call."""
        device_uuid = call.data["device_uuid"]
        variables = call.data["variables"]

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info(
                "Updating environment variables for device %s: %s",
                device_uuid,
                list(variables.keys()),
            )

            success = await coordinator.async_update_environment_variables(
                device_uuid, variables
            )

            if success:
                _LOGGER.info(
                    "Successfully updated environment variables for device %s",
                    device_uuid,
                )
            else:
                _LOGGER.error(
                    "Failed to update environment variables for device %s", device_uuid
                )

        except Exception as err:
            _LOGGER.error(
                "Error updating environment variables for device %s: %s",
                device_uuid,
                err,
            )

    async def _handle_enable_device_url(self, call: ServiceCall) -> None:
        """Handle enable device URL service call."""
        device_uuid = call.data["device_uuid"]

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info("Enabling device URL for device %s", device_uuid)

            success = await coordinator.async_enable_device_url(device_uuid)

            if success:
                _LOGGER.info(
                    "Successfully enabled device URL for device %s", device_uuid
                )
            else:
                _LOGGER.error("Failed to enable device URL for device %s", device_uuid)

        except Exception as err:
            _LOGGER.error(
                "Error enabling device URL for device %s: %s", device_uuid, err
            )

    async def _handle_disable_device_url(self, call: ServiceCall) -> None:
        """Handle disable device URL service call."""
        device_uuid = call.data["device_uuid"]

        coordinator = self.get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("No coordinator found for device %s", device_uuid)
            return

        try:
            _LOGGER.info("Disabling device URL for device %s", device_uuid)

            success = await coordinator.async_disable_device_url(device_uuid)

            if success:
                _LOGGER.info(
                    "Successfully disabled device URL for device %s", device_uuid
                )
            else:
                _LOGGER.error("Failed to disable device URL for device %s", device_uuid)

        except Exception as err:
            _LOGGER.error(
                "Error disabling device URL for device %s: %s", device_uuid, err
            )


# Global service handler instance
_service_handler: BalenaCloudServiceHandler | None = None


def get_service_handler(hass: HomeAssistant) -> BalenaCloudServiceHandler:
    """Get the global service handler instance."""
    global _service_handler
    if _service_handler is None:
        _service_handler = BalenaCloudServiceHandler(hass)
    return _service_handler


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    service_handler = get_service_handler(hass)
    await service_handler.async_setup_services()


async def async_remove_services(hass: HomeAssistant) -> None:
    """Remove services for the integration."""
    service_handler = get_service_handler(hass)
    await service_handler.async_remove_services()
