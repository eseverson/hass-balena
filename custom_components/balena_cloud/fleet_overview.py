"""Fleet overview component for Balena Cloud integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ICON_FLEET,
)
from .coordinator import BalenaCloudDataUpdateCoordinator
from .models import BalenaDevice, BalenaFleet

_LOGGER = logging.getLogger(__name__)


class BalenaFleetOverview(CoordinatorEntity[BalenaCloudDataUpdateCoordinator]):
    """Fleet overview component for comprehensive fleet monitoring."""

    def __init__(
        self,
        coordinator: BalenaCloudDataUpdateCoordinator,
        fleet_id: int,
    ) -> None:
        """Initialize the fleet overview."""
        super().__init__(coordinator)
        self._fleet_id = fleet_id
        self._attr_unique_id = f"fleet_overview_{fleet_id}"

    @property
    def fleet(self) -> BalenaFleet | None:
        """Return the fleet."""
        return self.coordinator.get_fleet(self._fleet_id)

    @property
    def devices(self) -> List[BalenaDevice]:
        """Return devices in this fleet."""
        return self.coordinator.get_devices_by_fleet(self._fleet_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.fleet is not None

    @property
    def name(self) -> str:
        """Return the name of the fleet overview."""
        if self.fleet:
            return f"{self.fleet.app_name} Fleet Overview"
        return f"Fleet {self._fleet_id} Overview"

    @property
    def icon(self) -> str:
        """Return the icon for the fleet overview."""
        return ICON_FLEET

    @property
    def fleet_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive fleet statistics."""
        devices = self.devices

        if not devices:
            return {
                "total_devices": 0,
                "online_devices": 0,
                "offline_devices": 0,
                "updating_devices": 0,
                "idle_devices": 0,
                "average_metrics": {},
                "health_summary": {},
                "device_types": {},
                "status_distribution": {},
            }

        # Basic counts
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.is_online)
        offline_devices = total_devices - online_devices
        updating_devices = sum(1 for d in devices if d.is_updating)
        idle_devices = sum(1 for d in devices if d.is_idle)

        # Device type distribution
        device_types = {}
        for device in devices:
            device_type = device.device_type
            device_types[device_type] = device_types.get(device_type, 0) + 1

        # Status distribution
        status_distribution = {}
        for device in devices:
            status = device.status
            status_distribution[status] = status_distribution.get(status, 0) + 1

        # Average metrics (only for devices with metrics)
        devices_with_metrics = [d for d in devices if d.metrics is not None]
        average_metrics = self._calculate_average_metrics(devices_with_metrics)

        # Health summary
        health_summary = self._calculate_fleet_health(devices)

        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "updating_devices": updating_devices,
            "idle_devices": idle_devices,
            "online_percentage": (
                round((online_devices / total_devices) * 100, 1)
                if total_devices > 0
                else 0
            ),
            "average_metrics": average_metrics,
            "health_summary": health_summary,
            "device_types": device_types,
            "status_distribution": status_distribution,
            "last_update": datetime.now().isoformat(),
        }

    def _calculate_average_metrics(
        self, devices_with_metrics: List[BalenaDevice]
    ) -> Dict[str, Any]:
        """Calculate average metrics across fleet devices."""
        if not devices_with_metrics:
            return {}

        cpu_values = [
            d.metrics.cpu_percentage
            for d in devices_with_metrics
            if d.metrics.cpu_percentage is not None
        ]
        memory_values = [
            d.metrics.memory_percentage
            for d in devices_with_metrics
            if d.metrics.memory_percentage is not None
        ]
        storage_values = [
            d.metrics.storage_percentage
            for d in devices_with_metrics
            if d.metrics.storage_percentage is not None
        ]
        temp_values = [
            d.metrics.temperature
            for d in devices_with_metrics
            if d.metrics.temperature is not None
        ]

        return {
            "average_cpu_usage": (
                round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None
            ),
            "average_memory_usage": (
                round(sum(memory_values) / len(memory_values), 1)
                if memory_values
                else None
            ),
            "average_storage_usage": (
                round(sum(storage_values) / len(storage_values), 1)
                if storage_values
                else None
            ),
            "average_temperature": (
                round(sum(temp_values) / len(temp_values), 1) if temp_values else None
            ),
            "devices_with_metrics": len(devices_with_metrics),
        }

    def _calculate_fleet_health(self, devices: List[BalenaDevice]) -> Dict[str, Any]:
        """Calculate overall fleet health indicators."""
        if not devices:
            return {
                "overall_status": "unknown",
                "critical_devices": 0,
                "warning_devices": 0,
                "healthy_devices": 0,
                "alerts": [],
            }

        critical_devices = 0
        warning_devices = 0
        healthy_devices = 0
        fleet_alerts = []

        for device in devices:
            if not device.is_online:
                critical_devices += 1
                continue

            device_health = self._assess_device_health(device)

            if device_health["status"] == "critical":
                critical_devices += 1
            elif device_health["status"] == "warning":
                warning_devices += 1
            else:
                healthy_devices += 1

        # Fleet-level alerts
        offline_percentage = (
            (len(devices) - sum(1 for d in devices if d.is_online)) / len(devices) * 100
        )
        if offline_percentage > 50:
            fleet_alerts.append(
                f"High offline rate: {offline_percentage:.1f}% of devices offline"
            )
        elif offline_percentage > 25:
            fleet_alerts.append(
                f"Elevated offline rate: {offline_percentage:.1f}% of devices offline"
            )

        if critical_devices > 0:
            fleet_alerts.append(f"{critical_devices} device(s) in critical state")

        # Determine overall fleet status
        if critical_devices == 0 and warning_devices == 0:
            overall_status = "healthy"
        elif critical_devices == 0:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return {
            "overall_status": overall_status,
            "critical_devices": critical_devices,
            "warning_devices": warning_devices,
            "healthy_devices": healthy_devices,
            "alerts": fleet_alerts,
        }

    def _assess_device_health(self, device: BalenaDevice) -> Dict[str, str]:
        """Assess individual device health for fleet calculations."""
        if not device.metrics:
            return {"status": "unknown"}

        critical_conditions = []
        warning_conditions = []

        metrics = device.metrics

        # Check critical conditions
        if metrics.cpu_percentage is not None and metrics.cpu_percentage > 95:
            critical_conditions.append("cpu")
        if metrics.memory_percentage is not None and metrics.memory_percentage > 95:
            critical_conditions.append("memory")
        if metrics.storage_percentage is not None and metrics.storage_percentage > 98:
            critical_conditions.append("storage")
        if metrics.temperature is not None and metrics.temperature > 85:
            critical_conditions.append("temperature")

        # Check warning conditions
        if metrics.cpu_percentage is not None and 80 < metrics.cpu_percentage <= 95:
            warning_conditions.append("cpu")
        if (
            metrics.memory_percentage is not None
            and 85 < metrics.memory_percentage <= 95
        ):
            warning_conditions.append("memory")
        if (
            metrics.storage_percentage is not None
            and 90 < metrics.storage_percentage <= 98
        ):
            warning_conditions.append("storage")
        if metrics.temperature is not None and 75 < metrics.temperature <= 85:
            warning_conditions.append("temperature")

        if critical_conditions:
            return {"status": "critical"}
        elif warning_conditions:
            return {"status": "warning"}
        else:
            return {"status": "healthy"}

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attrs = self.fleet_statistics.copy()

        if self.fleet:
            attrs.update(
                {
                    "fleet_id": self.fleet.id,
                    "fleet_name": self.fleet.app_name,
                    "fleet_slug": self.fleet.slug,
                    "device_type": self.fleet.device_type,
                    "created_at": (
                        self.fleet.created_at.isoformat()
                        if self.fleet.created_at
                        else None
                    ),
                }
            )

        return attrs

    @property
    def state(self) -> str:
        """Return the state of the fleet overview."""
        stats = self.fleet_statistics
        return f"{stats['online_devices']}/{stats['total_devices']} online"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information about this entity."""
        if not self.fleet:
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, f"fleet_{self.fleet.id}")},
            name=f"{self.fleet.app_name} Fleet",
            manufacturer="Balena",
            model="Fleet",
            configuration_url=f"https://dashboard.balena-cloud.com/apps/{self.fleet.id}",
        )


async def async_setup_fleet_overviews(
    hass: HomeAssistant,
    coordinator: BalenaCloudDataUpdateCoordinator,
) -> List[BalenaFleetOverview]:
    """Set up fleet overview entities for all discovered fleets."""
    overviews = []

    for fleet_id in coordinator.fleets:
        overview = BalenaFleetOverview(coordinator, fleet_id)
        overviews.append(overview)

    return overviews
