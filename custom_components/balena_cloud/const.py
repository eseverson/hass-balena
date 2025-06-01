"""Constants for the Balena Cloud integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

# Integration domain
DOMAIN: Final = "balena_cloud"

# API Configuration
BALENA_API_BASE_URL: Final = "https://api.balena-cloud.com"
BALENA_API_VERSION: Final = "v6"
API_TIMEOUT: Final = 30  # seconds

# Configuration keys
CONF_API_TOKEN: Final = "api_token"
CONF_FLEETS: Final = "fleets"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_INCLUDE_OFFLINE_DEVICES: Final = "include_offline_devices"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 30  # seconds
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=DEFAULT_UPDATE_INTERVAL)
DEFAULT_INCLUDE_OFFLINE_DEVICES: Final = True

# Retry configuration (for balena-sdk operations)
MAX_RETRIES: Final = 3
RETRY_DELAY: Final = 1  # seconds

# Entity attributes
ATTR_DEVICE_UUID: Final = "device_uuid"
ATTR_FLEET_NAME: Final = "fleet_name"
ATTR_FLEET_ID: Final = "fleet_id"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_DEVICE_TYPE: Final = "device_type"
ATTR_OS_VERSION: Final = "os_version"
ATTR_SUPERVISOR_VERSION: Final = "supervisor_version"
ATTR_LAST_SEEN: Final = "last_seen"
ATTR_IP_ADDRESS: Final = "ip_address"
ATTR_PUBLIC_ADDRESS: Final = "public_address"
ATTR_MAC_ADDRESS: Final = "mac_address"
ATTR_CPU_USAGE: Final = "cpu_usage"
ATTR_MEMORY_USAGE: Final = "memory_usage"
ATTR_MEMORY_TOTAL: Final = "memory_total"
ATTR_STORAGE_USAGE: Final = "storage_usage"
ATTR_STORAGE_TOTAL: Final = "storage_total"
ATTR_TEMPERATURE: Final = "temperature"

# Device states
DEVICE_STATE_ONLINE: Final = "online"
DEVICE_STATE_OFFLINE: Final = "offline"
DEVICE_STATE_IDLE: Final = "idle"
DEVICE_STATE_UPDATING: Final = "updating"

# Service states
SERVICE_STATE_RUNNING: Final = "running"
SERVICE_STATE_STOPPED: Final = "stopped"
SERVICE_STATE_FAILED: Final = "failed"
SERVICE_STATE_EXITED: Final = "exited"
SERVICE_STATE_RESTARTING: Final = "restarting"

# Icons
ICON_DEVICE: Final = "mdi:raspberry-pi"
ICON_FLEET: Final = "mdi:server-network"
ICON_ONLINE: Final = "mdi:check-circle"
ICON_OFFLINE: Final = "mdi:alert-circle"
ICON_CPU: Final = "mdi:chip"
ICON_MEMORY: Final = "mdi:memory"
ICON_STORAGE: Final = "mdi:harddisk"
ICON_TEMPERATURE: Final = "mdi:thermometer"
ICON_RESTART: Final = "mdi:restart"
ICON_REBOOT: Final = "mdi:power-cycle"
ICON_LOCATION: Final = "mdi:map-marker"
ICON_IP_ADDRESS: Final = "mdi:ip-network"
ICON_MAC_ADDRESS: Final = "mdi:ethernet"

# Device classes and units
UNIT_PERCENTAGE: Final = "%"
UNIT_BYTES: Final = "B"
UNIT_MEGABYTES: Final = "MB"
UNIT_GIGABYTES: Final = "GB"
UNIT_CELSIUS: Final = "°C"

# Error messages
ERROR_AUTH_FAILED: Final = "Authentication failed"
ERROR_NETWORK_ERROR: Final = "Network error occurred"
ERROR_RATE_LIMITED: Final = "API rate limit exceeded"
ERROR_INVALID_TOKEN: Final = "Invalid API token"
ERROR_FLEET_NOT_FOUND: Final = "Fleet not found"
ERROR_DEVICE_NOT_FOUND: Final = "Device not found"

# Service names
SERVICE_RESTART_APPLICATION: Final = "restart_application"
SERVICE_REBOOT_DEVICE: Final = "reboot_device"
SERVICE_SHUTDOWN_DEVICE: Final = "shutdown_device"
SERVICE_UPDATE_ENVIRONMENT: Final = "update_environment"
SERVICE_ENABLE_DEVICE_URL: Final = "enable_device_url"
SERVICE_DISABLE_DEVICE_URL: Final = "disable_device_url"
