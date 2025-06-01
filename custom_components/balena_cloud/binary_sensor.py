"""Support for Balena Cloud binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
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
    ATTR_IP_ADDRESS,
    ATTR_LAST_SEEN,
    ATTR_MAC_ADDRESS,
    ATTR_OS_VERSION,
    ATTR_SUPERVISOR_VERSION,
    DOMAIN,
    ICON_OFFLINE,
    ICON_ONLINE,
)
from .coordinator import BalenaCloudDataUpdateCoordinator
from .models import BalenaDevice

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalenaCloudBinarySensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[BalenaDevice], bool | None]


@dataclass(frozen=True)
class BalenaCloudBinarySensorEntityDescription(
    BinarySensorEntityDescription, BalenaCloudBinarySensorEntityDescriptionMixin
):
    """Describes Balena Cloud binary sensor entity."""

    attr_fn: Callable[[BalenaDevice], dict[str, Any]] | None = None


BINARY_SENSOR_TYPES: tuple[BalenaCloudBinarySensorEntityDescription, ...] = (
    BalenaCloudBinarySensorEntityDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon=ICON_ONLINE,
        value_fn=lambda device: device.is_online,
        attr_fn=lambda device: {
            "status": device.status,
            ATTR_LAST_SEEN: device.last_seen.isoformat() if device.last_seen else None,
        },
    ),
    BalenaCloudBinarySensorEntityDescription(
        key="updating",
        name="Updating",
        device_class=BinarySensorDeviceClass.UPDATE,
        icon="mdi:update",
        value_fn=lambda device: device.is_updating,
        attr_fn=lambda device: {
            "status": device.status,
            "provisioning_progress": device.provisioning_progress,
            "provisioning_state": device.provisioning_state,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Balena Cloud binary sensors from a config entry."""
    coordinator: BalenaCloudDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[BalenaCloudBinarySensorEntity] = []

    for device_uuid, device in coordinator.devices.items():
        for description in BINARY_SENSOR_TYPES:
            entities.append(
                BalenaCloudBinarySensorEntity(
                    coordinator=coordinator,
                    description=description,
                    device_uuid=device_uuid,
                )
            )

    async_add_entities(entities)


class BalenaCloudBinarySensorEntity(
    CoordinatorEntity[BalenaCloudDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Balena Cloud binary sensor."""

    entity_description: BalenaCloudBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        description: BalenaCloudBinarySensorEntityDescription,
        device_uuid: str,
    ) -> None:
        """Initialize the binary sensor."""
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
        return super().available and self.device is not None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self.device:
            return f"{self.device.display_name} {self.entity_description.name}"
        return f"Unknown Device {self.entity_description.name}"

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if self.device:
            return self.entity_description.value_fn(self.device)
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon of the binary sensor."""
        if self.entity_description.key == "online" and self.device:
            return ICON_ONLINE if self.device.is_online else ICON_OFFLINE
        return self.entity_description.icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.device:
            return {}

        attrs = {
            ATTR_DEVICE_UUID: self.device.uuid,
            ATTR_DEVICE_NAME: self.device.device_name,
            ATTR_DEVICE_TYPE: self.device.device_type,
            ATTR_FLEET_NAME: self.device.fleet_name,
            ATTR_OS_VERSION: self.device.os_version,
            ATTR_SUPERVISOR_VERSION: self.device.supervisor_version,
            ATTR_IP_ADDRESS: self.device.ip_address,
            ATTR_MAC_ADDRESS: self.device.mac_address,
        }

        # Add sensor-specific attributes
        if self.entity_description.attr_fn:
            attrs.update(self.entity_description.attr_fn(self.device))

        # Remove None values
        return {k: v for k, v in attrs.items() if v is not None}

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
