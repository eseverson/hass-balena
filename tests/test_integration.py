"""Home Assistant integration tests for Balena Cloud."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.balena_cloud import async_setup_entry, async_unload_entry
from custom_components.balena_cloud.const import DOMAIN


class TestHomeAssistantIntegration:
    """Test Home Assistant integration setup and teardown."""

    @pytest.mark.asyncio
    async def test_integration_setup_success(self, hass: HomeAssistant, mock_config_entry):
        """Test successful integration setup."""

        with patch("custom_components.balena_cloud.BalenaCloudDataUpdateCoordinator") as mock_coordinator, \
             patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"):

            # Configure coordinator mock
            coordinator_instance = AsyncMock()
            coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.return_value = coordinator_instance

            # Create config entry
            config_entry = ConfigEntry(
                version=1,
                domain=DOMAIN,
                title="Balena Cloud Test",
                data=mock_config_entry["data"],
                options=mock_config_entry["options"],
                entry_id="test_entry_id",
                source="user",
            )

            # Test setup
            result = await async_setup_entry(hass, config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert config_entry.entry_id in hass.data[DOMAIN]

            # Verify coordinator was created and first refresh called
            mock_coordinator.assert_called_once()
            coordinator_instance.async_config_entry_first_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_unload_success(self, hass: HomeAssistant, mock_config_entry):
        """Test successful integration unload."""

        with patch("custom_components.balena_cloud.BalenaCloudDataUpdateCoordinator") as mock_coordinator, \
             patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"):

            coordinator_instance = AsyncMock()
            coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.return_value = coordinator_instance

            config_entry = ConfigEntry(
                version=1,
                domain=DOMAIN,
                title="Balena Cloud Test",
                data=mock_config_entry["data"],
                options=mock_config_entry["options"],
                entry_id="test_entry_id",
                source="user",
            )

            # Set up integration first
            await async_setup_entry(hass, config_entry)

            # Mock platform unloading
            with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms") as mock_unload:
                mock_unload.return_value = True

                # Test unload
                result = await async_unload_entry(hass, config_entry)

                assert result is True
                assert config_entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_integration_setup_failure(self, hass: HomeAssistant, mock_config_entry):
        """Test integration setup failure handling."""

        with patch("custom_components.balena_cloud.BalenaCloudDataUpdateCoordinator") as mock_coordinator, \
             patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"):

            # Configure coordinator to fail
            coordinator_instance = AsyncMock()
            coordinator_instance.async_config_entry_first_refresh.side_effect = Exception("API Error")
            mock_coordinator.return_value = coordinator_instance

            config_entry = ConfigEntry(
                version=1,
                domain=DOMAIN,
                title="Balena Cloud Test",
                data=mock_config_entry["data"],
                options=mock_config_entry["options"],
                entry_id="test_entry_id",
                source="user",
            )

            # Test setup failure
            with pytest.raises(Exception):
                await async_setup_entry(hass, config_entry)


class TestEntityPlatformIntegration:
    """Test entity platform integration."""

    @pytest.fixture
    async def setup_integration(self, hass: HomeAssistant, mock_config_entry, mock_balena_api_response):
        """Set up integration with mock data."""

        with patch("custom_components.balena_cloud.BalenaCloudDataUpdateCoordinator") as mock_coordinator, \
             patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"):

            # Configure coordinator with test data
            coordinator_instance = AsyncMock()
            coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            coordinator_instance.devices = {
                "device-uuid-1": MagicMock(uuid="device-uuid-1", display_name="Test Device 1"),
                "device-uuid-2": MagicMock(uuid="device-uuid-2", display_name="Test Device 2"),
            }
            coordinator_instance.fleets = {
                1001: MagicMock(id=1001, app_name="test-fleet-1"),
                1002: MagicMock(id=1002, app_name="test-fleet-2"),
            }
            mock_coordinator.return_value = coordinator_instance

            config_entry = ConfigEntry(
                version=1,
                domain=DOMAIN,
                title="Balena Cloud Test",
                data=mock_config_entry["data"],
                options=mock_config_entry["options"],
                entry_id="test_entry_id",
                source="user",
            )

            await async_setup_entry(hass, config_entry)

            return coordinator_instance

    @pytest.mark.asyncio
    async def test_sensor_platform_setup(self, hass: HomeAssistant, setup_integration):
        """Test sensor platform setup."""
        coordinator = await setup_integration

        # Import and test sensor platform
        from custom_components.balena_cloud.sensor import async_setup_entry as sensor_setup

        config_entry = MagicMock()
        config_entry.entry_id = "test_entry_id"

        with patch("homeassistant.helpers.entity_platform.AddEntitiesCallback") as mock_add_entities:

            # Mock the data structure in hass
            hass.data[DOMAIN] = {"test_entry_id": coordinator}

            await sensor_setup(hass, config_entry, mock_add_entities)

            # Verify entities were added
            mock_add_entities.assert_called_once()

            # Get the entities that were added
            added_entities = mock_add_entities.call_args[0][0]
            assert len(added_entities) > 0

    @pytest.mark.asyncio
    async def test_binary_sensor_platform_setup(self, hass: HomeAssistant, setup_integration):
        """Test binary sensor platform setup."""
        coordinator = await setup_integration

        from custom_components.balena_cloud.binary_sensor import async_setup_entry as binary_sensor_setup

        config_entry = MagicMock()
        config_entry.entry_id = "test_entry_id"

        with patch("homeassistant.helpers.entity_platform.AddEntitiesCallback") as mock_add_entities:

            hass.data[DOMAIN] = {"test_entry_id": coordinator}

            await binary_sensor_setup(hass, config_entry, mock_add_entities)

            mock_add_entities.assert_called_once()
            added_entities = mock_add_entities.call_args[0][0]
            assert len(added_entities) > 0

    @pytest.mark.asyncio
    async def test_button_platform_setup(self, hass: HomeAssistant, setup_integration):
        """Test button platform setup."""
        coordinator = await setup_integration

        from custom_components.balena_cloud.button import async_setup_entry as button_setup

        config_entry = MagicMock()
        config_entry.entry_id = "test_entry_id"

        with patch("homeassistant.helpers.entity_platform.AddEntitiesCallback") as mock_add_entities:

            hass.data[DOMAIN] = {"test_entry_id": coordinator}

            await button_setup(hass, config_entry, mock_add_entities)

            mock_add_entities.assert_called_once()
            added_entities = mock_add_entities.call_args[0][0]
            assert len(added_entities) > 0


class TestServiceIntegration:
    """Test service integration and calls."""

    @pytest.fixture
    async def setup_services(self, hass: HomeAssistant, mock_config_entry):
        """Set up services for testing."""

        from custom_components.balena_cloud.services import get_service_handler

        service_handler = get_service_handler(hass)

        # Mock coordinator
        coordinator = AsyncMock()
        coordinator.devices = {
            "device-uuid-1": MagicMock(
                uuid="device-uuid-1",
                display_name="Test Device 1",
                is_online=True,
                is_updating=False
            ),
        }
        coordinator.async_restart_application = AsyncMock(return_value=True)
        coordinator.async_reboot_device = AsyncMock(return_value=True)
        coordinator.async_update_environment_variables = AsyncMock(return_value=True)

        service_handler.register_coordinator("test_entry_id", coordinator)
        await service_handler.async_setup_services()

        return service_handler, coordinator

    @pytest.mark.asyncio
    async def test_restart_application_service(self, hass: HomeAssistant, setup_services):
        """Test restart application service call."""
        service_handler, coordinator = await setup_services

        # Test successful restart
        await hass.services.async_call(
            DOMAIN,
            "restart_application",
            {
                "device_uuid": "device-uuid-1",
                "confirm": True,
            },
            blocking=True,
        )

        coordinator.async_restart_application.assert_called_once_with("device-uuid-1", None)

    @pytest.mark.asyncio
    async def test_reboot_device_service(self, hass: HomeAssistant, setup_services):
        """Test reboot device service call."""
        service_handler, coordinator = await setup_services

        await hass.services.async_call(
            DOMAIN,
            "reboot_device",
            {
                "device_uuid": "device-uuid-1",
                "confirm": True,
            },
            blocking=True,
        )

        coordinator.async_reboot_device.assert_called_once_with("device-uuid-1")

    @pytest.mark.asyncio
    async def test_update_environment_service(self, hass: HomeAssistant, setup_services):
        """Test update environment variables service call."""
        service_handler, coordinator = await setup_services

        await hass.services.async_call(
            DOMAIN,
            "update_environment",
            {
                "device_uuid": "device-uuid-1",
                "variables": {"TEST_VAR": "test_value"},
            },
            blocking=True,
        )

        coordinator.async_update_environment_variables.assert_called_once_with(
            "device-uuid-1", {"TEST_VAR": "test_value"}
        )

    @pytest.mark.asyncio
    async def test_service_calls_without_confirmation(self, hass: HomeAssistant, setup_services):
        """Test service calls without required confirmation."""
        service_handler, coordinator = await setup_services

        # Should not execute without confirmation
        await hass.services.async_call(
            DOMAIN,
            "restart_application",
            {
                "device_uuid": "device-uuid-1",
                "confirm": False,
            },
            blocking=True,
        )

        # Should not have been called
        coordinator.async_restart_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_operations(self, hass: HomeAssistant, setup_services):
        """Test bulk operation services."""
        service_handler, coordinator = await setup_services

        # Mock multiple devices
        coordinator.get_devices_by_fleet.return_value = [
            MagicMock(uuid="device-uuid-1", is_online=True),
            MagicMock(uuid="device-uuid-2", is_online=True),
        ]

        await hass.services.async_call(
            DOMAIN,
            "bulk_restart_applications",
            {
                "fleet_id": 1001,
                "confirm": True,
            },
            blocking=True,
        )

        # Should have been called for both devices
        assert coordinator.async_restart_application.call_count == 2


class TestConfigurationFlow:
    """Test configuration flow integration."""

    @pytest.mark.asyncio
    async def test_config_flow_user_step(self, hass: HomeAssistant):
        """Test user step of config flow."""

        from custom_components.balena_cloud.config_flow import BalenaCloudConfigFlow

        flow = BalenaCloudConfigFlow()
        flow.hass = hass

        with patch.object(flow, "_async_validate_input") as mock_validate, \
             patch.object(flow, "_async_fetch_fleets") as mock_fetch_fleets:

            mock_validate.return_value = None
            flow.api_token = "test_token"
            flow.fleets = {1001: "test-fleet"}
            flow.user_info = {"username": "test_user"}

            # Test valid input
            result = await flow.async_step_user({
                "api_token": "test_token_12345"
            })

            assert result["type"] == "form"
            assert result["step_id"] == "fleets"

    @pytest.mark.asyncio
    async def test_config_flow_fleet_step(self, hass: HomeAssistant):
        """Test fleet selection step of config flow."""

        from custom_components.balena_cloud.config_flow import BalenaCloudConfigFlow

        flow = BalenaCloudConfigFlow()
        flow.hass = hass
        flow.api_token = "test_token"
        flow.fleets = {1001: "test-fleet"}
        flow.user_info = {"username": "test_user"}

        result = await flow.async_step_fleets({
            "fleets": [1001]
        })

        assert result["type"] == "create_entry"
        assert result["title"] == "Balena Cloud (test_user)"
        assert result["data"]["api_token"] == "test_token"
        assert result["data"]["fleets"] == [1001]

    @pytest.mark.asyncio
    async def test_config_flow_validation_error(self, hass: HomeAssistant):
        """Test config flow with validation error."""

        from custom_components.balena_cloud.config_flow import BalenaCloudConfigFlow, InvalidAuth

        flow = BalenaCloudConfigFlow()
        flow.hass = hass

        with patch.object(flow, "_async_validate_input") as mock_validate:
            mock_validate.side_effect = InvalidAuth()

            result = await flow.async_step_user({
                "api_token": "invalid_token"
            })

            assert result["type"] == "form"
            assert result["errors"]["base"] == "invalid_auth"


class TestEntityStateManagement:
    """Test entity state management and updates."""

    @pytest.fixture
    def mock_device(self):
        """Create mock device for testing."""
        from custom_components.balena_cloud.models import BalenaDevice, BalenaDeviceMetrics

        device = BalenaDevice(
            uuid="device-uuid-1",
            device_name="Test Device 1",
            device_type="raspberrypi4-64",
            fleet_id=1001,
            fleet_name="test-fleet",
            is_online=True,
            status="Idle",
        )

        device.metrics = BalenaDeviceMetrics(
            cpu_usage=25.5,
            memory_usage=512000000,
            memory_total=2000000000,
            storage_usage=8000000000,
            storage_total=32000000000,
            temperature=45.2,
        )

        return device

    @pytest.mark.asyncio
    async def test_sensor_entity_state(self, mock_device):
        """Test sensor entity state updates."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        # Test CPU sensor
        cpu_sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],  # CPU usage sensor
            device_uuid="device-uuid-1",
        )

        assert cpu_sensor.native_value == 25.5
        assert cpu_sensor.available is True
        assert "device_uuid" in cpu_sensor.extra_state_attributes

    @pytest.mark.asyncio
    async def test_binary_sensor_entity_state(self, mock_device):
        """Test binary sensor entity state updates."""
        from custom_components.balena_cloud.binary_sensor import BalenaCloudBinarySensorEntity, BINARY_SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        # Test online sensor
        online_sensor = BalenaCloudBinarySensorEntity(
            coordinator=coordinator,
            description=BINARY_SENSOR_TYPES[0],  # Online sensor
            device_uuid="device-uuid-1",
        )

        assert online_sensor.is_on is True
        assert online_sensor.available is True
        assert online_sensor.icon == "mdi:check-circle"

    @pytest.mark.asyncio
    async def test_button_entity_press(self, mock_device):
        """Test button entity press functionality."""
        from custom_components.balena_cloud.button import BalenaCloudButtonEntity, BUTTON_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Test restart button
        restart_button = BalenaCloudButtonEntity(
            coordinator=coordinator,
            description=BUTTON_TYPES[0],  # Restart application button
            device_uuid="device-uuid-1",
        )

        await restart_button.async_press()

        coordinator.async_restart_application.assert_called_once_with("device-uuid-1")

    @pytest.mark.asyncio
    async def test_entity_availability(self, mock_device):
        """Test entity availability logic."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()

        # Test with available device
        coordinator.get_device.return_value = mock_device
        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="device-uuid-1",
        )
        assert sensor.available is True

        # Test with unavailable device
        coordinator.get_device.return_value = None
        assert sensor.available is False


class TestDeviceRegistryIntegration:
    """Test device registry integration."""

    @pytest.mark.asyncio
    async def test_device_info_creation(self, mock_device):
        """Test device info creation for Home Assistant device registry."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="device-uuid-1",
        )

        device_info = sensor.device_info

        assert device_info is not None
        assert device_info["name"] == "Test Device 1"
        assert device_info["manufacturer"] == "Balena"
        assert device_info["model"] == "raspberrypi4-64"
        assert "configuration_url" in device_info

    @pytest.mark.asyncio
    async def test_device_unique_id_generation(self, mock_device):
        """Test unique ID generation for entities."""
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="device-uuid-1",
        )

        expected_unique_id = f"device-uuid-1_{SENSOR_TYPES[0].key}"
        assert sensor.unique_id == expected_unique_id


class TestAdvancedComponentIntegration:
    """Test integration of advanced components."""

    @pytest.mark.asyncio
    async def test_device_card_integration(self, mock_device):
        """Test device card component integration."""
        from custom_components.balena_cloud.device_card import BalenaDeviceCard

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        card = BalenaDeviceCard(coordinator, "device-uuid-1")

        card_data = card.card_data
        assert "device_info" in card_data
        assert "status" in card_data
        assert "metrics" in card_data
        assert "health_indicators" in card_data

        # Verify health indicators
        health = card_data["health_indicators"]
        assert "overall_health" in health
        assert "health_score" in health

    @pytest.mark.asyncio
    async def test_fleet_overview_integration(self, mock_device):
        """Test fleet overview component integration."""
        from custom_components.balena_cloud.fleet_overview import BalenaFleetOverview
        from custom_components.balena_cloud.models import BalenaFleet

        coordinator = AsyncMock()

        # Mock fleet
        fleet = BalenaFleet(
            id=1001,
            app_name="test-fleet",
            slug="user/test-fleet",
            device_type="raspberrypi4-64"
        )
        coordinator.get_fleet.return_value = fleet
        coordinator.get_devices_by_fleet.return_value = [mock_device]

        overview = BalenaFleetOverview(coordinator, 1001)

        stats = overview.fleet_statistics
        assert stats["total_devices"] == 1
        assert stats["online_devices"] == 1
        assert stats["online_percentage"] == 100.0
        assert "health_summary" in stats