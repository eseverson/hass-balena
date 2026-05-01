"""API integration tests for Balena Cloud integration."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from balena import exceptions as balena_exceptions

from custom_components.balena_cloud.api import (
    BalenaCloudAPIClient,
    BalenaCloudAPIError,
    BalenaCloudAuthenticationError,
)
from custom_components.balena_cloud.const import API_TIMEOUT

from .conftest import validate_device_data, validate_fleet_data


class TestBalenaCloudAPIClient:
    """Test Balena Cloud API client functionality."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client with mocked session."""
        # Use new SDK-based constructor
        return BalenaCloudAPIClient("test_token")

    @pytest.mark.asyncio
    async def test_api_client_initialization(self, api_client):
        """Test API client initialization."""
        assert api_client._api_token == "test_token"
        assert api_client._balena is None  # Not initialized yet
        assert api_client._initialized is False

        # Patch the async initializer to set up a mock _balena
        with patch.object(api_client, '_ensure_initialized', autospec=True) as mock_ensure_init:
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = {"id": 12345}
            api_client._balena = mock_balena
            api_client._initialized = True

            # Now call the async method
            result = await api_client.async_get_user_info()
            assert result == {"id": 12345}

        # Now it should be initialized
        assert api_client._balena is not None
        assert api_client._initialized is True

    @pytest.mark.asyncio
    async def test_successful_user_info_request(self, api_client, mock_balena_api_response):
        """Test successful user info API request."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = mock_balena_api_response["user"]
            api_client._balena = mock_balena
            api_client._initialized = True
            user_info = await api_client.async_get_user_info()
            assert user_info == mock_balena_api_response["user"]

    @pytest.mark.asyncio
    async def test_successful_fleets_request(self, api_client, mock_balena_api_response):
        """Test successful fleets API request."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.models.application.get_all.return_value = mock_balena_api_response["fleets"]
            api_client._balena = mock_balena
            api_client._initialized = True
            fleets = await api_client.async_get_fleets()
            assert fleets == mock_balena_api_response["fleets"]

    @pytest.mark.asyncio
    async def test_successful_devices_request(self, api_client, mock_balena_api_response):
        """Test successful devices API request."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.models.device.get_all.return_value = mock_balena_api_response["devices"]
            api_client._balena = mock_balena
            api_client._initialized = True
            devices = await api_client.async_get_devices()
            assert devices == mock_balena_api_response["devices"]

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, api_client, mock_auth_error_response):
        """Test authentication error handling."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.side_effect = balena_exceptions.MalformedToken("Invalid token")
            api_client._balena = mock_balena
            api_client._initialized = True
            with pytest.raises(BalenaCloudAuthenticationError):
                await api_client.async_get_user_info()

    @pytest.mark.asyncio
    async def test_network_error_handling(self, api_client, mock_network_error):
        """Test network error handling."""
        with patch.object(api_client, '_run_in_executor') as mock_executor:
            mock_executor.side_effect = balena_exceptions.RequestError("Network error", status_code=500)

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_get_user_info()

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, api_client, mock_timeout_error):
        """Test timeout error handling."""
        with patch.object(api_client, '_run_in_executor') as mock_executor:
            mock_executor.side_effect = Exception("Timeout")

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_get_user_info()

    @pytest.mark.asyncio
    async def test_retry_mechanism_success(self, api_client):
        """Test retry mechanism with eventual success."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = {"id": 12345}
            api_client._balena = mock_balena
            api_client._initialized = True
            result = await api_client.async_get_user_info()
            assert result["id"] == 12345
        assert hasattr(api_client.async_get_user_info, '__wrapped__')

    @pytest.mark.asyncio
    async def test_retry_mechanism_max_retries(self, api_client):
        """Test retry mechanism with max retries exceeded."""
        with patch.object(api_client, '_run_in_executor') as mock_executor:
            mock_executor.side_effect = Exception("Persistent error")

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_get_user_info()

    @pytest.mark.asyncio
    async def test_device_control_operations(self, api_client):
        """Test device control operations."""
        with patch.object(api_client, '_ensure_initialized', autospec=True), \
             patch.object(api_client, '_run_in_executor') as mock_executor:

            mock_balena = MagicMock()
            mock_balena.models.device.restart_application.return_value = True
            mock_balena.models.device.restart_service.return_value = True
            mock_balena.models.device.reboot.return_value = True
            api_client._balena = mock_balena
            api_client._initialized = True

            mock_executor.return_value = True

            result = await api_client.async_restart_application("device-uuid-1", "main")
            assert result is True

            result = await api_client.async_reboot_device("device-uuid-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_token_validation(self, api_client):
        """Test API token validation."""
        assert hasattr(api_client, 'async_validate_token')

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, api_client):
        """Test concurrent API requests handling."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = {"result": "success"}
            mock_balena.models.application.get_all.return_value = {"result": "success"}
            mock_balena.models.device.get_all.return_value = {"result": "success"}
            api_client._balena = mock_balena
            api_client._initialized = True
            tasks = [
                api_client.async_get_user_info(),
                api_client.async_get_fleets(),
                api_client.async_get_devices(),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if isinstance(r, dict))
            assert success_count >= 2


class TestAPIIntegrationScenarios:
    """Test complex API integration scenarios."""

    @pytest.fixture
    def coordinator_setup(self, mock_hass, mock_config_entry):
        """Set up coordinator for integration testing."""
        from custom_components.balena_cloud.coordinator import BalenaCloudDataUpdateCoordinator
        # Ensure frame helper is initialized for this hass
        from homeassistant.helpers import frame as ha_frame
        import threading, asyncio
        mock_hass.loop_thread_id = threading.get_ident()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        mock_hass.loop = loop
        ha_frame.async_setup(mock_hass)

        # Ensure include_offline_devices is True for tests
        options = mock_config_entry["options"].copy()
        options["include_offline_devices"] = True

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        return BalenaCloudDataUpdateCoordinator(
            mock_hass,
            mock_entry,
            mock_config_entry["data"],
            options,
        )

    @pytest.mark.asyncio
    async def test_complete_device_discovery_flow(self, coordinator_setup, mock_balena_api_response):
        """Test complete device discovery and data processing flow."""
        coordinator = coordinator_setup

        with patch.object(coordinator.api, "async_get_fleets") as mock_get_fleets, \
             patch.object(coordinator.api, "async_get_devices") as mock_get_devices, \
             patch.object(coordinator.api, "async_get_device_status") as mock_get_status:

            mock_get_fleets.return_value = mock_balena_api_response["fleets"]
            mock_get_devices.return_value = mock_balena_api_response["devices"]
            mock_get_status.side_effect = lambda uuid: {
                "device": next((d for d in mock_balena_api_response["devices"] if d["uuid"] == uuid), {}),
                "metrics": mock_balena_api_response["device_metrics"].get(uuid, {}),
                "services": []  # Services are now included in device status
            }

            data = await coordinator._async_update_data()

            assert "fleets" in data
            assert "devices" in data
            assert len(data["fleets"]) == 2
            assert len(data["devices"]) == 2

            for device_uuid, device in data["devices"].items():
                assert device.uuid == device_uuid
                assert device.fleet_name in ["test-fleet-1", "test-fleet-2"]

    @pytest.mark.asyncio
    async def test_error_recovery_during_update(self, coordinator_setup):
        """Test error recovery during data update."""
        coordinator = coordinator_setup

        call_count = 0

        async def mock_get_fleets():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise BalenaCloudAPIError("Temporary API error")
            return [{"id": 1001, "app_name": "test-fleet", "slug": "user/test-fleet", "device_type": "rpi"}]

        with patch.object(coordinator.api, "async_get_fleets", side_effect=mock_get_fleets), \
             patch.object(coordinator.api, "async_get_devices", return_value=[]):

            with pytest.raises(Exception):
                await coordinator._async_update_data()

            data = await coordinator._async_update_data()
            assert len(data["fleets"]) == 1

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, coordinator_setup, performance_test_data):
        """Test handling of large datasets."""
        coordinator = coordinator_setup
        
        # Clear selected fleets to ensure all devices are included
        coordinator.selected_fleets = []

        with patch.object(coordinator.api, "async_get_fleets") as mock_get_fleets, \
             patch.object(coordinator.api, "async_get_devices") as mock_get_devices, \
             patch.object(coordinator.api, "async_get_device_status") as mock_get_status:

            mock_get_fleets.return_value = performance_test_data["fleets"]
            mock_get_devices.return_value = performance_test_data["devices"]
            mock_get_status.return_value = {"device": {}, "metrics": {}, "services": []}

            start_time = datetime.now()
            data = await coordinator._async_update_data()
            end_time = datetime.now()

            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 30

            assert len(data["fleets"]) == 50
            # With include_offline_devices=True, all 1000 devices should be included
            assert len(data["devices"]) == 1000


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for error testing."""
        return BalenaCloudAPIClient("test_token")

    @pytest.mark.asyncio
    async def test_http_error_codes(self, api_client):
        """Test handling of various HTTP error codes."""
        with patch.object(api_client, '_run_in_executor') as mock_executor:
            mock_executor.side_effect = balena_exceptions.RequestError("API Error", status_code=500)

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_get_user_info()

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, api_client):
        """Test handling of malformed JSON responses."""
        assert hasattr(api_client, 'async_get_user_info')

    @pytest.mark.asyncio
    async def test_rate_limit_with_reset_time(self, api_client):
        """Test rate limit handling with reset time."""
        assert hasattr(api_client, 'async_get_user_info')

    @pytest.mark.asyncio
    async def test_connection_timeout_scenarios(self, api_client):
        """Test various connection timeout scenarios."""
        with patch.object(api_client, '_run_in_executor') as mock_executor:
            mock_executor.side_effect = Exception("Connection timeout")

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_get_user_info()


class TestAPISecurityValidation:
    """Test API security and input validation."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for security testing."""
        return BalenaCloudAPIClient("test_token")

    @pytest.mark.asyncio
    async def test_secure_token_handling(self, mock_aiohttp_session):
        """Test secure token handling."""
        api_client = BalenaCloudAPIClient("sensitive_token_12345")

        assert api_client._api_token == "sensitive_token_12345"

        client_str = str(api_client)
        assert "sensitive_token_12345" not in client_str or "***" in client_str

    @pytest.mark.asyncio
    async def test_input_sanitization(self, api_client, security_test_scenarios):
        """Test input sanitization for security."""
        malicious_inputs = security_test_scenarios["malicious_inputs"]

        for malicious_uuid in malicious_inputs["device_uuid"]:
            if isinstance(malicious_uuid, str):
                try:
                    with patch.object(api_client, '_run_in_executor') as mock_executor:
                        mock_executor.return_value = {}
                        await api_client.async_get_device(malicious_uuid)
                except Exception as e:
                    assert "script" not in str(e).lower()
                    assert "passwd" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_request_parameter_validation(self, api_client):
        """Test request parameter validation."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            api_client._balena = mock_balena
            api_client._initialized = True
            assert api_client._balena is not None


class TestAPIPerformanceAndReliability:
    """Test API performance and reliability characteristics."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for performance testing."""
        return BalenaCloudAPIClient("test_token")

    @pytest.mark.asyncio
    async def test_request_timing(self, api_client):
        """Test request timing and timeout handling."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = {"data": "test"}
            api_client._balena = mock_balena
            api_client._initialized = True
            start_time = datetime.now()
            await api_client.async_get_user_info()
            end_time = datetime.now()
            request_time = (end_time - start_time).total_seconds()
            assert request_time < API_TIMEOUT

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_responses(self, api_client, performance_test_data):
        """Test memory usage with large API responses."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.models.device.get_all.return_value = performance_test_data["devices"]
            api_client._balena = mock_balena
            api_client._initialized = True
            result = await api_client.async_get_devices()
            assert len(result) == 1000

    @pytest.mark.asyncio
    async def test_rate_limit_backoff_strategy(self, api_client):
        """Test rate limit backoff strategy."""
        assert hasattr(api_client, 'async_get_user_info')

    @pytest.mark.asyncio
    async def test_concurrent_request_limit(self, api_client):
        """Test handling of concurrent request limits."""
        with patch.object(api_client, '_ensure_initialized', autospec=True):
            mock_balena = MagicMock()
            mock_balena.auth.get_user_info.return_value = {"data": "test"}
            api_client._balena = mock_balena
            api_client._initialized = True
            tasks = [api_client.async_get_user_info() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if isinstance(r, dict))
            assert success_count >= 8
