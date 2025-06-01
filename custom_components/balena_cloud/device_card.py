"""Device dashboard card component for Balena Cloud integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_component import EntityComponent
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


class BalenaDeviceCard(CoordinatorEntity[BalenaCloudDataUpdateCoordinator]):
    """Device card component for enhanced dashboard display."""

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the device card."""
        super().__init__(coordinator)
        self._device_uuid = device_uuid
        self._attr_unique_id = f"device_card_{device_uuid}"

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
        """Return the name of the device card."""
        if self.device:
            return f"{self.device.display_name} Dashboard"
        return "Unknown Device Dashboard"

    @property
    def card_data(self) -> Dict[str, Any]:
        """Return comprehensive card data for frontend display."""
        if not self.device:
            return {}

        metrics = self.device.metrics

        return {
            "device_info": {
                "uuid": self.device.uuid,
                "name": self.device.display_name,
                "type": self.device.device_type,
                "fleet": self.device.fleet_name,
                "os_version": self.device.os_version,
                "supervisor_version": self.device.supervisor_version,
                "ip_address": self.device.ip_address,
                "mac_address": self.device.mac_address,
            },
            "status": {
                "online": self.device.is_online,
                "updating": self.device.is_updating,
                "idle": self.device.is_idle,
                "status_text": self.device.status,
                "last_seen": (
                    self.device.last_seen.isoformat() if self.device.last_seen else None
                ),
            },
            "metrics": {
                "cpu_usage": metrics.cpu_percentage if metrics else None,
                "memory_usage": metrics.memory_percentage if metrics else None,
                "memory_used": metrics.memory_usage if metrics else None,
                "memory_total": metrics.memory_total if metrics else None,
                "storage_usage": metrics.storage_percentage if metrics else None,
                "storage_used": metrics.storage_usage if metrics else None,
                "storage_total": metrics.storage_total if metrics else None,
                "temperature": metrics.temperature if metrics else None,
            },
            "actions": {
                "restart_available": self.device.is_online,
                "reboot_available": self.device.is_online,
            },
            "health_indicators": self._get_health_indicators(),
            "last_update": datetime.now().isoformat(),
        }

    def _get_health_indicators(self) -> Dict[str, Any]:
        """Calculate health indicators for the device."""
        if not self.device or not self.device.metrics:
            return {
                "overall_health": "unknown",
                "alerts": [],
                "warnings": [],
            }

        alerts = []
        warnings = []
        health_score = 100

        metrics = self.device.metrics

        # CPU usage checks
        if metrics.cpu_percentage is not None:
            if metrics.cpu_percentage > 90:
                alerts.append("High CPU usage")
                health_score -= 20
            elif metrics.cpu_percentage > 75:
                warnings.append("Elevated CPU usage")
                health_score -= 10

        # Memory usage checks
        if metrics.memory_percentage is not None:
            if metrics.memory_percentage > 90:
                alerts.append("High memory usage")
                health_score -= 20
            elif metrics.memory_percentage > 80:
                warnings.append("Elevated memory usage")
                health_score -= 10

        # Storage usage checks
        if metrics.storage_percentage is not None:
            if metrics.storage_percentage > 95:
                alerts.append("Storage nearly full")
                health_score -= 25
            elif metrics.storage_percentage > 85:
                warnings.append("Storage usage high")
                health_score -= 15

        # Temperature checks (if available)
        if metrics.temperature is not None:
            if metrics.temperature > 80:  # 80°C threshold
                alerts.append("High temperature")
                health_score -= 15
            elif metrics.temperature > 70:
                warnings.append("Elevated temperature")
                health_score -= 5

        # Device status checks
        if not self.device.is_online:
            alerts.append("Device offline")
            health_score -= 50

        # Determine overall health
        if health_score >= 90:
            overall_health = "excellent"
        elif health_score >= 75:
            overall_health = "good"
        elif health_score >= 50:
            overall_health = "fair"
        elif health_score >= 25:
            overall_health = "poor"
        else:
            overall_health = "critical"

        return {
            "overall_health": overall_health,
            "health_score": health_score,
            "alerts": alerts,
            "warnings": warnings,
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return self.card_data

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


async def async_setup_device_cards(
    hass: HomeAssistant,
    coordinator: BalenaCloudDataUpdateCoordinator,
) -> None:
    """Set up device cards for all discovered devices."""
    cards = []

    for device_uuid in coordinator.devices:
        card = BalenaDeviceCard(coordinator, device_uuid)
        cards.append(card)

    # Register cards with Home Assistant
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(cards)
