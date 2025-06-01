"""Support for Balena Cloud buttons."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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
    ICON_REBOOT,
    ICON_RESTART,
)
from .coordinator import BalenaCloudDataUpdateCoordinator
from .models import BalenaDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class BalenaCloudButtonEntityDescriptionMixin:
    """Mixin for required keys."""

    action_fn: Callable[[BalenaCloudDataUpdateCoordinator, str], Any]


@dataclass
class BalenaCloudButtonEntityDescription(
    ButtonEntityDescription, BalenaCloudButtonEntityDescriptionMixin
):
    """Describes Balena Cloud button entity."""


BUTTON_TYPES: tuple[BalenaCloudButtonEntityDescription, ...] = (
    BalenaCloudButtonEntityDescription(
        key="restart_application",
        name="Restart Application",
        icon=ICON_RESTART,
        action_fn=lambda coordinator, device_uuid: coordinator.async_restart_application(
            device_uuid
        ),
    ),
    BalenaCloudButtonEntityDescription(
        key="reboot_device",
        name="Reboot Device",
        icon=ICON_REBOOT,
        action_fn=lambda coordinator, device_uuid: coordinator.async_reboot_device(
            device_uuid
        ),
    ),
    BalenaCloudButtonEntityDescription(
        key="shutdown_device",
        name="Shutdown Device",
        icon="mdi:power-off",
        action_fn=lambda coordinator, device_uuid: coordinator.async_shutdown_device(
            device_uuid
        ),
    ),
    BalenaCloudButtonEntityDescription(
        key="enable_device_url",
        name="Enable Public Device URL",
        icon="mdi:web",
        action_fn=lambda coordinator, device_uuid: coordinator.async_enable_device_url(
            device_uuid
        ),
    ),
    BalenaCloudButtonEntityDescription(
        key="disable_device_url",
        name="Disable Public Device URL",
        icon="mdi:web-off",
        action_fn=lambda coordinator, device_uuid: coordinator.async_disable_device_url(
            device_uuid
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Balena Cloud buttons from a config entry."""
    coordinator: BalenaCloudDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[BalenaCloudButtonEntity] = []

    for device_uuid, device in coordinator.devices.items():
        for description in BUTTON_TYPES:
            entities.append(
                BalenaCloudButtonEntity(
                    coordinator=coordinator,
                    description=description,
                    device_uuid=device_uuid,
                )
            )

    async_add_entities(entities)


class BalenaCloudButtonEntity(
    CoordinatorEntity[BalenaCloudDataUpdateCoordinator], ButtonEntity
):
    """Representation of a Balena Cloud button."""

    entity_description: BalenaCloudButtonEntityDescription

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        description: BalenaCloudButtonEntityDescription,
        device_uuid: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_uuid = device_uuid
        self._attr_unique_id = f"{device_uuid}_{description.key}"

    @property
    def device(self) -> BalenaDevice | None:
        """Return the device."""
        return self.coordinator.get_device(self._device_uuid)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.device is not None and self.device.is_online

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self.device:
            return f"{self.device.display_name} {self.entity_description.name}"
        return f"Unknown Device {self.entity_description.name}"

    async def async_press(self) -> None:
        """Handle the button press."""
        if not self.device:
            _LOGGER.error("Device not found for button %s", self._attr_unique_id)
            return

        _LOGGER.info(
            "Executing %s for device %s",
            self.entity_description.name,
            self.device.display_name,
        )

        try:
            success = await self.entity_description.action_fn(
                self.coordinator, self._device_uuid
            )
            if success:
                _LOGGER.info(
                    "Successfully executed %s for device %s",
                    self.entity_description.name,
                    self.device.display_name,
                )

                # For device URL operations, also get and log the URL
                if self.entity_description.key == "enable_device_url":
                    url = await self.coordinator.async_get_device_url(self._device_uuid)
                    if url:
                        _LOGGER.info(
                            "Device URL for %s: %s", self.device.display_name, url
                        )
            else:
                _LOGGER.error(
                    "Failed to execute %s for device %s",
                    self.entity_description.name,
                    self.device.display_name,
                )
        except Exception as err:
            _LOGGER.error(
                "Error executing %s for device %s: %s",
                self.entity_description.name,
                self.device.display_name,
                err,
            )

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
