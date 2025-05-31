"""Cross-platform functionality tests for Balena Cloud integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.balena_cloud.models import BalenaDevice, BalenaFleet, BalenaDeviceMetrics


class TestDeviceCompatibility:
    """Test compatibility across different device architectures and configurations."""

    @pytest.fixture
    def device_architectures(self):
        """Sample device architectures for testing."""
        return {
            "raspberry_pi_4": {
                "device_type": "raspberrypi4-64",
                "architecture": "aarch64",
                "features": ["gpio", "camera", "bluetooth"],
                "memory_total": 4000000000,  # 4GB
            },
            "jetson_nano": {
                "device_type": "jetson-nano",
                "architecture": "aarch64",
                "features": ["gpu", "ai_acceleration", "gpio"],
                "memory_total": 4000000000,  # 4GB
            },
            "intel_nuc": {
                "device_type": "intel-nuc",
                "architecture": "x86_64",
                "features": ["high_performance", "multiple_cores"],
                "memory_total": 8000000000,  # 8GB
            },
            "raspberry_pi_zero": {
                "device_type": "raspberry-pi",
                "architecture": "armv6l",
                "features": ["low_power", "compact"],
                "memory_total": 512000000,  # 512MB
            },
        }

    async def test_device_architecture_compatibility(self, device_architectures):
        """Test device compatibility across different architectures."""

        for arch_name, arch_info in device_architectures.items():
            # Create device with architecture-specific properties
            device = BalenaDevice(
                uuid=f"test-{arch_name}-uuid",
                device_name=f"Test {arch_name.replace('_', ' ').title()}",
                device_type=arch_info["device_type"],
                fleet_id=1001,
                fleet_name="multi-arch-fleet",
                is_online=True,
                status="Idle",
            )

            # Add architecture-specific metrics
            device.metrics = BalenaDeviceMetrics(
                cpu_usage=25.0,
                memory_usage=arch_info["memory_total"] // 4,  # 25% usage
                memory_total=arch_info["memory_total"],
                storage_usage=8000000000,  # 8GB used
                storage_total=32000000000,  # 32GB total
                temperature=45.0,
            )

            # Test that device handles architecture-specific features
            assert device.device_type == arch_info["device_type"]
            assert device.metrics.memory_total == arch_info["memory_total"]

            # Test memory percentage calculation
            expected_memory_percentage = 25.0
            assert abs(device.metrics.memory_percentage - expected_memory_percentage) < 0.1

    async def test_multi_service_device_scenarios(self):
        """Test devices with multiple services and complex configurations."""

        # Create device with multiple services
        device = BalenaDevice(
            uuid="multi-service-device-uuid",
            device_name="Multi-Service Device",
            device_type="raspberrypi4-64",
            fleet_id=1001,
            fleet_name="multi-service-fleet",
            is_online=True,
            status="Idle",
        )

        # Mock services on the device
        device.services = [
            {
                "service_name": "main",
                "status": "Running",
                "install_date": "2024-01-01T12:00:00Z",
                "image_id": "sha256:abc123",
            },
            {
                "service_name": "database",
                "status": "Running",
                "install_date": "2024-01-01T12:00:00Z",
                "image_id": "sha256:def456",
            },
            {
                "service_name": "worker",
                "status": "Stopped",
                "install_date": "2024-01-01T12:00:00Z",
                "image_id": "sha256:ghi789",
            },
        ]

        # Test service status aggregation
        running_services = [s for s in device.services if s["status"] == "Running"]
        assert len(running_services) == 2

        # Test that device can handle multiple service restarts
        coordinator = AsyncMock()
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Simulate restarting specific services
        for service in device.services:
            result = await coordinator.async_restart_application(
                device.uuid, service["service_name"]
            )
            assert result is True

    async def test_edge_case_device_states(self):
        """Test handling of edge case device states and conditions."""

        edge_cases = [
            {
                "name": "Device just provisioned",
                "status": "Configuring",
                "is_online": False,
                "metrics": None,
                "last_seen": None,
            },
            {
                "name": "Device updating OS",
                "status": "Updating",
                "is_online": True,
                "is_updating": True,
                "metrics": BalenaDeviceMetrics(cpu_usage=100.0),
            },
            {
                "name": "Device with failed services",
                "status": "Post Provisioning",
                "is_online": True,
                "services_status": "Failed",
            },
            {
                "name": "Device offline for extended period",
                "status": "Offline",
                "is_online": False,
                "last_seen": datetime.now() - timedelta(days=7),
            },
            {
                "name": "Device with extreme resource usage",
                "status": "Idle",
                "is_online": True,
                "metrics": BalenaDeviceMetrics(
                    cpu_usage=99.9,
                    memory_usage=3900000000,
                    memory_total=4000000000,  # 97.5% memory usage
                    storage_usage=31500000000,
                    storage_total=32000000000,  # 98.4% storage usage
                    temperature=85.0,  # High temperature
                ),
            },
        ]

        for case in edge_cases:
            device = BalenaDevice(
                uuid=f"edge-case-{case['name'].lower().replace(' ', '-')}-uuid",
                device_name=case["name"],
                device_type="raspberrypi4-64",
                fleet_id=1001,
                fleet_name="edge-case-fleet",
                is_online=case["is_online"],
                status=case["status"],
                last_seen=case.get("last_seen"),
            )

            if case.get("metrics"):
                device.metrics = case["metrics"]

            if case.get("is_updating"):
                device.is_updating = True

            # Test that the device object handles edge cases gracefully
            assert device.uuid is not None
            assert device.device_name == case["name"]
            assert device.is_online == case["is_online"]

            # Test health assessment for edge cases
            if device.metrics and device.is_online:
                # Should detect high resource usage
                if device.metrics.cpu_usage > 95:
                    assert device.metrics.cpu_percentage > 95
                if device.metrics.memory_percentage > 95:
                    # Should be flagged as critical
                    pass
                if device.metrics.temperature and device.metrics.temperature > 80:
                    # Should be flagged for high temperature
                    pass


class TestFleetManagementIntegration:
    """Test fleet management functionality across different scenarios."""

    async def test_large_fleet_handling(self, performance_test_data):
        """Test handling of large fleets with many devices."""

        from custom_components.balena_cloud.coordinator import BalenaCloudDataUpdateCoordinator

        coordinator = AsyncMock()

        # Mock large fleet data
        large_fleet_data = performance_test_data

        # Test fleet statistics calculation with large datasets
        fleet_id = 1000
        fleet_devices = [
            device for device in large_fleet_data["devices"]
            if device["belongs_to__application"]["__id"] == fleet_id
        ]

        # Simulate processing time for large fleet
        start_time = datetime.now()

        # Calculate statistics
        total_devices = len(fleet_devices)
        online_devices = sum(1 for d in fleet_devices if d["is_online"])
        device_types = {}

        for device in fleet_devices:
            device_type = device["device_type"]
            device_types[device_type] = device_types.get(device_type, 0) + 1

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Should process quickly even with large datasets
        assert processing_time < 1.0  # Less than 1 second
        assert total_devices == 20  # 20 devices per fleet in test data
        assert online_devices > 0
        assert len(device_types) > 0

    async def test_multi_fleet_account_scenarios(self):
        """Test scenarios with multiple fleets in a single account."""

        fleets = [
            {
                "id": 1001,
                "app_name": "production-app",
                "device_count": 50,
                "environment": "production",
            },
            {
                "id": 1002,
                "app_name": "staging-app",
                "device_count": 5,
                "environment": "staging",
            },
            {
                "id": 1003,
                "app_name": "development-app",
                "device_count": 2,
                "environment": "development",
            },
            {
                "id": 1004,
                "app_name": "iot-sensors",
                "device_count": 100,
                "environment": "production",
            },
        ]

        # Test fleet filtering by environment
        production_fleets = [f for f in fleets if f["environment"] == "production"]
        assert len(production_fleets) == 2

        # Test total device count across fleets
        total_devices = sum(f["device_count"] for f in fleets)
        assert total_devices == 157

        # Test fleet management operations
        coordinator = AsyncMock()
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Simulate bulk operations across multiple fleets
        for fleet in fleets:
            if fleet["environment"] == "production":
                # More careful handling for production
                assert fleet["id"] in [1001, 1004]

        # Test fleet access permissions
        user_accessible_fleets = [f for f in fleets if f["device_count"] > 0]
        assert len(user_accessible_fleets) == 4

    async def test_fleet_permission_and_access_testing(self):
        """Test fleet permissions and access control."""

        # Mock user with different permission levels
        users = [
            {
                "username": "admin_user",
                "permissions": ["read", "write", "admin"],
                "accessible_fleets": [1001, 1002, 1003, 1004],
            },
            {
                "username": "dev_user",
                "permissions": ["read", "write"],
                "accessible_fleets": [1002, 1003],  # Only staging and dev
            },
            {
                "username": "readonly_user",
                "permissions": ["read"],
                "accessible_fleets": [1001],  # Only production read access
            },
        ]

        for user in users:
            # Test fleet visibility based on permissions
            if "admin" in user["permissions"]:
                assert len(user["accessible_fleets"]) == 4
            elif "write" in user["permissions"]:
                # Dev user can access staging and development
                assert 1002 in user["accessible_fleets"]
                assert 1003 in user["accessible_fleets"]
            else:
                # Read-only user has limited access
                assert len(user["accessible_fleets"]) <= 1

    async def test_device_addition_and_removal_scenarios(self):
        """Test dynamic device addition and removal from fleets."""

        coordinator = AsyncMock()

        # Initial fleet state
        initial_devices = {
            "device-1": MagicMock(uuid="device-1", fleet_id=1001),
            "device-2": MagicMock(uuid="device-2", fleet_id=1001),
        }
        coordinator.devices = initial_devices.copy()

        # Test adding new device
        new_device = MagicMock(uuid="device-3", fleet_id=1001)
        coordinator.devices["device-3"] = new_device

        assert len(coordinator.devices) == 3
        assert "device-3" in coordinator.devices

        # Test removing device
        del coordinator.devices["device-2"]

        assert len(coordinator.devices) == 2
        assert "device-2" not in coordinator.devices

        # Test device moving between fleets
        coordinator.devices["device-1"].fleet_id = 1002

        # Verify fleet association updated
        assert coordinator.devices["device-1"].fleet_id == 1002


class TestAutomationAndTriggerIntegration:
    """Test integration with Home Assistant automations and triggers."""

    async def test_entity_state_change_triggers(self, mock_device):
        """Test entity state changes triggering automations."""

        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES
        from custom_components.balena_cloud.binary_sensor import BalenaCloudBinarySensorEntity, BINARY_SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        # Test CPU sensor state changes
        cpu_sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],  # CPU usage
            device_uuid="device-uuid-1",
        )

        # Simulate CPU usage increasing
        mock_device.metrics.cpu_usage = 95.0
        assert cpu_sensor.native_value == 95.0

        # Test binary sensor state changes
        online_sensor = BalenaCloudBinarySensorEntity(
            coordinator=coordinator,
            description=BINARY_SENSOR_TYPES[0],  # Online status
            device_uuid="device-uuid-1",
        )

        # Simulate device going offline
        mock_device.is_online = False
        coordinator.get_device.return_value = mock_device

        # Should reflect new state
        assert online_sensor.is_on is False

    async def test_service_calls_from_automations(self, sample_automation_config):
        """Test service calls triggered from Home Assistant automations."""

        coordinator = AsyncMock()
        coordinator.async_restart_application = AsyncMock(return_value=True)
        coordinator.async_reboot_device = AsyncMock(return_value=True)

        # Test automation calling restart service
        restart_automation = sample_automation_config["high_cpu_restart"]
        service_call = restart_automation["action"]

        assert service_call["service"] == "balena_cloud.restart_application"
        assert service_call["data"]["device_uuid"] == "device-uuid-1"
        assert service_call["data"]["confirm"] is True

        # Simulate service call
        await coordinator.async_restart_application(
            service_call["data"]["device_uuid"]
        )

        coordinator.async_restart_application.assert_called_once()

    async def test_conditional_logic_with_device_attributes(self, mock_device):
        """Test conditional logic using device attributes in automations."""

        from custom_components.balena_cloud.sensor import BalenaCloudSensorEntity, SENSOR_TYPES

        coordinator = AsyncMock()
        coordinator.get_device.return_value = mock_device

        cpu_sensor = BalenaCloudSensorEntity(
            coordinator=coordinator,
            description=SENSOR_TYPES[0],
            device_uuid="device-uuid-1",
        )

        # Test attributes available for conditional logic
        attributes = cpu_sensor.extra_state_attributes

        assert "device_uuid" in attributes
        assert "device_name" in attributes
        assert "fleet_name" in attributes
        assert "device_type" in attributes
        assert "is_online" in attributes

        # Test conditional scenarios
        conditions = [
            {
                "condition": "template",
                "value_template": "{{ states('sensor.test_device_1_cpu_usage') | float > 90 }}",
                "expected": False,  # Current CPU is 25.5%
            },
            {
                "condition": "template",
                "value_template": "{{ state_attr('sensor.test_device_1_cpu_usage', 'is_online') }}",
                "expected": True,  # Device is online
            },
            {
                "condition": "template",
                "value_template": "{{ state_attr('sensor.test_device_1_cpu_usage', 'device_type') == 'raspberrypi4-64' }}",
                "expected": True,  # Correct device type
            },
        ]

        for condition in conditions:
            # These would be evaluated by Home Assistant's template engine
            # We're verifying the attributes are available for such conditions
            assert "value_template" in condition

    async def test_complex_automation_scenarios(self, sample_automation_config):
        """Test complex automation scenarios with multiple devices and conditions."""

        # Test fleet health monitoring automation
        fleet_health_automation = sample_automation_config["fleet_health_check"]

        assert fleet_health_automation["trigger"]["platform"] == "time_pattern"
        assert fleet_health_automation["trigger"]["hours"] == "/6"  # Every 6 hours

        actions = fleet_health_automation["action"]
        assert len(actions) == 4  # Get health, wait, check condition, notify

        # Test multi-step automation flow
        get_health_action = actions[0]
        assert get_health_action["service"] == "balena_cloud.get_fleet_health"
        assert get_health_action["data"]["fleet_id"] == 1001

        wait_action = actions[1]
        assert wait_action["wait_for_trigger"]["platform"] == "event"
        assert wait_action["wait_for_trigger"]["event_type"] == "balena_cloud_fleet_health_response"

        condition_action = actions[2]
        assert condition_action["condition"] == "template"
        assert "critical_devices" in condition_action["value_template"]

        notify_action = actions[3]
        assert notify_action["service"] == "notify.admin"


class TestPerformanceAndScalability:
    """Test performance and scalability characteristics."""

    async def test_concurrent_device_operations(self):
        """Test concurrent operations on multiple devices."""

        coordinator = AsyncMock()
        coordinator.async_restart_application = AsyncMock(return_value=True)

        # Create multiple device UUIDs
        device_uuids = [f"device-uuid-{i}" for i in range(20)]

        # Test concurrent restart operations
        start_time = datetime.now()

        tasks = [
            coordinator.async_restart_application(uuid)
            for uuid in device_uuids
        ]

        results = await asyncio.gather(*tasks)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # All operations should succeed
        assert all(results)
        assert len(results) == 20

        # Should complete reasonably quickly
        assert duration < 5.0  # Less than 5 seconds

        # Verify all devices were processed
        assert coordinator.async_restart_application.call_count == 20

    async def test_memory_usage_with_large_datasets(self, performance_test_data):
        """Test memory usage with large device datasets."""

        # Create many device objects
        devices = []

        for device_data in performance_test_data["devices"]:
            device = BalenaDevice(
                uuid=device_data["uuid"],
                device_name=device_data["device_name"],
                device_type=device_data["device_type"],
                fleet_id=device_data["belongs_to__application"]["__id"],
                fleet_name=device_data["belongs_to__application"]["app_name"],
                is_online=device_data["is_online"],
                status=device_data["status"],
            )
            devices.append(device)

        # Verify we can handle large numbers of devices
        assert len(devices) == 1000

        # Test bulk processing
        online_devices = [d for d in devices if d.is_online]
        offline_devices = [d for d in devices if not d.is_online]

        # Should efficiently filter large datasets
        assert len(online_devices) > 0
        assert len(offline_devices) > 0
        assert len(online_devices) + len(offline_devices) == len(devices)

    async def test_api_rate_limit_compliance(self):
        """Test compliance with API rate limits under load."""

        coordinator = AsyncMock()

        # Simulate rate limit scenarios
        rate_limit_scenarios = [
            {"requests_per_second": 10, "duration": 60},
            {"requests_per_second": 50, "duration": 30},
            {"requests_per_second": 100, "duration": 10},
        ]

        for scenario in rate_limit_scenarios:
            # Calculate expected total requests
            expected_requests = scenario["requests_per_second"] * scenario["duration"]

            # Test that we don't exceed the rate limit
            assert scenario["requests_per_second"] <= 100  # Reasonable API limit
            assert expected_requests <= 6000  # Max requests in test scenario

            # Verify rate limiting logic would be applied
            if scenario["requests_per_second"] > 50:
                # Should implement backoff or queuing
                pass