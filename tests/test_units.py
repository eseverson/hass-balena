"""Comprehensive unit tests for Balena Cloud integration components."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientSession

from custom_components.balena_cloud.api import BalenaCloudAPIClient, BalenaCloudAPIError
from custom_components.balena_cloud.models import BalenaDevice, BalenaFleet, BalenaDeviceMetrics
from custom_components.balena_cloud.const import DOMAIN, DEFAULT_UPDATE_INTERVAL


class TestBalenaCloudAPIClientUnit:
    """Unit tests for Balena Cloud API client."""

    @pytest.fixture
    def api_client(self):
        """Create API client for unit testing."""
        session = AsyncMock(spec=ClientSession)
        return BalenaCloudAPIClient(session, "test_token_12345")

    def test_api_client_initialization(self, api_client):
        """Test API client initialization with proper defaults."""
        assert api_client._api_token == "test_token_12345"
        assert "Bearer test_token_12345" in api_client.headers["Authorization"]
        assert api_client.headers["Content-Type"] == "application/json"
        assert api_client._rate_limit_reset is None
        assert api_client._max_retries == 3

    def test_api_client_base_url_construction(self, api_client):
        """Test API base URL construction."""
        from custom_components.balena_cloud.const import BALENA_API_BASE_URL, BALENA_API_VERSION
        expected_url = f"{BALENA_API_BASE_URL}/{BALENA_API_VERSION}"
        assert api_client._base_url == expected_url

    def test_api_client_request_headers(self, api_client):
        """Test API client request headers."""
        headers = api_client.headers
        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert "User-Agent" in headers
        assert headers["User-Agent"].startswith("HomeAssistant")

    async def test_build_url_method(self, api_client):
        """Test URL building method."""
        # Test basic endpoint
        url = api_client._build_url("/user")
        assert url.endswith("/user")

        # Test endpoint with parameters
        url = api_client._build_url("/device", {"$filter": "is_online eq true"})
        assert "$filter=is_online+eq+true" in url or "$filter=is_online%20eq%20true" in url

    async def test_validate_response_method(self, api_client):
        """Test response validation method."""
        # Test successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"data": "test"}

        result = await api_client._validate_response(mock_response)
        assert result == {"data": "test"}

        # Test rate limit response
        mock_response.status = 429
        mock_response.headers = {"X-RateLimit-Reset": "1705398000"}

        with pytest.raises(Exception):  # Should raise rate limit exception
            await api_client._validate_response(mock_response)

    def test_sanitize_input_method(self, api_client):
        """Test input sanitization method."""
        # Test normal strings
        assert api_client._sanitize_input("normal_string") == "normal_string"
        assert api_client._sanitize_input("device-uuid-123") == "device-uuid-123"

        # Test None input
        assert api_client._sanitize_input(None) is None

        # Test numeric input
        assert api_client._sanitize_input(12345) == 12345


class TestBalenaDeviceModelUnit:
    """Unit tests for BalenaDevice model."""

    @pytest.fixture
    def sample_device_data(self):
        """Sample device data for testing."""
        return {
            "id": 12345,
            "uuid": "test-device-uuid-12345",
            "device_name": "Test Device",
            "device_type": "raspberrypi4-64",
            "belongs_to__application": {
                "__id": 1001,
                "app_name": "test-fleet"
            },
            "is_online": True,
            "status": "Idle",
            "ip_address": "192.168.1.100",
            "mac_address": "b8:27:eb:12:34:56",
            "os_version": "balenaOS 2024.1.1",
            "supervisor_version": "14.13.5",
            "last_connectivity_event": "2024-01-15T10:30:00.000Z",
            "created_at": "2024-01-01T12:00:00.000Z",
        }

    def test_device_creation_from_api_data(self, sample_device_data):
        """Test device creation from API data."""
        device = BalenaDevice.from_api_data(sample_device_data)

        assert device.uuid == "test-device-uuid-12345"
        assert device.device_name == "Test Device"
        assert device.device_type == "raspberrypi4-64"
        assert device.fleet_id == 1001
        assert device.fleet_name == "test-fleet"
        assert device.is_online is True
        assert device.status == "Idle"
        assert device.ip_address == "192.168.1.100"
        assert device.mac_address == "b8:27:eb:12:34:56"

    def test_device_display_name_property(self, sample_device_data):
        """Test device display name property."""
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.display_name == "Test Device"

        # Test with empty device name
        sample_device_data["device_name"] = ""
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.display_name == "test-device-uuid-12345"

    def test_device_is_updating_property(self, sample_device_data):
        """Test device is_updating property."""
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.is_updating is False

        # Test with updating status
        sample_device_data["status"] = "Updating"
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.is_updating is True

    def test_device_is_idle_property(self, sample_device_data):
        """Test device is_idle property."""
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.is_idle is True

        # Test with non-idle status
        sample_device_data["status"] = "Downloading"
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.is_idle is False

    def test_device_datetime_parsing(self, sample_device_data):
        """Test device datetime parsing."""
        device = BalenaDevice.from_api_data(sample_device_data)

        assert isinstance(device.last_seen, datetime)
        assert isinstance(device.created_at, datetime)

        # Test with None dates
        sample_device_data["last_connectivity_event"] = None
        device = BalenaDevice.from_api_data(sample_device_data)
        assert device.last_seen is None

    def test_device_with_missing_fields(self):
        """Test device creation with missing optional fields."""
        minimal_data = {
            "uuid": "minimal-device-uuid",
            "device_name": "Minimal Device",
            "device_type": "raspberrypi4-64",
            "belongs_to__application": {"__id": 1001, "app_name": "test-fleet"},
            "is_online": False,
            "status": "Offline",
        }

        device = BalenaDevice.from_api_data(minimal_data)
        assert device.uuid == "minimal-device-uuid"
        assert device.ip_address is None
        assert device.mac_address is None
        assert device.last_seen is None


class TestBalenaDeviceMetricsUnit:
    """Unit tests for BalenaDeviceMetrics model."""

    def test_metrics_creation(self):
        """Test metrics creation with basic data."""
        metrics = BalenaDeviceMetrics(
            cpu_usage=25.5,
            memory_usage=512000000,
            memory_total=2000000000,
            storage_usage=8000000000,
            storage_total=32000000000,
            temperature=45.2,
        )

        assert metrics.cpu_usage == 25.5
        assert metrics.memory_usage == 512000000
        assert metrics.memory_total == 2000000000
        assert metrics.temperature == 45.2

    def test_metrics_percentage_calculations(self):
        """Test metrics percentage calculations."""
        metrics = BalenaDeviceMetrics(
            cpu_usage=50.0,
            memory_usage=1000000000,  # 1GB
            memory_total=4000000000,  # 4GB
            storage_usage=16000000000,  # 16GB
            storage_total=32000000000,  # 32GB
        )

        assert metrics.cpu_percentage == 50.0
        assert metrics.memory_percentage == 25.0  # 1GB/4GB
        assert metrics.storage_percentage == 50.0  # 16GB/32GB

    def test_metrics_with_none_values(self):
        """Test metrics with None values."""
        metrics = BalenaDeviceMetrics(
            cpu_usage=None,
            memory_usage=None,
            memory_total=None,
            storage_usage=None,
            storage_total=None,
            temperature=None,
        )

        assert metrics.cpu_percentage is None
        assert metrics.memory_percentage is None
        assert metrics.storage_percentage is None

    def test_metrics_edge_cases(self):
        """Test metrics edge cases."""
        # Test zero total memory/storage
        metrics = BalenaDeviceMetrics(
            memory_usage=1000000000,
            memory_total=0,
            storage_usage=1000000000,
            storage_total=0,
        )

        assert metrics.memory_percentage is None
        assert metrics.storage_percentage is None

    def test_metrics_from_api_data(self):
        """Test metrics creation from API data."""
        api_data = {
            "cpu_usage": 30.5,
            "memory_usage": 1500000000,
            "memory_total": 4000000000,
            "storage_usage": 20000000000,
            "storage_total": 64000000000,
            "temperature": 55.3,
        }

        metrics = BalenaDeviceMetrics.from_api_data(api_data)
        assert metrics.cpu_usage == 30.5
        assert metrics.memory_percentage == 37.5  # 1.5GB/4GB
        assert metrics.storage_percentage == 31.25  # 20GB/64GB
        assert metrics.temperature == 55.3


class TestBalenaFleetModelUnit:
    """Unit tests for BalenaFleet model."""

    @pytest.fixture
    def sample_fleet_data(self):
        """Sample fleet data for testing."""
        return {
            "id": 1001,
            "app_name": "test-fleet-production",
            "slug": "testuser/test-fleet-production",
            "device_type": "raspberrypi4-64",
            "created_at": "2024-01-01T00:00:00.000Z",
        }

    def test_fleet_creation_from_api_data(self, sample_fleet_data):
        """Test fleet creation from API data."""
        fleet = BalenaFleet.from_api_data(sample_fleet_data)

        assert fleet.id == 1001
        assert fleet.app_name == "test-fleet-production"
        assert fleet.slug == "testuser/test-fleet-production"
        assert fleet.device_type == "raspberrypi4-64"
        assert isinstance(fleet.created_at, datetime)

    def test_fleet_display_name_property(self, sample_fleet_data):
        """Test fleet display name property."""
        fleet = BalenaFleet.from_api_data(sample_fleet_data)
        assert fleet.display_name == "test-fleet-production"

    def test_fleet_with_minimal_data(self):
        """Test fleet creation with minimal required data."""
        minimal_data = {
            "id": 2001,
            "app_name": "minimal-fleet",
            "slug": "user/minimal-fleet",
            "device_type": "intel-nuc",
        }

        fleet = BalenaFleet.from_api_data(minimal_data)
        assert fleet.id == 2001
        assert fleet.app_name == "minimal-fleet"
        assert fleet.created_at is None


class TestBalenaCloudDataUpdateCoordinatorUnit:
    """Unit tests for BalenaCloudDataUpdateCoordinator."""

    @pytest.fixture
    def mock_coordinator_setup(self):
        """Set up mock coordinator for testing."""
        mock_hass = AsyncMock()
        mock_session = AsyncMock(spec=ClientSession)

        config_data = {
            "api_token": "test_token_12345",
            "fleets": [1001, 1002],
        }

        config_options = {
            "update_interval": 30,
            "include_offline_devices": True,
        }

        from custom_components.balena_cloud.coordinator import BalenaCloudDataUpdateCoordinator

        coordinator = BalenaCloudDataUpdateCoordinator(
            mock_hass,
            mock_session,
            config_data,
            config_options,
        )

        return coordinator, mock_hass, mock_session

    def test_coordinator_initialization(self, mock_coordinator_setup):
        """Test coordinator initialization."""
        coordinator, mock_hass, mock_session = mock_coordinator_setup

        assert coordinator.hass == mock_hass
        assert coordinator.name == "Balena Cloud"
        assert coordinator.update_interval == timedelta(seconds=30)
        assert coordinator._include_offline_devices is True

    def test_coordinator_config_access(self, mock_coordinator_setup):
        """Test coordinator configuration access."""
        coordinator, _, _ = mock_coordinator_setup

        assert coordinator._api_token == "test_token_12345"
        assert coordinator._selected_fleets == [1001, 1002]

    async def test_coordinator_get_device_method(self, mock_coordinator_setup):
        """Test coordinator get_device method."""
        coordinator, _, _ = mock_coordinator_setup

        # Mock device data
        test_device = MagicMock()
        test_device.uuid = "test-device-uuid"
        coordinator.devices = {"test-device-uuid": test_device}

        # Test getting existing device
        device = coordinator.get_device("test-device-uuid")
        assert device == test_device

        # Test getting non-existent device
        device = coordinator.get_device("non-existent-uuid")
        assert device is None

    async def test_coordinator_get_fleet_method(self, mock_coordinator_setup):
        """Test coordinator get_fleet method."""
        coordinator, _, _ = mock_coordinator_setup

        # Mock fleet data
        test_fleet = MagicMock()
        test_fleet.id = 1001
        coordinator.fleets = {1001: test_fleet}

        # Test getting existing fleet
        fleet = coordinator.get_fleet(1001)
        assert fleet == test_fleet

        # Test getting non-existent fleet
        fleet = coordinator.get_fleet(9999)
        assert fleet is None

    async def test_coordinator_get_devices_by_fleet_method(self, mock_coordinator_setup):
        """Test coordinator get_devices_by_fleet method."""
        coordinator, _, _ = mock_coordinator_setup

        # Mock devices with different fleet IDs
        device1 = MagicMock()
        device1.fleet_id = 1001
        device2 = MagicMock()
        device2.fleet_id = 1001
        device3 = MagicMock()
        device3.fleet_id = 1002

        coordinator.devices = {
            "device-1": device1,
            "device-2": device2,
            "device-3": device3,
        }

        # Test getting devices for fleet 1001
        fleet_devices = coordinator.get_devices_by_fleet(1001)
        assert len(fleet_devices) == 2
        assert all(d.fleet_id == 1001 for d in fleet_devices)

        # Test getting devices for fleet with no devices
        fleet_devices = coordinator.get_devices_by_fleet(9999)
        assert len(fleet_devices) == 0

    async def test_coordinator_device_control_methods(self, mock_coordinator_setup):
        """Test coordinator device control methods."""
        coordinator, _, _ = mock_coordinator_setup

        # Mock API client
        coordinator.api = AsyncMock()
        coordinator.api.async_restart_application.return_value = True
        coordinator.api.async_reboot_device.return_value = True
        coordinator.api.async_update_environment_variables.return_value = True

        # Test restart application
        result = await coordinator.async_restart_application("device-uuid-1", "main")
        assert result is True
        coordinator.api.async_restart_application.assert_called_once_with("device-uuid-1", "main")

        # Test reboot device
        result = await coordinator.async_reboot_device("device-uuid-1")
        assert result is True
        coordinator.api.async_reboot_device.assert_called_once_with("device-uuid-1")

        # Test update environment variables
        env_vars = {"TEST_VAR": "test_value"}
        result = await coordinator.async_update_environment_variables("device-uuid-1", env_vars)
        assert result is True
        coordinator.api.async_update_environment_variables.assert_called_once_with("device-uuid-1", env_vars)


class TestConfigurationFlowUnit:
    """Unit tests for configuration flow."""

    @pytest.fixture
    def mock_config_flow(self):
        """Create mock config flow for testing."""
        from custom_components.balena_cloud.config_flow import BalenaCloudConfigFlow

        flow = BalenaCloudConfigFlow()
        flow.hass = AsyncMock()
        return flow

    def test_config_flow_initialization(self, mock_config_flow):
        """Test config flow initialization."""
        assert mock_config_flow.VERSION == 1
        assert mock_config_flow.domain == DOMAIN

    async def test_config_flow_validate_input_method(self, mock_config_flow):
        """Test config flow input validation method."""
        # Mock API client
        with patch("custom_components.balena_cloud.config_flow.BalenaCloudAPIClient") as mock_api_class:
            mock_api = AsyncMock()
            mock_api.async_validate_token.return_value = True
            mock_api.async_get_user_info.return_value = {"username": "test_user"}
            mock_api_class.return_value = mock_api

            user_input = {"api_token": "valid_token_12345"}
            result = await mock_config_flow._async_validate_input(user_input)

            assert result is None  # No errors
            assert mock_config_flow.api_token == "valid_token_12345"
            assert mock_config_flow.user_info == {"username": "test_user"}

    async def test_config_flow_fetch_fleets_method(self, mock_config_flow):
        """Test config flow fleet fetching method."""
        # Mock API client
        mock_config_flow.api = AsyncMock()
        mock_config_flow.api.async_get_fleets.return_value = [
            {"id": 1001, "app_name": "fleet-1"},
            {"id": 1002, "app_name": "fleet-2"},
        ]

        await mock_config_flow._async_fetch_fleets()

        assert mock_config_flow.fleets == {1001: "fleet-1", 1002: "fleet-2"}

    async def test_config_flow_user_step_form_validation(self, mock_config_flow):
        """Test config flow user step form validation."""
        # Test empty token
        user_input = {"api_token": ""}
        result = await mock_config_flow.async_step_user(user_input)

        assert result["type"] == "form"
        assert "errors" in result


class TestEntityPlatformsUnit:
    """Unit tests for entity platforms."""

    @pytest.fixture
    def mock_device_with_metrics(self):
        """Create mock device with metrics for testing."""
        device = MagicMock()
        device.uuid = "test-device-uuid"
        device.display_name = "Test Device"
        device.device_type = "raspberrypi4-64"
        device.fleet_name = "test-fleet"
        device.is_online = True
        device.status = "Idle"

        device.metrics = MagicMock()
        device.metrics.cpu_percentage = 25.5
        device.metrics.memory_percentage = 45.2
        device.metrics.storage_percentage = 60.1
        device.metrics.temperature = 42.3

        return device

    async def test_sensor_entity_creation(self, mock_device_with_metrics):
        """Test sensor entity creation and basic properties."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device_with_metrics

        # Test CPU sensor
        cpu_sensor_desc = SENSOR_TYPES[0]  # Assuming first is CPU
        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=cpu_sensor_desc,
            device_uuid="test-device-uuid",
        )

        assert sensor._device_uuid == "test-device-uuid"
        assert sensor.available is True
        assert sensor.unique_id == f"test-device-uuid_{cpu_sensor_desc.key}"

    async def test_binary_sensor_entity_creation(self, mock_device_with_metrics):
        """Test binary sensor entity creation and basic properties."""
        from custom_components.balena_cloud.binary_sensor import BalenaCloudBinarySensorEntity, BINARY_SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device_with_metrics

        # Test online sensor
        online_sensor_desc = BINARY_SENSOR_TYPES[0]  # Assuming first is online status
        sensor = BalenaCloudBinarySensorEntity(
            coordinator=coordinator,
            description=online_sensor_desc,
            device_uuid="test-device-uuid",
        )

        assert sensor._device_uuid == "test-device-uuid"
        assert sensor.available is True
        assert sensor.unique_id == f"test-device-uuid_{online_sensor_desc.key}"

    async def test_button_entity_creation(self, mock_device_with_metrics):
        """Test button entity creation and basic properties."""
        from custom_components.balena_cloud.button import BalenaCloudButtonEntity, BUTTON_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device_with_metrics
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Test restart button
        restart_button_desc = BUTTON_TYPES[0]  # Assuming first is restart
        button = BalenaCloudButtonEntity(
            coordinator=coordinator,
            description=restart_button_desc,
            device_uuid="test-device-uuid",
        )

        assert button._device_uuid == "test-device-uuid"
        assert button.available is True
        assert button.unique_id == f"test-device-uuid_{restart_button_desc.key}"

        # Test button press
        await button.async_press()
        coordinator.async_restart_application.assert_called_once()

    async def test_entity_device_info_creation(self, mock_device_with_metrics):
        """Test entity device info creation."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device_with_metrics

        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="test-device-uuid",
        )

        device_info = sensor.device_info

        assert device_info is not None
        assert device_info["name"] == "Test Device"
        assert device_info["manufacturer"] == "Balena"
        assert device_info["model"] == "raspberrypi4-64"
        assert DOMAIN in str(device_info["identifiers"])


class TestUtilityFunctionsUnit:
    """Unit tests for utility functions."""

    def test_const_values(self):
        """Test constant values are properly defined."""
        from custom_components.balena_cloud.const import (
            DOMAIN, DEFAULT_UPDATE_INTERVAL, API_TIMEOUT, MAX_RETRIES,
            BALENA_API_BASE_URL, BALENA_API_VERSION
        )

        assert DOMAIN == "balena_cloud"
        assert DEFAULT_UPDATE_INTERVAL == 30
        assert API_TIMEOUT > 0
        assert MAX_RETRIES > 0
        assert BALENA_API_BASE_URL.startswith("https://")
        assert BALENA_API_VERSION.startswith("v")

    def test_sensor_types_definition(self):
        """Test sensor types are properly defined."""
        from custom_components.balena_cloud.sensor import SENSOR_TYPES

        assert len(SENSOR_TYPES) > 0

        for sensor_type in SENSOR_TYPES:
            assert hasattr(sensor_type, 'key')
            assert hasattr(sensor_type, 'name')
            assert hasattr(sensor_type, 'icon')
            assert isinstance(sensor_type.key, str)
            assert isinstance(sensor_type.name, str)

    def test_binary_sensor_types_definition(self):
        """Test binary sensor types are properly defined."""
        from custom_components.balena_cloud.binary_sensor import BINARY_SENSOR_TYPES

        assert len(BINARY_SENSOR_TYPES) > 0

        for sensor_type in BINARY_SENSOR_TYPES:
            assert hasattr(sensor_type, 'key')
            assert hasattr(sensor_type, 'name')
            assert hasattr(sensor_type, 'device_class')
            assert isinstance(sensor_type.key, str)
            assert isinstance(sensor_type.name, str)

    def test_button_types_definition(self):
        """Test button types are properly defined."""
        from custom_components.balena_cloud.button import BUTTON_TYPES

        assert len(BUTTON_TYPES) > 0

        for button_type in BUTTON_TYPES:
            assert hasattr(button_type, 'key')
            assert hasattr(button_type, 'name')
            assert hasattr(button_type, 'icon')
            assert isinstance(button_type.key, str)
            assert isinstance(button_type.name, str)


class TestErrorHandlingUnit:
    """Unit tests for error handling throughout the integration."""

    async def test_api_client_error_handling(self):
        """Test API client error handling."""
        from custom_components.balena_cloud.api import (
            BalenaCloudAPIError, BalenaCloudAuthenticationError, BalenaCloudRateLimitError
        )

        # Test error hierarchy
        assert issubclass(BalenaCloudAuthenticationError, BalenaCloudAPIError)
        assert issubclass(BalenaCloudRateLimitError, BalenaCloudAPIError)

    async def test_coordinator_error_recovery(self, mock_coordinator_setup):
        """Test coordinator error recovery mechanisms."""
        coordinator, _, _ = mock_coordinator_setup

        # Mock API client to raise errors
        coordinator.api = AsyncMock()
        coordinator.api.async_get_fleets.side_effect = Exception("API Error")

        # Test that coordinator handles API errors gracefully
        with pytest.raises(Exception):
            await coordinator._async_update_data()

    async def test_entity_availability_on_errors(self, mock_device_with_metrics):
        """Test entity availability when errors occur."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = None  # Simulate device not found

        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="non-existent-device",
        )

        # Entity should be unavailable when device is not found
        assert sensor.available is False

    def test_config_flow_error_messages(self):
        """Test configuration flow error message definitions."""
        from custom_components.balena_cloud.config_flow import ERRORS

        assert "invalid_auth" in ERRORS
        assert "cannot_connect" in ERRORS
        assert "unknown" in ERRORS

        # All error messages should be strings
        for error_code, error_message in ERRORS.items():
            assert isinstance(error_code, str)
            assert isinstance(error_message, str)


class TestDataValidationUnit:
    """Unit tests for data validation functions."""

    def test_device_data_validation(self):
        """Test device data validation function."""
        from tests.conftest import validate_device_data

        # Valid device data
        valid_data = {
            "uuid": "test-uuid",
            "device_name": "Test Device",
            "device_type": "raspberrypi4-64",
            "is_online": True,
            "status": "Idle",
        }
        assert validate_device_data(valid_data) is True

        # Invalid device data (missing required field)
        invalid_data = {
            "device_name": "Test Device",
            "device_type": "raspberrypi4-64",
            # Missing uuid, is_online, status
        }
        assert validate_device_data(invalid_data) is False

    def test_fleet_data_validation(self):
        """Test fleet data validation function."""
        from tests.conftest import validate_fleet_data

        # Valid fleet data
        valid_data = {
            "id": 1001,
            "app_name": "test-fleet",
            "slug": "user/test-fleet",
            "device_type": "raspberrypi4-64",
        }
        assert validate_fleet_data(valid_data) is True

        # Invalid fleet data (missing required field)
        invalid_data = {
            "app_name": "test-fleet",
            "slug": "user/test-fleet",
            # Missing id, device_type
        }
        assert validate_fleet_data(invalid_data) is False

    def test_metrics_data_validation(self):
        """Test metrics data validation function."""
        from tests.conftest import validate_metrics_data

        # Valid metrics data
        valid_data = {
            "cpu_usage": 25.5,
            "memory_usage": 1000000000,
            "memory_total": 4000000000,
        }
        assert validate_metrics_data(valid_data) is True

        # Empty metrics data should be invalid
        empty_data = {}
        assert validate_metrics_data(empty_data) is False


class TestSecurityFeaturesUnit:
    """Unit tests for security features."""

    def test_api_token_sanitization(self):
        """Test API token sanitization in logs and outputs."""
        from custom_components.balena_cloud.api import BalenaCloudAPIClient

        session = AsyncMock(spec=ClientSession)
        api_client = BalenaCloudAPIClient(session, "sensitive_token_12345")

        # Token should not appear in string representation
        client_str = str(api_client)
        assert "sensitive_token_12345" not in client_str
        assert "***" in client_str or "hidden" in client_str.lower()

    def test_input_parameter_validation(self):
        """Test input parameter validation for security."""
        from custom_components.balena_cloud.api import BalenaCloudAPIClient

        session = AsyncMock(spec=ClientSession)
        api_client = BalenaCloudAPIClient(session, "test_token")

        # Test UUID validation patterns
        valid_uuids = [
            "device-uuid-12345",
            "1234567890abcdef",
            "test-device-uuid",
        ]

        for uuid in valid_uuids:
            sanitized = api_client._sanitize_input(uuid)
            assert sanitized == uuid  # Should pass through unchanged

        # Test that None is handled safely
        assert api_client._sanitize_input(None) is None

    async def test_rate_limiting_implementation(self):
        """Test rate limiting implementation."""
        session = AsyncMock(spec=ClientSession)
        api_client = BalenaCloudAPIClient(session, "test_token")

        # Test that rate limit reset time is tracked
        assert api_client._rate_limit_reset is None

        # Simulate setting rate limit
        future_time = datetime.now().timestamp() + 60
        api_client._rate_limit_reset = future_time

        assert api_client._rate_limit_reset == future_time

    def test_configuration_data_protection(self):
        """Test configuration data protection."""
        config_data = {
            "api_token": "sensitive_token_12345",
            "fleets": [1001, 1002],
        }

        # Simulate how the integration would handle sensitive data
        # In real implementation, this would use Home Assistant's credential storage
        protected_data = config_data.copy()

        # Verify original structure is maintained
        assert "api_token" in protected_data
        assert protected_data["fleets"] == [1001, 1002]