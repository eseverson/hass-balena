"""DataUpdateCoordinator for Balena Cloud integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BalenaCloudAPIClient, BalenaCloudAPIError
from .const import (
    CONF_API_TOKEN,
    CONF_FLEETS,
    CONF_INCLUDE_OFFLINE_DEVICES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .models import BalenaDevice, BalenaFleet

_LOGGER = logging.getLogger(__name__)


class BalenaCloudDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Balena Cloud API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_data: Dict[str, Any],
        options: Dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        self.api_token = config_data[CONF_API_TOKEN]
        self.selected_fleets = config_data.get(CONF_FLEETS, [])
        self.include_offline_devices = options.get(CONF_INCLUDE_OFFLINE_DEVICES, True)

        # Calculate update interval
        update_interval_seconds = options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
        )
        update_interval = timedelta(seconds=update_interval_seconds)

        # Initialize API client with balena-sdk
        self.api = BalenaCloudAPIClient(self.api_token)

        # Store fleets and devices data
        self.fleets: Dict[int, BalenaFleet] = {}
        self.devices: Dict[str, BalenaDevice] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            _LOGGER.debug("Updating Balena Cloud data")

            # Fetch fleets first
            await self._async_update_fleets()

            # Fetch devices for selected fleets
            await self._async_update_devices()

            # Return combined data
            return {
                "fleets": self.fleets,
                "devices": self.devices,
                "last_update": datetime.now(),
            }

        except BalenaCloudAPIError as err:
            _LOGGER.error("Error communicating with Balena Cloud API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error updating Balena Cloud data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _async_update_fleets(self) -> None:
        """Update fleet information."""
        try:
            _LOGGER.debug("Fetching fleets from Balena Cloud")
            fleets_data = await self.api.async_get_fleets()

            self.fleets.clear()
            for fleet_data in fleets_data:
                fleet = BalenaFleet.from_api_data(fleet_data)
                self.fleets[fleet.id] = fleet

            _LOGGER.debug("Found %d fleets", len(self.fleets))

        except Exception as err:
            _LOGGER.error("Failed to update fleets: %s", err)
            raise

    async def _async_update_devices(self) -> None:
        """Update device information."""
        try:
            _LOGGER.debug("Fetching devices from Balena Cloud")

            # If specific fleets are selected, fetch only those
            if self.selected_fleets:
                all_devices = []
                for fleet_id in self.selected_fleets:
                    if fleet_id in self.fleets:
                        fleet_devices = await self.api.async_get_devices(fleet_id)
                        all_devices.extend(fleet_devices)
            else:
                # Fetch all devices
                all_devices = await self.api.async_get_devices()

            # Process device data
            self.devices.clear()
            for device_data in all_devices:
                try:
                    # Get fleet name for the device
                    fleet_id = device_data.get("belongs_to__application", {}).get(
                        "__id"
                    )
                    fleet_name = ""
                    if fleet_id and fleet_id in self.fleets:
                        fleet_name = self.fleets[fleet_id].app_name

                    device = BalenaDevice.from_api_data(device_data, fleet_name)

                    # Skip offline devices if not included
                    if not self.include_offline_devices and not device.is_online:
                        continue

                    # Get device metrics if available
                    try:
                        status_data = await self.api.async_get_device_status(
                            device.uuid
                        )
                        if "metrics" in status_data and status_data["metrics"]:
                            device.update_metrics(status_data["metrics"])
                    except Exception as metrics_err:
                        _LOGGER.debug(
                            "Could not fetch metrics for device %s: %s",
                            device.uuid,
                            metrics_err,
                        )

                    self.devices[device.uuid] = device

                except Exception as device_err:
                    _LOGGER.warning("Failed to process device data: %s", device_err)
                    continue

            _LOGGER.debug("Found %d devices", len(self.devices))

        except Exception as err:
            _LOGGER.error("Failed to update devices: %s", err)
            raise

    async def async_restart_application(
        self, device_uuid: str, service_name: Optional[str] = None
    ) -> bool:
        """Restart application on a device."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        result = await self.api.async_restart_application(device_uuid, service_name)
        if result:
            # Trigger a data refresh to get updated status
            await self.async_request_refresh()

        return result

    async def async_reboot_device(self, device_uuid: str) -> bool:
        """Reboot a device."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        result = await self.api.async_reboot_device(device_uuid)
        if result:
            # Trigger a data refresh to get updated status
            await self.async_request_refresh()

        return result

    async def async_shutdown_device(self, device_uuid: str) -> bool:
        """Shutdown a device."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        result = await self.api.async_shutdown_device(device_uuid)
        if result:
            # Trigger a data refresh to get updated status
            await self.async_request_refresh()

        return result

    async def async_update_environment_variables(
        self, device_uuid: str, variables: Dict[str, str]
    ) -> bool:
        """Update environment variables for a device."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        result = await self.api.async_update_environment_variables(
            device_uuid, variables
        )
        if result:
            # Trigger a data refresh to get updated status
            await self.async_request_refresh()

        return result

    async def async_enable_device_url(self, device_uuid: str) -> bool:
        """Enable public device URL."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        return await self.api.async_enable_device_url(device_uuid)

    async def async_disable_device_url(self, device_uuid: str) -> bool:
        """Disable public device URL."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return False

        return await self.api.async_disable_device_url(device_uuid)

    async def async_get_device_url(self, device_uuid: str) -> Optional[str]:
        """Get public device URL."""
        if device_uuid not in self.devices:
            _LOGGER.error("Device %s not found", device_uuid)
            return None

        return await self.api.async_get_device_url(device_uuid)

    def get_device(self, device_uuid: str) -> Optional[BalenaDevice]:
        """Get device by UUID."""
        return self.devices.get(device_uuid)

    def get_fleet(self, fleet_id: int) -> Optional[BalenaFleet]:
        """Get fleet by ID."""
        return self.fleets.get(fleet_id)

    def get_devices_by_fleet(self, fleet_id: int) -> List[BalenaDevice]:
        """Get all devices for a specific fleet."""
        return [
            device for device in self.devices.values() if device.fleet_id == fleet_id
        ]

    @property
    def online_devices_count(self) -> int:
        """Get count of online devices."""
        return sum(1 for device in self.devices.values() if device.is_online)

    @property
    def total_devices_count(self) -> int:
        """Get total count of devices."""
        return len(self.devices)

    @property
    def fleets_count(self) -> int:
        """Get count of fleets."""
        return len(self.fleets)
