"""Test configuration and fixtures for Balena Cloud integration tests."""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest_asyncio

from custom_components.balena_cloud.const import DOMAIN


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession."""
    session = AsyncMock(spec=ClientSession)
    return session


@pytest.fixture
def mock_balena_api_response():
    """Mock Balena Cloud API responses."""
    return {
        "user": {
            "id": 12345,
            "username": "test_user",
            "email": "test@example.com",
        },
        "fleets": [
            {
                "id": 1001,
                "app_name": "test-fleet-1",
                "slug": "test_user/test-fleet-1",
                "device_type": "raspberrypi4-64",
                "created_at": "2024-01-01T00:00:00.000Z",
            },
            {
                "id": 1002,
                "app_name": "test-fleet-2",
                "slug": "test_user/test-fleet-2",
                "device_type": "jetson-orin-nano-devkit",
                "created_at": "2024-01-02T00:00:00.000Z",
            },
        ],
        "devices": [
            {
                "id": 2001,
                "uuid": "device-uuid-1",
                "device_name": "test-device-1",
                "device_type": "raspberrypi4-64",
                "belongs_to__application": {"__id": 1001, "app_name": "test-fleet-1"},
                "is_online": True,
                "status": "Idle",
                "ip_address": "192.168.1.100",
                "mac_address": "b8:27:eb:12:34:56",
                "os_version": "balenaOS 2024.1.1",
                "supervisor_version": "14.13.5",
                "last_connectivity_event": "2024-01-15T10:30:00.000Z",
                "created_at": "2024-01-01T12:00:00.000Z",
            },
            {
                "id": 2002,
                "uuid": "device-uuid-2",
                "device_name": "test-device-2",
                "device_type": "jetson-orin-nano-devkit",
                "belongs_to__application": {"__id": 1002, "app_name": "test-fleet-2"},
                "is_online": False,
                "status": "Offline",
                "ip_address": None,
                "mac_address": "00:04:4b:12:34:56",
                "os_version": "balenaOS 2024.1.0",
                "supervisor_version": "14.13.3",
                "last_connectivity_event": "2024-01-14T08:15:00.000Z",
                "created_at": "2024-01-02T14:30:00.000Z",
            },
        ],
        "device_metrics": {
            "device-uuid-1": {
                "cpu_usage": 25.5,
                "memory_usage": 512000000,
                "memory_total": 2000000000,
                "storage_usage": 8000000000,
                "storage_total": 32000000000,
                "temperature": 45.2,
            },
            "device-uuid-2": {
                "cpu_usage": None,
                "memory_usage": None,
                "memory_total": None,
                "storage_usage": None,
                "storage_total": None,
                "temperature": None,
            },
        },
    }


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    return {
        "entry_id": "test_entry_id",
        "data": {
            "api_token": "test_api_token_12345",
            "fleets": [1001, 1002],
        },
        "options": {
            "update_interval": 30,
            "include_offline_devices": True,
        },
    }


@pytest_asyncio.fixture
async def mock_integration_setup(hass: HomeAssistant, mock_config_entry):
    """Set up the integration with mocked dependencies."""

    with patch("custom_components.balena_cloud.BalenaCloudAPIClient") as mock_api, \
         patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:

        # Configure API client mock
        api_instance = AsyncMock()
        mock_api.return_value = api_instance

        # Configure session mock
        mock_session.return_value = AsyncMock(spec=ClientSession)

        # Set up the integration
        assert await async_setup_component(
            hass,
            DOMAIN,
            {DOMAIN: mock_config_entry["data"]},
        )
        await hass.async_block_till_done()

        yield {
            "api_client": api_instance,
            "session": mock_session.return_value,
        }


@pytest.fixture
def mock_rate_limit_response():
    """Mock rate limit HTTP response."""
    response = MagicMock()
    response.status = 429
    response.headers = {"X-RateLimit-Reset": "1705398000"}  # Future timestamp
    response.text = AsyncMock(return_value="Rate limit exceeded")
    return response


@pytest.fixture
def mock_auth_error_response():
    """Mock authentication error HTTP response."""
    response = MagicMock()
    response.status = 401
    response.headers = {}
    response.text = AsyncMock(return_value="Unauthorized")
    return response


@pytest.fixture
def mock_network_error():
    """Mock network error."""
    from aiohttp import ClientError
    return ClientError("Network connection failed")


@pytest.fixture
def mock_timeout_error():
    """Mock timeout error."""
    import asyncio
    return asyncio.TimeoutError()


class MockHomeAssistant:
    """Mock Home Assistant instance for testing."""

    def __init__(self):
        self.data = {}
        self.states = MagicMock()  # Use MagicMock for properties
        self.services = MagicMock()  # Use MagicMock for properties
        # Override has_service and async_register to be regular methods, not async
        self.services.has_service = MagicMock(return_value=False)
        self.services.async_register = MagicMock()
        self.services.async_remove = MagicMock()
        self.services.async_call = AsyncMock()  # This is actually awaited
        self.bus = MagicMock()  # Use MagicMock for properties
        self.config_entries = MagicMock()  # Use MagicMock for properties
        # But async_forward_entry_setups is actually awaited
        self.config_entries.async_forward_entry_setups = AsyncMock()

    async def async_block_till_done(self):
        """Mock async_block_till_done."""
        pass


@pytest.fixture
def mock_hass():
    """Provide a mock Home Assistant instance."""
    return MockHomeAssistant()


# Alias for the hass fixture that tests expect
@pytest.fixture
def hass(mock_hass):
    """Alias for mock_hass fixture to match test expectations."""
    return mock_hass


@pytest.fixture
def mock_device():
    """Mock Balena device for testing."""
    device = MagicMock()
    device.uuid = "device-uuid-1"
    device.display_name = "Test Device 1"
    device.device_name = "Test Device 1"
    device.device_type = "raspberrypi4-64"
    device.fleet_id = 1001
    device.fleet_name = "test-fleet-1"
    device.is_online = True
    device.status = "Idle"
    device.ip_address = "192.168.1.100"
    device.mac_address = "b8:27:eb:12:34:56"
    device.os_version = "balenaOS 2024.1.1"
    device.supervisor_version = "14.13.5"
    device.last_connectivity_event = "2024-01-15T10:30:00.000Z"
    device.created_at = "2024-01-01T12:00:00.000Z"

    # Mock metrics
    device.metrics = MagicMock()
    device.metrics.cpu_usage = 25.5
    device.metrics.cpu_percentage = 25.5
    device.metrics.memory_usage = 512000000
    device.metrics.memory_total = 2000000000
    device.metrics.memory_percentage = 25.6
    device.metrics.storage_usage = 8000000000
    device.metrics.storage_total = 32000000000
    device.metrics.storage_percentage = 25.0
    device.metrics.temperature = 45.2

    return device


@pytest.fixture
def mock_device_with_metrics():
    """Mock Balena device with metrics for testing."""
    from custom_components.balena_cloud.models import BalenaDevice, BalenaDeviceMetrics
    from datetime import datetime

    # Create the device using the actual model
    device = BalenaDevice(
        uuid="test-device-uuid-12345",
        device_name="Test Device",
        device_type="raspberrypi4-64",
        fleet_id=1001,
        fleet_name="test-fleet",
        is_online=True,
        status="Idle",
        ip_address="192.168.1.100",
        mac_address="b8:27:eb:12:34:56",
        os_version="balenaOS 2024.1.1",
        supervisor_version="14.13.5",
        last_connectivity_event=datetime.fromisoformat("2024-01-15T10:30:00"),
        created_at=datetime.fromisoformat("2024-01-01T12:00:00"),
    )

    # Add metrics
    device.metrics = BalenaDeviceMetrics(
        cpu_usage=25.5,
        memory_usage=512000000,
        memory_total=2000000000,
        storage_usage=8000000000,
        storage_total=32000000000,
        temperature=45.2,
    )

    return device


@pytest.fixture
def mock_coordinator_setup():
    """Set up mock coordinator for testing."""
    from custom_components.balena_cloud.coordinator import BalenaCloudDataUpdateCoordinator

    mock_hass = AsyncMock()

    config_data = {
        "api_token": "test_token_12345",
        "fleets": [1001, 1002],
    }

    config_options = {
        "update_interval": 30,
        "include_offline_devices": True,
    }

    # Create coordinator with correct constructor signature (3 args: hass, config_data, options)
    coordinator = BalenaCloudDataUpdateCoordinator(
        mock_hass,
        config_data,
        config_options,
    )

    # Mock the API client
    coordinator.api = AsyncMock()

    return coordinator, mock_hass, config_data


@pytest.fixture
def sample_automation_config():
    """Sample automation configurations for testing."""
    return {
        "device_offline_alert": {
            "alias": "Balena Device Offline Alert",
            "trigger": {
                "platform": "state",
                "entity_id": "binary_sensor.test_device_1_online",
                "to": "off",
                "for": {"minutes": 5},
            },
            "action": {
                "service": "notify.mobile_app",
                "data": {
                    "title": "Device Offline",
                    "message": "{{ trigger.to_state.attributes.device_name }} went offline",
                },
            },
        },
        "high_cpu_restart": {
            "alias": "Restart on High CPU",
            "trigger": {
                "platform": "numeric_state",
                "entity_id": "sensor.test_device_1_cpu_usage",
                "above": 90,
                "for": {"minutes": 10},
            },
            "action": {
                "service": "balena_cloud.restart_application",
                "data": {
                    "device_uuid": "device-uuid-1",
                    "confirm": True,
                },
            },
        },
        "fleet_health_check": {
            "alias": "Fleet Health Check",
            "trigger": {
                "platform": "time_pattern",
                "hours": "/6",
            },
            "action": [
                {
                    "service": "balena_cloud.get_fleet_health",
                    "data": {"fleet_id": 1001},
                },
                {
                    "wait_for_trigger": {
                        "platform": "event",
                        "event_type": "balena_cloud_fleet_health_response",
                    },
                    "timeout": 30,
                },
                {
                    "condition": "template",
                    "value_template": "{{ wait.trigger.event.data.critical_devices > 0 }}",
                },
                {
                    "service": "notify.admin",
                    "data": {
                        "title": "Fleet Health Alert",
                        "message": "Fleet has {{ wait.trigger.event.data.critical_devices }} critical devices.",
                    },
                },
            ],
        },
    }


@pytest.fixture
def performance_test_data():
    """Performance test data with large datasets."""

    # Generate large fleet and device datasets
    fleets = []
    devices = []

    for fleet_id in range(1000, 1050):  # 50 fleets
        fleets.append({
            "id": fleet_id,
            "app_name": f"performance-fleet-{fleet_id}",
            "slug": f"test_user/performance-fleet-{fleet_id}",
            "device_type": "raspberrypi4-64",
            "created_at": "2024-01-01T00:00:00.000Z",
        })

        # 20 devices per fleet = 1000 total devices
        for device_idx in range(20):
            device_id = fleet_id * 100 + device_idx
            devices.append({
                "id": device_id,
                "uuid": f"perf-device-{device_id}",
                "device_name": f"performance-device-{device_id}",
                "device_type": "raspberrypi4-64",
                "belongs_to__application": {"__id": fleet_id, "app_name": f"performance-fleet-{fleet_id}"},
                "is_online": device_idx % 4 != 0,  # 75% online rate
                "status": "Idle" if device_idx % 4 != 0 else "Offline",
                "ip_address": f"192.168.1.{100 + device_idx}" if device_idx % 4 != 0 else None,
                "mac_address": f"b8:27:eb:12:{device_idx:02x}:56",
                "os_version": "balenaOS 2024.1.1",
                "supervisor_version": "14.13.5",
                "last_connectivity_event": "2024-01-15T10:30:00.000Z",
                "created_at": "2024-01-01T12:00:00.000Z",
            })

    return {
        "fleets": fleets,
        "devices": devices,
    }


@pytest.fixture
def security_test_scenarios():
    """Security test scenarios and data."""
    return {
        "invalid_tokens": [
            "",
            "invalid_token",
            "expired_token_12345",
            "malicious_token_<script>",
            "../../etc/passwd",
            "'; DROP TABLE devices; --",
        ],
        "malicious_inputs": {
            "device_uuid": [
                "../../../etc/passwd",
                "<script>alert('xss')</script>",
                "'; DROP TABLE devices; --",
                "device-uuid-1; rm -rf /",
                {"malicious": "object"},
                ["array", "input"],
            ],
            "service_name": [
                "../../../bin/bash",
                "; rm -rf /",
                "service'; cat /etc/passwd #",
                "<script>alert('xss')</script>",
            ],
            "environment_variables": {
                "../../../etc/passwd": "malicious_value",
                "NORMAL_VAR": "'; cat /etc/passwd #",
                "XSS_VAR": "<script>alert('xss')</script>",
                "SQL_INJECTION": "'; DROP TABLE devices; --",
            },
        },
        "rate_limit_scenarios": [
            {"requests_per_second": 10, "duration": 60},
            {"requests_per_second": 50, "duration": 30},
            {"requests_per_second": 100, "duration": 10},
        ],
    }


# Test data validation helpers
def validate_device_data(device_data: Dict[str, Any]) -> bool:
    """Validate device data structure."""
    required_fields = ["uuid", "device_name", "device_type", "is_online", "status"]
    return all(field in device_data for field in required_fields)


def validate_fleet_data(fleet_data: Dict[str, Any]) -> bool:
    """Validate fleet data structure."""
    required_fields = ["id", "app_name", "slug", "device_type"]
    return all(field in fleet_data for field in required_fields)


def validate_metrics_data(metrics_data: Dict[str, Any]) -> bool:
    """Validate metrics data structure."""
    expected_fields = ["cpu_usage", "memory_usage", "memory_total", "storage_usage", "storage_total"]
    return any(field in metrics_data for field in expected_fields)
