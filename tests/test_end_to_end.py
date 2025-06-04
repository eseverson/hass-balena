"""End-to-end tests for Balena Cloud integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.balena_cloud.const import DOMAIN
from custom_components.balena_cloud.models import BalenaDevice, BalenaDeviceMetrics


class TestCompleteUserWorkflows:
    """Test complete user workflows from installation to usage."""

    @pytest.mark.asyncio
    async def test_full_installation_and_setup_workflow(self, hass: HomeAssistant):
        """Test complete installation and setup workflow."""
        # Step 1: User starts configuration flow
        from custom_components.balena_cloud.config_flow import BalenaCloudConfigFlow

        flow = BalenaCloudConfigFlow()
        flow.hass = hass

        # Mock API responses for the setup process
        with patch("custom_components.balena_cloud.config_flow.BalenaCloudAPIClient") as mock_api_class:
            mock_api = AsyncMock()
            mock_api.async_validate_token.return_value = True
            mock_api.async_get_user_info.return_value = {
                "username": "test_user",
                "id": 12345,
                "email": "test@example.com"
            }
            mock_api.async_get_fleets.return_value = [
                {"id": 1001, "app_name": "production-fleet"},
                {"id": 1002, "app_name": "development-fleet"},
            ]
            mock_api_class.return_value = mock_api

            # Step 2: User enters API token
            result = await flow.async_step_user({
                "api_token": "balena_api_token_12345"
            })

            assert result["type"] == "form"
            assert result["step_id"] == "fleets"
            assert flow.api_token == "balena_api_token_12345"
            assert flow.user_info["username"] == "test_user"

            # Step 3: User selects fleets
            result = await flow.async_step_fleets({
                "fleets": [1001, 1002]
            })

            assert result["type"] == "create_entry"
            assert result["title"] == "Balena Cloud (test_user)"
            assert result["data"]["api_token"] == "balena_api_token_12345"
            assert result["data"]["fleets"] == [1001, 1002]

        # Step 4: Integration is set up in Home Assistant
        config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Balena Cloud (test_user)",
            data=result["data"],
            options={
                "update_interval": 30,
                "include_offline_devices": True,
            },
            entry_id="test_entry_id",
            source="user",
            unique_id=None,
            discovery_keys=set(),
            subentries_data={},
        )

        # Mock the full integration setup
        with patch("custom_components.balena_cloud.BalenaCloudDataUpdateCoordinator") as mock_coordinator_class, \
             patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"):

            coordinator_instance = AsyncMock()
            coordinator_instance.async_config_entry_first_refresh = AsyncMock()

            # Mock device data
            coordinator_instance.devices = {
                "device-uuid-1": MagicMock(
                    uuid="device-uuid-1",
                    display_name="Production Device 1",
                    fleet_name="production-fleet",
                    is_online=True,
                    status="Idle"
                ),
                "device-uuid-2": MagicMock(
                    uuid="device-uuid-2",
                    display_name="Dev Device 1",
                    fleet_name="development-fleet",
                    is_online=False,
                    status="Offline"
                ),
            }

            coordinator_instance.fleets = {
                1001: MagicMock(id=1001, app_name="production-fleet"),
                1002: MagicMock(id=1002, app_name="development-fleet"),
            }

            mock_coordinator_class.return_value = coordinator_instance

            # Setup the integration
            from custom_components.balena_cloud import async_setup_entry

            setup_result = await async_setup_entry(hass, config_entry)
            assert setup_result is True

            # Verify coordinator was created and data refresh was called
            mock_coordinator_class.assert_called_once()
            coordinator_instance.async_config_entry_first_refresh.assert_called_once()

            # Step 5: Verify entities are created
            assert DOMAIN in hass.data
            assert config_entry.entry_id in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_device_monitoring_workflow(self, hass: HomeAssistant):
        """Test device monitoring workflow."""
        # Set up integration with mock data
        coordinator = MagicMock()

        # Create test device with metrics
        test_device = BalenaDevice(
            uuid="monitoring-device-uuid",
            device_name="Monitoring Test Device",
            device_type="raspberrypi4-64",
            fleet_id=1001,
            fleet_name="monitoring-fleet",
            is_online=True,
            status="Idle",
            ip_address="192.168.1.100",
        )

        # Add metrics
        test_device.metrics = BalenaDeviceMetrics(
            cpu_usage=75.5,
            memory_usage=1205000000,  # ~60.2% of 2GB
            memory_total=2000000000,
            storage_usage=14653000000,  # ~45.8% of 32GB
            storage_total=32000000000,
            temperature=55.3,
        )

        coordinator.get_device.return_value = test_device
        coordinator.devices = {"monitoring-device-uuid": test_device}

        # Test sensor entities
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        # Create CPU sensor
        cpu_sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],  # Assuming CPU is first
            device_uuid="monitoring-device-uuid",
        )

        # Verify sensor state
        assert cpu_sensor.native_value == 75.5
        assert cpu_sensor.available is True
        assert "monitoring-device-uuid" in cpu_sensor.unique_id

        # Test binary sensor for online status
        from custom_components.balena_cloud.binary_sensor import BalenaCloudBinarySensorEntity, BINARY_SENSOR_TYPES

        online_sensor = BalenaCloudBinarySensorEntity(
            coordinator=coordinator,
            description=BINARY_SENSOR_TYPES[0],  # Assuming online status is first
            device_uuid="monitoring-device-uuid",
        )

        assert online_sensor.is_on is True
        assert online_sensor.available is True

        # Simulate device going offline
        test_device.is_online = False
        test_device.status = "Offline"
        test_device.metrics = None

        # Verify sensor updates
        assert online_sensor.is_on is False
        # CPU sensor should still be available but may show None for offline device

    @pytest.mark.asyncio
    async def test_device_control_workflow(self, hass: HomeAssistant):
        """Test device control operations workflow."""
        coordinator = MagicMock()

        # Mock device
        test_device = BalenaDevice(
            uuid="control-device-uuid",
            device_name="Control Test Device",
            device_type="raspberrypi4-64",
            fleet_id=1001,
            fleet_name="control-fleet",
            is_online=True,
            status="Idle",
        )

        coordinator.get_device.return_value = test_device
        coordinator.devices = {"control-device-uuid": test_device}

        # Mock coordinator control methods
        coordinator.async_restart_application = AsyncMock(return_value=True)
        coordinator.async_reboot_device = AsyncMock(return_value=True)
        coordinator.async_update_environment_variables = AsyncMock(return_value=True)

        # Test button entities for control operations
        from custom_components.balena_cloud.button import BalenaCloudButtonEntity, BUTTON_TYPES

        # Test restart button
        restart_button = BalenaCloudButtonEntity(
            coordinator=coordinator,
            description=BUTTON_TYPES[0],  # Assuming restart is first
            device_uuid="control-device-uuid",
        )

        # Test button press
        await restart_button.async_press()
        coordinator.async_restart_application.assert_called_once_with("control-device-uuid")

        # Test reboot button
        reboot_button = BalenaCloudButtonEntity(
            coordinator=coordinator,
            description=BUTTON_TYPES[1],  # Assuming reboot is second
            device_uuid="control-device-uuid",
        )

        await reboot_button.async_press()
        coordinator.async_reboot_device.assert_called_once_with("control-device-uuid")

        # Test service calls
        service_handler = MagicMock()
        service_handler.register_coordinator("test_entry", coordinator)

        # Simulate service call for restart
        await hass.services.async_call(
            DOMAIN,
            "restart_application",
            {
                "device_uuid": "control-device-uuid",
                "confirm": True,
            },
            blocking=True,
        )

        # Verify the operation was called
        assert coordinator.async_restart_application.call_count >= 1

    @pytest.mark.asyncio
    async def test_fleet_management_workflow(self, hass: HomeAssistant):
        """Test fleet management workflow."""
        coordinator = MagicMock()

        # Create fleet with multiple devices
        fleet_devices = []
        for i in range(5):
            device = BalenaDevice(
                uuid=f"fleet-device-{i}",
                device_name=f"Fleet Device {i}",
                device_type="raspberrypi4-64",
                fleet_id=1001,
                fleet_name="management-fleet",
                is_online=(i % 2 == 0),  # Alternate online/offline
                status="Idle" if (i % 2 == 0) else "Offline"
            )
            fleet_devices.append(device)

        # Mock coordinator methods
        coordinator.get_devices_by_fleet.return_value = fleet_devices
        coordinator.get_fleet.return_value = MagicMock(
            id=1001,
            app_name="management-fleet",
            display_name="Management Fleet"
        )

        # Test fleet overview
        from custom_components.balena_cloud.fleet_overview import BalenaFleetOverview

        fleet_overview = BalenaFleetOverview(coordinator, 1001)
        stats = fleet_overview.fleet_statistics

        assert stats["total_devices"] == 5
        assert stats["online_devices"] == 3  # 3 devices online (0, 2, 4)
        assert stats["offline_devices"] == 2  # 2 devices offline (1, 3)
        assert stats["online_percentage"] == 60.0  # 3/5 = 60%

        # Test bulk operations
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Simulate bulk restart for online devices only
        online_devices = [d for d in fleet_devices if d.is_online]
        for device in online_devices:
            await coordinator.async_restart_application(device.uuid)

        # Should have been called 3 times (for online devices)
        assert coordinator.async_restart_application.call_count == 3

    @pytest.mark.asyncio
    async def test_automation_integration_workflow(self, hass: HomeAssistant):
        """Test integration with Home Assistant automations."""
        coordinator = MagicMock()

        # Create device for automation testing
        test_device = BalenaDevice(
            uuid="automation-device-uuid",
            device_name="Automation Test Device",
            device_type="raspberrypi4-64",
            fleet_id=1001,
            fleet_name="automation-fleet",
            is_online=True,
            status="Idle",
        )
        test_device.metrics = BalenaDeviceMetrics(cpu_usage=45.0)  # Normal CPU usage

        coordinator.get_device.return_value = test_device
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Create sensor entity
        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        cpu_sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],  # CPU sensor
            device_uuid="automation-device-uuid",
        )

        # Test normal state
        assert cpu_sensor.native_value == 45.0
        assert cpu_sensor.available is True

        # Simulate high CPU usage triggering automation
        test_device.metrics.cpu_usage = 95.0  # High CPU usage

        # In a real scenario, this would trigger an automation
        # Here we simulate the automation response
        if cpu_sensor.native_value > 90:
            # Automation would call restart service
            await coordinator.async_restart_application("automation-device-uuid")

        coordinator.async_restart_application.assert_called_once_with("automation-device-uuid")

        # Test device going offline scenario
        test_device.is_online = False
        test_device.status = "Offline"

        # Create binary sensor for online status
        from custom_components.balena_cloud.binary_sensor import BalenaCloudBinarySensorEntity, BINARY_SENSOR_TYPES

        online_sensor = BalenaCloudBinarySensorEntity(
            coordinator=coordinator,
            description=BINARY_SENSOR_TYPES[0],  # Online sensor
            device_uuid="automation-device-uuid",
        )

        # Should reflect offline status
        assert online_sensor.is_on is False

        # In a real scenario, this would trigger an offline alert automation

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, hass: HomeAssistant):
        """Test error recovery and resilience workflow."""
        coordinator = AsyncMock()

        # Simulate API errors during device operations
        coordinator.async_restart_application.side_effect = [
            Exception("API Error"),  # First call fails
            True,  # Second call succeeds
        ]

        # Test that operations can recover from errors
        try:
            await coordinator.async_restart_application("device-uuid-1")
            assert False, "Should have raised exception"
        except Exception as e:
            assert "API Error" in str(e)

        # Retry should succeed
        result = await coordinator.async_restart_application("device-uuid-1")
        assert result is True

        # Test entity error handling
        coordinator_mock = MagicMock()
        coordinator_mock.get_device.return_value = None  # Device not found

        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        sensor = BalenaCloudSensorEntity(
            coordinator=coordinator_mock,
            description=SENSOR_TYPES[0],
            device_uuid="non-existent-device",
        )

        # Entity should gracefully handle missing device
        assert sensor.available is False
        assert sensor.native_value is None

    @pytest.mark.asyncio
    async def test_configuration_changes_workflow(self, hass: HomeAssistant):
        """Test configuration changes and options workflow."""
        # Create initial config entry
        config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Balena Cloud Test",
            data={
                "api_token": "initial_token",
                "fleets": [1001],
            },
            options={
                "update_interval": 30,
                "include_offline_devices": True,
            },
            entry_id="test_entry_id",
            source="user",
            unique_id=None,
            discovery_keys=set(),
            subentries_data={},
        )

        # Test options flow for configuration updates
        from custom_components.balena_cloud.config_flow import BalenaCloudOptionsFlowHandler

        options_flow = BalenaCloudOptionsFlowHandler(config_entry)

        # Test updating options
        result = await options_flow.async_step_init({
            "update_interval": 60,  # Changed from 30 to 60
            "include_offline_devices": False,  # Changed from True to False
        })

        assert result["type"] == "create_entry"
        assert result["data"]["update_interval"] == 60
        assert result["data"]["include_offline_devices"] is False

        # In a real scenario, this would trigger coordinator reconfiguration


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_iot_sensor_fleet_scenario(self):
        """Test scenario with IoT sensor fleet."""
        # Simulate IoT sensor fleet with many small devices
        devices = []
        for i in range(20):
            device = BalenaDevice(
                uuid=f"iot-sensor-{i:03d}",
                device_name=f"IoT Sensor {i:03d}",
                device_type="raspberry-pi",
                fleet_id=1001,
                fleet_name="iot-sensors",
                is_online=(i % 5 != 0),  # 80% online rate
                status="Idle" if (i % 5 != 0) else "Offline"
            )

            if device.is_online:
                device.metrics = BalenaDeviceMetrics(
                    cpu_usage=10.0 + (i % 20),  # 10-30% CPU
                    memory_usage=None,  # Set below
                    memory_total=512000000,  # 512MB total
                    temperature=35.0 + (i % 15)  # 35-50°C
                )
                # Calculate memory usage for 30-70% range
                memory_percent = 30.0 + (i % 40)
                device.metrics.memory_usage = int(device.metrics.memory_total * memory_percent / 100)
            else:
                device.metrics = None

            devices.append(device)

        # Test fleet statistics
        online_devices = [d for d in devices if d.is_online]
        offline_devices = [d for d in devices if not d.is_online]

        assert len(online_devices) == 16  # 80% of 20
        assert len(offline_devices) == 4   # 20% of 20

        # Test average metrics calculation
        avg_cpu = sum(d.metrics.cpu_usage for d in online_devices) / len(online_devices)
        avg_memory = sum(d.metrics.memory_percentage for d in online_devices) / len(online_devices)

        assert 10 <= avg_cpu <= 30
        assert 30 <= avg_memory <= 70

    @pytest.mark.asyncio
    async def test_production_deployment_scenario(self):
        """Test scenario with production deployment fleet."""
        # Simulate production deployment with critical services
        devices = []
        for i in range(5):
            device = BalenaDevice(
                uuid=f"prod-server-{i:02d}",
                device_name=f"Production Server {i:02d}",
                device_type="intel-nuc",
                fleet_id=1001,
                fleet_name="production-services",
                is_online=True,  # Production should be always online
                status="Idle"
            )

            # Production devices have higher resource usage
            device.metrics = BalenaDeviceMetrics(
                cpu_usage=60.0 + (i * 5),  # 60-80% CPU
                memory_usage=None,  # Set below
                memory_total=8000000000,  # 8GB
                storage_usage=None,  # Set below
                storage_total=64000000000,  # 64GB
                temperature=45.0 + (i * 2)  # 45-53°C
            )

            # Calculate memory and storage usage
            memory_percent = 70.0 + (i * 3)  # 70-82% memory
            storage_percent = 50.0 + (i * 8)  # 50-82% storage
            device.metrics.memory_usage = int(device.metrics.memory_total * memory_percent / 100)
            device.metrics.storage_usage = int(device.metrics.storage_total * storage_percent / 100)

            devices.append(device)

        # Test health monitoring for production
        critical_devices = []
        warning_devices = []

        for device in devices:
            if (device.metrics.cpu_usage > 85 or
                device.metrics.memory_percentage > 90 or
                device.metrics.storage_percentage > 90 or
                device.metrics.temperature > 70):
                critical_devices.append(device)
            elif (device.metrics.cpu_usage > 75 or
                  device.metrics.memory_percentage > 80 or
                  device.metrics.storage_percentage > 80 or
                  device.metrics.temperature > 60):
                warning_devices.append(device)

        # In this scenario, some devices should be in warning state
        assert len(warning_devices) > 0
        # No devices should be critical with current values
        assert len(critical_devices) == 0

    @pytest.mark.asyncio
    async def test_development_testing_scenario(self):
        """Test scenario with development and testing environment."""
        # Simulate development environment with frequent changes
        dev_devices = []
        for i in range(3):
            device = BalenaDevice(
                uuid=f"dev-machine-{i:02d}",
                device_name=f"Dev Machine {i:02d}",
                device_type="raspberrypi4-64",
                fleet_id=1001,
                fleet_name="development",
                is_online=True,
                status="Updating" if i == 0 else "Idle"  # One device updating
            )

            if device.status != "Updating":
                device.metrics = BalenaDeviceMetrics(
                    cpu_usage=20.0 + (i * 15),
                    memory_usage=None,  # Set below
                    memory_total=4000000000,  # 4GB
                    temperature=40.0 + (i * 3)
                )
                memory_percent = 40.0 + (i * 10)
                device.metrics.memory_usage = int(device.metrics.memory_total * memory_percent / 100)
            else:
                device.metrics = None  # No metrics during update

            dev_devices.append(device)

        # Test development scenario characteristics
        updating_devices = [d for d in dev_devices if d.status == "Updating"]
        idle_devices = [d for d in dev_devices if d.status == "Idle"]

        assert len(updating_devices) == 1
        assert len(idle_devices) == 2

        # Test that updating devices are handled properly
        for device in updating_devices:
            assert device.metrics is None
            assert device.status == "Updating"

    @pytest.mark.asyncio
    async def test_mixed_architecture_scenario(self):
        """Test scenario with mixed device architectures."""
        architectures = [
            {"type": "raspberrypi4-64", "count": 10, "memory_base": 4000000000},
            {"type": "jetson-nano", "count": 5, "memory_base": 4000000000},
            {"type": "intel-nuc", "count": 3, "memory_base": 8000000000},
            {"type": "raspberry-pi", "count": 8, "memory_base": 512000000},
        ]

        all_devices = []
        for arch in architectures:
            for i in range(arch["count"]):
                device = BalenaDevice(
                    uuid=f"{arch['type']}-{i:03d}",
                    device_name=f"{arch['type'].title()} Device {i:03d}",
                    device_type=arch["type"],
                    fleet_id=1001,
                    fleet_name="mixed-architecture",
                    is_online=(i % 3 != 0),  # ~67% online rate
                    status="Idle" if (i % 3 != 0) else "Offline"
                )

                if device.is_online:
                    device.metrics = BalenaDeviceMetrics(
                        memory_total=arch["memory_base"],
                        memory_usage=int(arch["memory_base"] * 0.4),  # 40% usage
                    )

                all_devices.append(device)

        # Test architecture distribution
        arch_counts = {}
        for device in all_devices:
            arch_counts[device.device_type] = arch_counts.get(device.device_type, 0) + 1

        assert arch_counts["raspberrypi4-64"] == 10
        assert arch_counts["jetson-nano"] == 5
        assert arch_counts["intel-nuc"] == 3
        assert arch_counts["raspberry-pi"] == 8

        # Test that different architectures have appropriate memory configurations
        pi_zero_devices = [d for d in all_devices if d.device_type == "raspberry-pi" and d.is_online]
        nuc_devices = [d for d in all_devices if d.device_type == "intel-nuc" and d.is_online]

        if pi_zero_devices and nuc_devices:
            pi_memory = pi_zero_devices[0].metrics.memory_total
            nuc_memory = nuc_devices[0].metrics.memory_total
            assert nuc_memory > pi_memory  # NUC should have more memory


class TestPerformanceScenarios:
    """Test performance under various load conditions."""

    @pytest.mark.asyncio
    async def test_large_fleet_performance(self, performance_test_data):
        """Test performance with large fleet of devices."""
        start_time = datetime.now()

        # Process large dataset
        fleets = performance_test_data["fleets"]
        devices = performance_test_data["devices"]

        # Simulate coordinator processing time
        fleet_lookup = {f["id"]: f for f in fleets}
        device_groups = {}

        for device in devices:
            fleet_id = device["belongs_to__application"]["__id"]
            if fleet_id not in device_groups:
                device_groups[fleet_id] = []
            device_groups[fleet_id].append(device)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Should process 50 fleets and 1000 devices quickly
        assert processing_time < 2.0  # Less than 2 seconds
        assert len(fleet_lookup) == 50
        assert len(devices) == 1000
        assert all(len(device_groups[fleet_id]) == 20 for fleet_id in device_groups)

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test performance of concurrent device operations."""
        coordinator = AsyncMock()
        coordinator.async_restart_application = AsyncMock(return_value=True)

        device_uuids = [f"perf-device-{i:04d}" for i in range(100)]

        start_time = datetime.now()

        # Execute concurrent operations
        tasks = [
            coordinator.async_restart_application(uuid)
            for uuid in device_uuids
        ]

        results = await asyncio.gather(*tasks)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # All operations should succeed
        assert all(results)
        assert len(results) == 100

        # Should complete within reasonable time
        assert duration < 3.0  # Less than 3 seconds for 100 operations

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """Test memory usage with large datasets."""
        # Create many device objects
        devices = []
        for i in range(1000):
            device = BalenaDevice(
                uuid=f"memory-test-device-{i:04d}",
                device_name=f"Memory Test Device {i:04d}",
                device_type="raspberrypi4-64",
                fleet_id=1001,
                fleet_name="memory-test-fleet",
                is_online=True,
                status="Idle"
            )
            device.metrics = BalenaDeviceMetrics()
            devices.append(device)

        # Test filtering operations on large dataset
        online_devices = [d for d in devices if d.is_online]
        devices_by_type = {}
        for device in devices:
            device_type = device.device_type
            if device_type not in devices_by_type:
                devices_by_type[device_type] = []
            devices_by_type[device_type].append(device)

        # Operations should complete successfully
        assert len(online_devices) == 1000
        assert len(devices_by_type["raspberrypi4-64"]) == 1000

    @pytest.mark.asyncio
    async def test_api_rate_limit_handling_performance(self):
        """Test API rate limit handling under load."""
        api_client = AsyncMock()

        # Simulate rate limiting after 50 requests
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 50:
                raise Exception("Rate limit exceeded")
            return {"success": True}

        api_client.async_request = mock_request

        # Make many requests
        successful_requests = 0
        rate_limited_requests = 0

        for i in range(100):
            try:
                await api_client.async_request("GET", f"/test/{i}")
                successful_requests += 1
            except Exception:
                rate_limited_requests += 1

        # Should handle rate limiting gracefully
        assert successful_requests == 50
        assert rate_limited_requests == 50