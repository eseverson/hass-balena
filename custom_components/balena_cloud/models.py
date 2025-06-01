"""Data models for Balena Cloud integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BalenaFleet:
    """Represents a Balena Cloud fleet (application)."""

    id: int
    app_name: str
    slug: str
    device_type: str
    is_accessible_by_support_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> BalenaFleet:
        """Create a BalenaFleet from API response data."""
        return cls(
            id=data.get("id", 0),
            app_name=data.get("app_name", ""),
            slug=data.get("slug", ""),
            device_type=data.get("device_type", ""),
            is_accessible_by_support_until=_parse_datetime(
                data.get("is_accessible_by_support_until__expiry_date")
            ),
            created_at=_parse_datetime(data.get("created_at")),
            modified_at=_parse_datetime(data.get("__metadata", {}).get("modified_at")),
        )

    @property
    def display_name(self) -> str:
        """Get display name for the fleet."""
        return self.app_name


@dataclass
class BalenaDeviceMetrics:
    """Represents device metrics and resource usage."""

    cpu_usage: Optional[float] = None
    memory_usage: Optional[int] = None
    memory_total: Optional[int] = None
    storage_usage: Optional[int] = None
    storage_total: Optional[int] = None
    temperature: Optional[float] = None

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> BalenaDeviceMetrics:
        """Create a BalenaDeviceMetrics from API response data."""
        return cls(
            cpu_usage=data.get("cpu_usage"),
            memory_usage=data.get("memory_usage"),
            memory_total=data.get("memory_total"),
            storage_usage=data.get("storage_usage"),
            storage_total=data.get("storage_total"),
            temperature=data.get("temperature"),
        )

    @property
    def cpu_percentage(self) -> Optional[float]:
        """Get CPU usage as percentage."""
        return self.cpu_usage

    @property
    def memory_percentage(self) -> Optional[float]:
        """Get memory usage as percentage."""
        if (
            self.memory_usage is not None
            and self.memory_total is not None
            and self.memory_total > 0
        ):
            return (self.memory_usage / self.memory_total) * 100
        return None

    @property
    def storage_percentage(self) -> Optional[float]:
        """Get storage usage as percentage."""
        if (
            self.storage_usage is not None
            and self.storage_total is not None
            and self.storage_total > 0
        ):
            return (self.storage_usage / self.storage_total) * 100
        return None


@dataclass
class BalenaDevice:
    """Represents a Balena Cloud device."""

    uuid: str
    device_name: str
    device_type: str
    fleet_id: int
    fleet_name: str
    is_online: bool
    status: str
    last_connectivity_event: Optional[datetime] = None
    last_vpn_event: Optional[datetime] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    os_version: Optional[str] = None
    os_variant: Optional[str] = None
    supervisor_version: Optional[str] = None
    provisioning_progress: Optional[int] = None
    provisioning_state: Optional[str] = None
    public_address: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    metrics: Optional[BalenaDeviceMetrics] = None

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], fleet_name: str = "") -> BalenaDevice:
        """Create a BalenaDevice from API response data."""
        return cls(
            uuid=data.get("uuid", ""),
            device_name=data.get("device_name") or data.get("name", ""),
            device_type=data.get("device_type", ""),
            fleet_id=data.get("belongs_to__application", {}).get("__id", 0),
            fleet_name=fleet_name
            or data.get("belongs_to__application", {}).get("app_name", ""),
            is_online=data.get("is_online", False),
            status=data.get("status", "offline"),
            last_connectivity_event=_parse_datetime(
                data.get("last_connectivity_event")
            ),
            last_vpn_event=_parse_datetime(data.get("last_vpn_event")),
            ip_address=data.get("ip_address"),
            mac_address=data.get("mac_address"),
            os_version=data.get("os_version"),
            os_variant=data.get("os_variant"),
            supervisor_version=data.get("supervisor_version"),
            provisioning_progress=data.get("provisioning_progress"),
            provisioning_state=data.get("provisioning_state"),
            public_address=data.get("public_address"),
            created_at=_parse_datetime(data.get("created_at")),
            modified_at=_parse_datetime(data.get("__metadata", {}).get("modified_at")),
        )

    @property
    def unique_id(self) -> str:
        """Get unique identifier for the device."""
        return self.uuid

    @property
    def display_name(self) -> str:
        """Get display name for the device."""
        if self.device_name:
            return self.device_name
        return self.uuid

    @property
    def is_updating(self) -> bool:
        """Check if device is currently updating."""
        return self.status in ["Updating", "Downloading", "Downloaded"]

    @property
    def is_idle(self) -> bool:
        """Check if device is idle."""
        return self.status == "Idle"

    @property
    def last_seen(self) -> Optional[datetime]:
        """Get the last time the device was seen."""
        if self.last_connectivity_event:
            return self.last_connectivity_event
        if self.last_vpn_event:
            return self.last_vpn_event
        return None

    def update_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Update device metrics."""
        self.metrics = BalenaDeviceMetrics(
            cpu_usage=metrics_data.get("cpu_usage"),
            memory_usage=metrics_data.get("memory_usage"),
            memory_total=metrics_data.get("memory_total"),
            storage_usage=metrics_data.get("storage_usage"),
            storage_total=metrics_data.get("storage_total"),
            temperature=metrics_data.get("temperature"),
        )


@dataclass
class BalenaService:
    """Represents a service running on a Balena device."""

    service_name: str
    status: str
    image_id: Optional[str] = None
    created_at: Optional[datetime] = None
    running_since: Optional[datetime] = None
    restart_count: int = 0

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> BalenaService:
        """Create a BalenaService from API response data."""
        return cls(
            service_name=data.get("service_name", ""),
            status=data.get("status", "unknown"),
            image_id=data.get("image_id"),
            created_at=_parse_datetime(data.get("created_at")),
            running_since=_parse_datetime(data.get("running_since")),
            restart_count=data.get("restart_count", 0),
        )

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self.status.lower() == "running"

    @property
    def has_failed(self) -> bool:
        """Check if service has failed."""
        return self.status.lower() in ["failed", "exited"]


@dataclass
class BalenaEnvironmentVariable:
    """Represents an environment variable on a Balena device."""

    name: str
    value: str
    device_uuid: Optional[str] = None
    fleet_id: Optional[int] = None

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> BalenaEnvironmentVariable:
        """Create a BalenaEnvironmentVariable from API response data."""
        return cls(
            name=data.get("name", ""),
            value=data.get("value", ""),
            device_uuid=(
                data.get("device", {}).get("uuid")
                if isinstance(data.get("device"), dict)
                else data.get("device")
            ),
            fleet_id=(
                data.get("application", {}).get("__id")
                if isinstance(data.get("application"), dict)
                else data.get("application")
            ),
        )


def _parse_datetime(date_string: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from API response."""
    if not date_string:
        return None

    try:
        # Handle different datetime formats from Balena API
        if date_string.endswith("Z"):
            return datetime.fromisoformat(date_string[:-1] + "+00:00")
        else:
            return datetime.fromisoformat(date_string)
    except (ValueError, TypeError):
        return None
