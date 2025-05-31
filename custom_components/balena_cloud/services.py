"""Service handlers for Balena Cloud integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_RESTART_APPLICATION,
    SERVICE_REBOOT_DEVICE,
    SERVICE_SHUTDOWN_DEVICE,
    SERVICE_UPDATE_ENVIRONMENT,
    SERVICE_ENABLE_DEVICE_URL,
    SERVICE_DISABLE_DEVICE_URL,
)
from .coordinator import BalenaCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
RESTART_APPLICATION_SCHEMA = vol.Schema({
    vol.Required("device_uuid"): cv.string,
    vol.Optional("service_name"): cv.string,
    vol.Optional("confirm", default=False): bool,
})

REBOOT_DEVICE_SCHEMA = vol.Schema({
    vol.Required("device_uuid"): cv.string,
    vol.Optional("confirm", default=False): bool,
    vol.Optional("force", default=False): bool,
})

SHUTDOWN_DEVICE_SCHEMA = vol.Schema({
    vol.Required("device_uuid"): cv.string,
    vol.Optional("confirm", default=False): bool,
    vol.Optional("force", default=False): bool,
})

UPDATE_ENVIRONMENT_SCHEMA = vol.Schema({
    vol.Required("device_uuid"): cv.string,
    vol.Required("variables"): dict,
    vol.Optional("merge", default=True): bool,
})

DEVICE_URL_SCHEMA = vol.Schema({
    vol.Required("device_uuid"): cv.string,
})

BULK_RESTART_SCHEMA = vol.Schema({
    vol.Optional("device_uuids"): [cv.string],
    vol.Optional("fleet_id"): cv.positive_int,
    vol.Optional("service_name"): cv.string,
    vol.Optional("confirm", default=False): bool,
})

BULK_REBOOT_SCHEMA = vol.Schema({
    vol.Optional("device_uuids"): [cv.string],
    vol.Optional("fleet_id"): cv.positive_int,
    vol.Optional("confirm", default=False): bool,
    vol.Optional("force", default=False): bool,
})


class BalenaCloudServiceHandler:
    """Handle service calls for Balena Cloud integration."""

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

    async def async_setup_services(self) -> None:
        """Set up services for the integration."""
        # Individual device services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_RESTART_APPLICATION,
            self._handle_restart_application,
            schema=RESTART_APPLICATION_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REBOOT_DEVICE,
            self._handle_reboot_device,
            schema=REBOOT_DEVICE_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SHUTDOWN_DEVICE,
            self._handle_shutdown_device,
            schema=SHUTDOWN_DEVICE_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_ENVIRONMENT,
            self._handle_update_environment,
            schema=UPDATE_ENVIRONMENT_SCHEMA,
        )

        # Device URL management services
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_DEVICE_URL,
            self._handle_enable_device_url,
            schema=DEVICE_URL_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_DISABLE_DEVICE_URL,
            self._handle_disable_device_url,
            schema=DEVICE_URL_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            "get_device_url",
            self._handle_get_device_url,
            schema=DEVICE_URL_SCHEMA,
        )

        # Bulk operation services
        self.hass.services.async_register(
            DOMAIN,
            "bulk_restart_applications",
            self._handle_bulk_restart,
            schema=BULK_RESTART_SCHEMA,
        )

        self.hass.services.async_register(
            DOMAIN,
            "bulk_reboot_devices",
            self._handle_bulk_reboot,
            schema=BULK_REBOOT_SCHEMA,
        )

        # Fleet management services
        self.hass.services.async_register(
            DOMAIN,
            "restart_fleet",
            self._handle_restart_fleet,
            schema=vol.Schema({
                vol.Required("fleet_id"): cv.positive_int,
                vol.Optional("service_name"): cv.string,
                vol.Optional("confirm", default=False): bool,
            }),
        )

        self.hass.services.async_register(
            DOMAIN,
            "get_fleet_health",
            self._handle_get_fleet_health,
            schema=vol.Schema({
                vol.Required("fleet_id"): cv.positive_int,
            }),
        )

        _LOGGER.info("Balena Cloud services registered")

    async def async_remove_services(self) -> None:
        """Remove services for the integration."""
        services = [
            SERVICE_RESTART_APPLICATION,
            SERVICE_REBOOT_DEVICE,
            SERVICE_SHUTDOWN_DEVICE,
            SERVICE_UPDATE_ENVIRONMENT,
            SERVICE_ENABLE_DEVICE_URL,
            SERVICE_DISABLE_DEVICE_URL,
            "get_device_url",
            "bulk_restart_applications",
            "bulk_reboot_devices",
            "restart_fleet",
            "get_fleet_health",
        ]

        for service in services:
            if self.hass.services.has_service(DOMAIN, service):
                self.hass.services.async_remove(DOMAIN, service)

        _LOGGER.info("Balena Cloud services removed")

    def _get_coordinator_for_device(self, device_uuid: str) -> Optional[BalenaCloudDataUpdateCoordinator]:
        """Find coordinator that manages the specified device."""
        for coordinator in self._coordinators.values():
            if device_uuid in coordinator.devices:
                return coordinator
        return None

    def _get_all_coordinators(self) -> List[BalenaCloudDataUpdateCoordinator]:
        """Get all registered coordinators."""
        return list(self._coordinators.values())

    async def _handle_restart_application(self, call: ServiceCall) -> None:
        """Handle restart application service call."""
        device_uuid = call.data["device_uuid"]
        service_name = call.data.get("service_name")
        confirm = call.data.get("confirm", False)

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        if not confirm:
            _LOGGER.warning(
                "Restart application for %s requires confirmation. Use confirm=true",
                device.display_name,
            )
            return

        _LOGGER.info(
            "Restarting application on device %s%s",
            device.display_name,
            f" (service: {service_name})" if service_name else "",
        )

        success = await coordinator.async_restart_application(device_uuid, service_name)
        if success:
            _LOGGER.info("Successfully restarted application on %s", device.display_name)
        else:
            _LOGGER.error("Failed to restart application on %s", device.display_name)

    async def _handle_reboot_device(self, call: ServiceCall) -> None:
        """Handle reboot device service call."""
        device_uuid = call.data["device_uuid"]
        confirm = call.data.get("confirm", False)
        force = call.data.get("force", False)

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        if not confirm:
            _LOGGER.warning(
                "Reboot device %s requires confirmation. Use confirm=true",
                device.display_name,
            )
            return

        _LOGGER.info("Rebooting device %s", device.display_name)

        success = await coordinator.async_reboot_device(device_uuid)
        if success:
            _LOGGER.info("Successfully rebooted device %s", device.display_name)
        else:
            _LOGGER.error("Failed to reboot device %s", device.display_name)

    async def _handle_shutdown_device(self, call: ServiceCall) -> None:
        """Handle shutdown device service call."""
        device_uuid = call.data["device_uuid"]
        confirm = call.data.get("confirm", False)
        force = call.data.get("force", False)

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        if not confirm:
            _LOGGER.warning(
                "Shutdown device %s requires confirmation. Use confirm=true",
                device.display_name,
            )
            return

        _LOGGER.info("Shutting down device %s", device.display_name)

        success = await coordinator.async_shutdown_device(device_uuid)
        if success:
            _LOGGER.info("Successfully shutdown device %s", device.display_name)
        else:
            _LOGGER.error("Failed to shutdown device %s", device.display_name)

    async def _handle_enable_device_url(self, call: ServiceCall) -> None:
        """Handle enable device URL service call."""
        device_uuid = call.data["device_uuid"]

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        _LOGGER.info("Enabling device URL for %s", device.display_name)

        success = await coordinator.async_enable_device_url(device_uuid)
        if success:
            # Get the URL to display it
            url = await coordinator.async_get_device_url(device_uuid)
            _LOGGER.info(
                "Successfully enabled device URL for %s: %s",
                device.display_name,
                url or "URL will be available shortly"
            )
        else:
            _LOGGER.error("Failed to enable device URL for %s", device.display_name)

    async def _handle_disable_device_url(self, call: ServiceCall) -> None:
        """Handle disable device URL service call."""
        device_uuid = call.data["device_uuid"]

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        _LOGGER.info("Disabling device URL for %s", device.display_name)

        success = await coordinator.async_disable_device_url(device_uuid)
        if success:
            _LOGGER.info("Successfully disabled device URL for %s", device.display_name)
        else:
            _LOGGER.error("Failed to disable device URL for %s", device.display_name)

    async def _handle_get_device_url(self, call: ServiceCall) -> None:
        """Handle get device URL service call."""
        device_uuid = call.data["device_uuid"]

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        url = await coordinator.async_get_device_url(device_uuid)
        if url:
            _LOGGER.info("Device URL for %s: %s", device.display_name, url)
            # You could also fire an event or update a sensor here
            self.hass.bus.async_fire(
                "balena_cloud_device_url",
                {
                    "device_uuid": device_uuid,
                    "device_name": device.display_name,
                    "url": url,
                }
            )
        else:
            _LOGGER.info("No device URL configured for %s", device.display_name)

    async def _handle_update_environment(self, call: ServiceCall) -> None:
        """Handle update environment variables service call."""
        device_uuid = call.data["device_uuid"]
        variables = call.data["variables"]
        merge = call.data.get("merge", True)

        coordinator = self._get_coordinator_for_device(device_uuid)
        if not coordinator:
            _LOGGER.error("Device %s not found in any coordinator", device_uuid)
            return

        device = coordinator.get_device(device_uuid)
        if not device:
            _LOGGER.error("Device %s not found", device_uuid)
            return

        _LOGGER.info(
            "Updating environment variables for device %s (%s mode)",
            device.display_name,
            "merge" if merge else "replace",
        )

        success = await coordinator.async_update_environment_variables(device_uuid, variables)
        if success:
            _LOGGER.info("Successfully updated environment variables for %s", device.display_name)
        else:
            _LOGGER.error("Failed to update environment variables for %s", device.display_name)

    async def _handle_bulk_restart(self, call: ServiceCall) -> None:
        """Handle bulk restart applications service call."""
        device_uuids = call.data.get("device_uuids")
        fleet_id = call.data.get("fleet_id")
        service_name = call.data.get("service_name")
        confirm = call.data.get("confirm", False)

        if not confirm:
            _LOGGER.warning("Bulk restart requires confirmation. Use confirm=true")
            return

        if not device_uuids and not fleet_id:
            _LOGGER.error("Either device_uuids or fleet_id must be specified")
            return

        target_devices = []

        # Collect target devices
        if device_uuids:
            for device_uuid in device_uuids:
                coordinator = self._get_coordinator_for_device(device_uuid)
                if coordinator:
                    device = coordinator.get_device(device_uuid)
                    if device:
                        target_devices.append((coordinator, device))
        elif fleet_id:
            for coordinator in self._get_all_coordinators():
                fleet_devices = coordinator.get_devices_by_fleet(fleet_id)
                for device in fleet_devices:
                    target_devices.append((coordinator, device))

        if not target_devices:
            _LOGGER.warning("No devices found for bulk restart operation")
            return

        _LOGGER.info(
            "Starting bulk restart for %d devices%s",
            len(target_devices),
            f" (service: {service_name})" if service_name else "",
        )

        successful = 0
        failed = 0

        for coordinator, device in target_devices:
            if device.is_online:
                success = await coordinator.async_restart_application(device.uuid, service_name)
                if success:
                    successful += 1
                    _LOGGER.debug("Restarted application on %s", device.display_name)
                else:
                    failed += 1
                    _LOGGER.warning("Failed to restart application on %s", device.display_name)
            else:
                failed += 1
                _LOGGER.warning("Skipped offline device %s", device.display_name)

        _LOGGER.info(
            "Bulk restart completed: %d successful, %d failed",
            successful,
            failed,
        )

    async def _handle_bulk_reboot(self, call: ServiceCall) -> None:
        """Handle bulk reboot devices service call."""
        device_uuids = call.data.get("device_uuids")
        fleet_id = call.data.get("fleet_id")
        confirm = call.data.get("confirm", False)
        force = call.data.get("force", False)

        if not confirm:
            _LOGGER.warning("Bulk reboot requires confirmation. Use confirm=true")
            return

        if not device_uuids and not fleet_id:
            _LOGGER.error("Either device_uuids or fleet_id must be specified")
            return

        target_devices = []

        # Collect target devices
        if device_uuids:
            for device_uuid in device_uuids:
                coordinator = self._get_coordinator_for_device(device_uuid)
                if coordinator:
                    device = coordinator.get_device(device_uuid)
                    if device:
                        target_devices.append((coordinator, device))
        elif fleet_id:
            for coordinator in self._get_all_coordinators():
                fleet_devices = coordinator.get_devices_by_fleet(fleet_id)
                for device in fleet_devices:
                    target_devices.append((coordinator, device))

        if not target_devices:
            _LOGGER.warning("No devices found for bulk reboot operation")
            return

        _LOGGER.info("Starting bulk reboot for %d devices", len(target_devices))

        successful = 0
        failed = 0

        for coordinator, device in target_devices:
            if device.is_online and (force or not device.is_updating):
                success = await coordinator.async_reboot_device(device.uuid)
                if success:
                    successful += 1
                    _LOGGER.debug("Rebooted device %s", device.display_name)
                else:
                    failed += 1
                    _LOGGER.warning("Failed to reboot device %s", device.display_name)
            else:
                failed += 1
                reason = "offline" if not device.is_online else "updating"
                _LOGGER.warning("Skipped %s device %s", reason, device.display_name)

        _LOGGER.info(
            "Bulk reboot completed: %d successful, %d failed",
            successful,
            failed,
        )

    async def _handle_restart_fleet(self, call: ServiceCall) -> None:
        """Handle restart fleet service call."""
        fleet_id = call.data["fleet_id"]
        service_name = call.data.get("service_name")
        confirm = call.data.get("confirm", False)

        if not confirm:
            _LOGGER.warning("Fleet restart requires confirmation. Use confirm=true")
            return

        target_devices = []
        for coordinator in self._get_all_coordinators():
            fleet_devices = coordinator.get_devices_by_fleet(fleet_id)
            for device in fleet_devices:
                if device.is_online:
                    target_devices.append((coordinator, device))

        if not target_devices:
            _LOGGER.warning("No online devices found in fleet %d", fleet_id)
            return

        fleet_name = None
        for coordinator in self._get_all_coordinators():
            fleet = coordinator.get_fleet(fleet_id)
            if fleet:
                fleet_name = fleet.app_name
                break

        _LOGGER.info(
            "Restarting fleet %s (%d devices)%s",
            fleet_name or f"ID {fleet_id}",
            len(target_devices),
            f" (service: {service_name})" if service_name else "",
        )

        successful = 0
        failed = 0

        for coordinator, device in target_devices:
            success = await coordinator.async_restart_application(device.uuid, service_name)
            if success:
                successful += 1
            else:
                failed += 1

        _LOGGER.info(
            "Fleet restart completed: %d successful, %d failed",
            successful,
            failed,
        )

    async def _handle_get_fleet_health(self, call: ServiceCall) -> None:
        """Handle get fleet health service call."""
        fleet_id = call.data["fleet_id"]

        health_data = {
            "fleet_id": fleet_id,
            "total_devices": 0,
            "online_devices": 0,
            "healthy_devices": 0,
            "warning_devices": 0,
            "critical_devices": 0,
            "device_details": [],
        }

        for coordinator in self._get_all_coordinators():
            fleet_devices = coordinator.get_devices_by_fleet(fleet_id)
            health_data["total_devices"] += len(fleet_devices)

            for device in fleet_devices:
                if device.is_online:
                    health_data["online_devices"] += 1

                # Simple health assessment
                device_health = "healthy"
                if not device.is_online:
                    device_health = "critical"
                elif device.metrics:
                    if (device.metrics.cpu_percentage and device.metrics.cpu_percentage > 90) or \
                       (device.metrics.memory_percentage and device.metrics.memory_percentage > 90) or \
                       (device.metrics.storage_percentage and device.metrics.storage_percentage > 95):
                        device_health = "critical"
                    elif (device.metrics.cpu_percentage and device.metrics.cpu_percentage > 75) or \
                         (device.metrics.memory_percentage and device.metrics.memory_percentage > 80) or \
                         (device.metrics.storage_percentage and device.metrics.storage_percentage > 85):
                        device_health = "warning"

                if device_health == "healthy":
                    health_data["healthy_devices"] += 1
                elif device_health == "warning":
                    health_data["warning_devices"] += 1
                else:
                    health_data["critical_devices"] += 1

                health_data["device_details"].append({
                    "uuid": device.uuid,
                    "name": device.display_name,
                    "health": device_health,
                    "online": device.is_online,
                    "status": device.status,
                })

        # Send response as event
        self.hass.bus.async_fire(
            f"{DOMAIN}_fleet_health_response",
            health_data,
        )

        _LOGGER.info(
            "Fleet %d health: %d total, %d online, %d healthy, %d warning, %d critical",
            fleet_id,
            health_data["total_devices"],
            health_data["online_devices"],
            health_data["healthy_devices"],
            health_data["warning_devices"],
            health_data["critical_devices"],
        )


# Global service handler instance
_service_handler: Optional[BalenaCloudServiceHandler] = None


def get_service_handler(hass: HomeAssistant) -> BalenaCloudServiceHandler:
    """Get or create the global service handler."""
    global _service_handler
    if _service_handler is None:
        _service_handler = BalenaCloudServiceHandler(hass)
    return _service_handler