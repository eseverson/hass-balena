"""Support for Balena Cloud switches."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_TYPE,
    ATTR_DEVICE_UUID,
    ATTR_FLEET_NAME,
    DOMAIN,
)
from .coordinator import BalenaCloudDataUpdateCoordinator
from .device_registry import async_ensure_fleet_device
from .models import BalenaDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Balena Cloud switches from a config entry."""
    coordinator: BalenaCloudDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    # Ensure fleet devices exist in the device registry
    for fleet in coordinator.fleets.values():
        await async_ensure_fleet_device(hass, fleet)

    switches = []
    for device_uuid, device in coordinator.devices.items():
        switches.append(BalenaCloudPublicUrlSwitch(coordinator, device_uuid))

    async_add_entities(switches)


class BalenaCloudPublicUrlSwitch(
    CoordinatorEntity[BalenaCloudDataUpdateCoordinator], SwitchEntity
):
    """Toggle for device public URL."""

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the public URL switch."""
        super().__init__(coordinator)
        self._device_uuid = device_uuid
        self._attr_unique_id = f"{device_uuid}_public_url"
        self._attr_name = "Public URL"
        self._attr_icon = "mdi:web"
        self._cached_url = None

    @property
    def device(self) -> BalenaDevice | None:
        """Return the device."""
        return self.coordinator.get_device(self._device_uuid)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.device is not None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self.device:
            return f"{self.device.display_name} Public URL"
        return "Unknown Device Public URL"

    @property
    def is_on(self) -> bool | None:
        """Return true if public URL is enabled."""
        # We determine this by checking if we can get a URL
        # This will be updated during coordinator refresh
        return self._cached_url is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable public device URL."""
        if not self.device:
            _LOGGER.error("Device not found for public URL switch %s", self._attr_unique_id)
            return

        _LOGGER.info("Enabling public URL for device %s", self.device.display_name)

        try:
            success = await self.coordinator.async_enable_device_url(self._device_uuid)
            if success:
                # Get the URL and cache it
                url = await self.coordinator.async_get_device_url(self._device_uuid)
                self._cached_url = url
                _LOGGER.info(
                    "Successfully enabled public URL for device %s: %s",
                    self.device.display_name,
                    url or "URL not immediately available"
                )
                self.async_write_ha_state()
            else:
                _LOGGER.error(
                    "Failed to enable public URL for device %s",
                    self.device.display_name,
                )
        except Exception as err:
            _LOGGER.error(
                "Error enabling public URL for device %s: %s",
                self.device.display_name,
                err,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable public device URL."""
        if not self.device:
            _LOGGER.error("Device not found for public URL switch %s", self._attr_unique_id)
            return

        _LOGGER.info("Disabling public URL for device %s", self.device.display_name)

        try:
            success = await self.coordinator.async_disable_device_url(self._device_uuid)
            if success:
                self._cached_url = None
                _LOGGER.info(
                    "Successfully disabled public URL for device %s",
                    self.device.display_name,
                )
                self.async_write_ha_state()
            else:
                _LOGGER.error(
                    "Failed to disable public URL for device %s",
                    self.device.display_name,
                )
        except Exception as err:
            _LOGGER.error(
                "Error disabling public URL for device %s: %s",
                self.device.display_name,
                err,
            )

    async def async_update(self) -> None:
        """Update the switch state by checking current URL."""
        try:
            url = await self.coordinator.async_get_device_url(self._device_uuid)
            self._cached_url = url
        except Exception as err:
            _LOGGER.debug("Could not update public URL state for %s: %s", self._device_uuid, err)
            # Don't change cached state on error

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_DEVICE_UUID: self.device.uuid if self.device else None,
            ATTR_DEVICE_NAME: self.device.device_name if self.device else None,
            ATTR_DEVICE_TYPE: self.device.device_type if self.device else None,
            ATTR_FLEET_NAME: self.device.fleet_name if self.device else None,
        }
        if self._cached_url:
            attrs["public_url"] = self._cached_url
        return {k: v for k, v in attrs.items() if v is not None}

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info."""
        if not (device := self.device):
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, device.uuid)},
            name=device.display_name,
            manufacturer="Balena",
            model=device.device_type,
            sw_version=device.os_version,
            configuration_url=f"https://dashboard.balena-cloud.com/devices/{device.uuid}",
            via_device=(DOMAIN, f"fleet_{device.fleet_id}"),
        )
