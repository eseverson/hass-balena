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

    # For now, we don't have any switches to create
    # This platform is prepared for future use when we add toggleable features
    entities: list[BalenaCloudSwitchEntity] = []

    # Example of future switch types:
    # - Maintenance mode toggle
    # - Service enable/disable switches
    # - Remote access toggle

    async_add_entities(entities)


class BalenaCloudSwitchEntity(
    CoordinatorEntity[BalenaCloudDataUpdateCoordinator], SwitchEntity
):
    """Representation of a Balena Cloud switch."""

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        device_uuid: str,
        switch_type: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_uuid = device_uuid
        self._switch_type = switch_type
        self._attr_unique_id = f"{device_uuid}_{switch_type}"

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
            return f"{self.device.display_name} {self._switch_type.title()}"
        return f"Unknown Device {self._switch_type.title()}"

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        # This will be implemented based on the specific switch type
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # This will be implemented based on the specific switch type
        pass

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # This will be implemented based on the specific switch type
        pass

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.device:
            return {}

        return {
            ATTR_DEVICE_UUID: self.device.uuid,
            ATTR_DEVICE_NAME: self.device.device_name,
            ATTR_DEVICE_TYPE: self.device.device_type,
            ATTR_FLEET_NAME: self.device.fleet_name,
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information about this entity."""
        if not self.device:
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, self.device.uuid)},
            name=self.device.display_name,
            manufacturer="Balena",
            model=self.device.device_type,
            sw_version=self.device.os_version,
            configuration_url=f"https://dashboard.balena-cloud.com/devices/{self.device.uuid}",
            via_device=(DOMAIN, f"fleet_{self.device.fleet_id}"),
        )