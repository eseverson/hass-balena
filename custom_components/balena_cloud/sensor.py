"""Sensor platform for Balena Cloud integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorEntityDescription,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (ATTR_DEVICE_NAME, ATTR_DEVICE_TYPE, ATTR_DEVICE_UUID,
                    ATTR_FLEET_ID, ATTR_FLEET_NAME, ATTR_IP_ADDRESS, ATTR_LAST_SEEN,
                    ATTR_MAC_ADDRESS, ATTR_MEMORY_TOTAL, ATTR_MEMORY_USAGE,
                    ATTR_OS_VERSION, ATTR_PUBLIC_ADDRESS, ATTR_STORAGE_TOTAL, ATTR_STORAGE_USAGE,
                    ATTR_SUPERVISOR_VERSION, DOMAIN, ICON_CPU, ICON_FLEET, ICON_IP_ADDRESS,
                    ICON_LOCATION, ICON_MAC_ADDRESS, ICON_MEMORY,
                    ICON_STORAGE, ICON_TEMPERATURE, UNIT_CELSIUS)
from .coordinator import BalenaCloudDataUpdateCoordinator
from .models import BalenaDevice

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalenaCloudSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[BalenaDevice], Any]


@dataclass(frozen=True)
class BalenaCloudSensorEntityDescription(
    SensorEntityDescription, BalenaCloudSensorEntityDescriptionMixin
):
    """Describes Balena Cloud sensor entity."""

    attr_fn: Callable[[BalenaDevice], dict[str, Any]] | None = None


SENSOR_TYPES: tuple[BalenaCloudSensorEntityDescription, ...] = (
    BalenaCloudSensorEntityDescription(
        key="cpu_usage",
        name="CPU Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_CPU,
        value_fn=lambda device: (
            device.metrics.cpu_percentage if device.metrics else None
        ),
    ),
    BalenaCloudSensorEntityDescription(
        key="memory_usage",
        name="Memory Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_MEMORY,
        value_fn=lambda device: (
            device.metrics.memory_percentage if device.metrics else None
        ),
        attr_fn=lambda device: {
            ATTR_MEMORY_USAGE: device.metrics.memory_usage if device.metrics else None,
            ATTR_MEMORY_TOTAL: device.metrics.memory_total if device.metrics else None,
        },
    ),
    BalenaCloudSensorEntityDescription(
        key="storage_usage",
        name="Storage Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_STORAGE,
        value_fn=lambda device: (
            device.metrics.storage_percentage if device.metrics else None
        ),
        attr_fn=lambda device: {
            ATTR_STORAGE_USAGE: (
                device.metrics.storage_usage if device.metrics else None
            ),
            ATTR_STORAGE_TOTAL: (
                device.metrics.storage_total if device.metrics else None
            ),
        },
    ),
    BalenaCloudSensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UNIT_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon=ICON_TEMPERATURE,
        value_fn=lambda device: (
            device.metrics.temperature_rounded if device.metrics else None
        ),
    ),
    BalenaCloudSensorEntityDescription(
        key="fleet_name",
        name="Fleet",
        icon=ICON_FLEET,
        value_fn=lambda device: device.fleet_name,
        attr_fn=lambda device: {
            ATTR_FLEET_ID: device.fleet_id,
            ATTR_FLEET_NAME: device.fleet_name,
        },
    ),
    BalenaCloudSensorEntityDescription(
        key="ip_address",
        name="IP Address",
        icon=ICON_IP_ADDRESS,
        value_fn=lambda device: device.ip_address,
        attr_fn=lambda device: {
            ATTR_IP_ADDRESS: device.ip_address,
            ATTR_PUBLIC_ADDRESS: device.public_address,
        },
    ),
    BalenaCloudSensorEntityDescription(
        key="mac_address",
        name="MAC Address",
        icon=ICON_MAC_ADDRESS,
        value_fn=lambda device: device.mac_address,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Balena Cloud sensors from a config entry."""
    coordinator: BalenaCloudDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[BalenaCloudSensorEntity] = []

    for device_uuid, device in coordinator.devices.items():
        for description in SENSOR_TYPES:
            entities.append(
                BalenaCloudSensorEntity(
                    coordinator=coordinator,
                    description=description,
                    device_uuid=device_uuid,
                )
            )

    async_add_entities(entities)


class BalenaCloudSensorEntity(
    CoordinatorEntity[BalenaCloudDataUpdateCoordinator], SensorEntity
):
    """Representation of a Balena Cloud sensor."""

    entity_description: BalenaCloudSensorEntityDescription

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        description: BalenaCloudSensorEntityDescription,
        device_uuid: str,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.device:
            return self.entity_description.value_fn(self.device)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.device:
            return {}

        attrs = {
            ATTR_DEVICE_UUID: self.device.uuid,
            ATTR_DEVICE_NAME: self.device.device_name,
            ATTR_DEVICE_TYPE: self.device.device_type,
            ATTR_FLEET_ID: self.device.fleet_id,
            ATTR_FLEET_NAME: self.device.fleet_name,
            ATTR_OS_VERSION: self.device.os_version,
            ATTR_SUPERVISOR_VERSION: self.device.supervisor_version,
            ATTR_IP_ADDRESS: self.device.ip_address,
            ATTR_PUBLIC_ADDRESS: self.device.public_address,
            ATTR_MAC_ADDRESS: self.device.mac_address,
            ATTR_LAST_SEEN: (
                self.device.last_seen.isoformat() if self.device.last_seen else None
            ),
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
