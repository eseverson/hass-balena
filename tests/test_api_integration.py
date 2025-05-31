"""API integration tests for Balena Cloud integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientSession

from custom_components.balena_cloud.api import (
    BalenaCloudAPIClient,
    BalenaCloudAPIError,
    BalenaCloudAuthenticationError,
    BalenaCloudRateLimitError,
)
from custom_components.balena_cloud.const import (
    API_TIMEOUT,
    BALENA_API_BASE_URL,
    BALENA_API_VERSION,
    MAX_RETRIES,
)

from .conftest import validate_device_data, validate_fleet_data


class TestBalenaCloudAPIClient:
    """Test Balena Cloud API client functionality."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client with mocked session."""
        return BalenaCloudAPIClient(mock_aiohttp_session, "test_token")

    async def test_api_client_initialization(self, api_client):
        """Test API client initialization."""
        assert api_client._api_token == "test_token"
        assert api_client._base_url == f"{BALENA_API_BASE_URL}/{BALENA_API_VERSION}"
        assert "Bearer test_token" in api_client.headers["Authorization"]

    async def test_successful_user_info_request(self, api_client, mock_balena_api_response):
        """Test successful user info API request."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_balena_api_response["user"]

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        user_info = await api_client.async_get_user_info()

        assert user_info["id"] == 12345
        assert user_info["username"] == "test_user"
        assert user_info["email"] == "test@example.com"

    async def test_successful_fleets_request(self, api_client, mock_balena_api_response):
        """Test successful fleets API request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"d": mock_balena_api_response["fleets"]}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        fleets = await api_client.async_get_fleets()

        assert len(fleets) == 2
        assert all(validate_fleet_data(fleet) for fleet in fleets)
        assert fleets[0]["app_name"] == "test-fleet-1"

    async def test_successful_devices_request(self, api_client, mock_balena_api_response):
        """Test successful devices API request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"d": mock_balena_api_response["devices"]}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        devices = await api_client.async_get_devices()

        assert len(devices) == 2
        assert all(validate_device_data(device) for device in devices)
        assert devices[0]["device_name"] == "test-device-1"

    async def test_authentication_error_handling(self, api_client, mock_auth_error_response):
        """Test authentication error handling."""
        api_client._session.request.return_value.__aenter__.return_value = mock_auth_error_response

        with pytest.raises(BalenaCloudAuthenticationError):
            await api_client.async_get_user_info()

    async def test_rate_limit_error_handling(self, api_client, mock_rate_limit_response):
        """Test rate limit error handling."""
        api_client._session.request.return_value.__aenter__.return_value = mock_rate_limit_response

        with pytest.raises(BalenaCloudRateLimitError):
            await api_client.async_get_user_info()

    async def test_network_error_handling(self, api_client, mock_network_error):
        """Test network error handling."""
        api_client._session.request.side_effect = mock_network_error

        with pytest.raises(BalenaCloudAPIError):
            await api_client.async_get_user_info()

    async def test_timeout_error_handling(self, api_client, mock_timeout_error):
        """Test timeout error handling."""
        api_client._session.request.side_effect = mock_timeout_error

        with pytest.raises(BalenaCloudAPIError):
            await api_client.async_get_user_info()

    async def test_retry_mechanism_success(self, api_client):
        """Test retry mechanism with eventual success."""
        # First call fails, second succeeds
        responses = [
            ClientError("Temporary network error"),
            AsyncMock(status=200, json=AsyncMock(return_value={"id": 12345}))
        ]

        api_client._session.request.side_effect = [
            responses[0],  # First call raises exception
            responses[1].__aenter__.return_value  # Second call returns response
        ]

        result = await api_client.async_request("GET", "/user")
        assert result["id"] == 12345

    async def test_retry_mechanism_max_retries(self, api_client):
        """Test retry mechanism with max retries exceeded."""
        api_client._session.request.side_effect = ClientError("Persistent error")

        with pytest.raises(BalenaCloudAPIError):
            await api_client.async_request("GET", "/user")

        # Should have tried MAX_RETRIES + 1 times (initial + retries)
        assert api_client._session.request.call_count == MAX_RETRIES + 1

    async def test_device_control_operations(self, api_client):
        """Test device control operations."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"status": "success"}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # Test restart application
        result = await api_client.async_restart_application("device-uuid-1", "main")
        assert result is True

        # Test reboot device
        result = await api_client.async_reboot_device("device-uuid-1")
        assert result is True

        # Test update environment variables
        result = await api_client.async_update_environment_variables(
            "device-uuid-1", {"KEY": "value"}
        )
        assert result is True

    async def test_token_validation(self, api_client):
        """Test API token validation."""
        # Valid token
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"id": 12345}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        is_valid = await api_client.async_validate_token()
        assert is_valid is True

        # Invalid token
        mock_response.status = 401
        is_valid = await api_client.async_validate_token()
        assert is_valid is False


class TestAPIIntegrationScenarios:
    """Test complex API integration scenarios."""

    @pytest.fixture
    def coordinator_setup(self, mock_hass, mock_aiohttp_session, mock_config_entry):
        """Set up coordinator for integration testing."""
        from custom_components.balena_cloud.coordinator import BalenaCloudDataUpdateCoordinator

        return BalenaCloudDataUpdateCoordinator(
            mock_hass,
            mock_aiohttp_session,
            mock_config_entry["data"],
            mock_config_entry["options"],
        )

    async def test_complete_device_discovery_flow(self, coordinator_setup, mock_balena_api_response):
        """Test complete device discovery and data processing flow."""
        coordinator = coordinator_setup

        # Mock API responses for the full flow
        with patch.object(coordinator.api, "async_get_fleets") as mock_get_fleets, \
             patch.object(coordinator.api, "async_get_devices") as mock_get_devices, \
             patch.object(coordinator.api, "async_get_device_status") as mock_get_status:

            mock_get_fleets.return_value = mock_balena_api_response["fleets"]
            mock_get_devices.return_value = mock_balena_api_response["devices"]
            mock_get_status.side_effect = lambda uuid: {
                "device": next((d for d in mock_balena_api_response["devices"] if d["uuid"] == uuid), {}),
                "metrics": mock_balena_api_response["device_metrics"].get(uuid, {})
            }

            # Run the update flow
            data = await coordinator._async_update_data()

            # Verify results
            assert "fleets" in data
            assert "devices" in data
            assert len(data["fleets"]) == 2
            assert len(data["devices"]) == 2

            # Verify device data structure
            for device_uuid, device in data["devices"].items():
                assert device.uuid == device_uuid
                assert device.fleet_name in ["test-fleet-1", "test-fleet-2"]

    async def test_error_recovery_during_update(self, coordinator_setup):
        """Test error recovery during data update."""
        coordinator = coordinator_setup

        # Mock API to fail on first call, succeed on second
        call_count = 0

        async def mock_get_fleets():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise BalenaCloudAPIError("Temporary API error")
            return [{"id": 1001, "app_name": "test-fleet", "slug": "user/test-fleet", "device_type": "rpi"}]

        with patch.object(coordinator.api, "async_get_fleets", side_effect=mock_get_fleets), \
             patch.object(coordinator.api, "async_get_devices", return_value=[]):

            # First update should fail
            with pytest.raises(Exception):
                await coordinator._async_update_data()

            # Second update should succeed
            data = await coordinator._async_update_data()
            assert len(data["fleets"]) == 1

    async def test_large_dataset_handling(self, coordinator_setup, performance_test_data):
        """Test handling of large datasets."""
        coordinator = coordinator_setup

        with patch.object(coordinator.api, "async_get_fleets") as mock_get_fleets, \
             patch.object(coordinator.api, "async_get_devices") as mock_get_devices, \
             patch.object(coordinator.api, "async_get_device_status") as mock_get_status:

            mock_get_fleets.return_value = performance_test_data["fleets"]
            mock_get_devices.return_value = performance_test_data["devices"]
            mock_get_status.return_value = {"device": {}, "metrics": {}}

            start_time = datetime.now()
            data = await coordinator._async_update_data()
            end_time = datetime.now()

            # Verify performance - should complete within reasonable time
            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 30  # 30 seconds max for 1000 devices

            # Verify data integrity
            assert len(data["fleets"]) == 50
            assert len(data["devices"]) == 1000

    async def test_concurrent_api_requests(self, api_client):
        """Test concurrent API requests handling."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"result": "success"}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # Make multiple concurrent requests
        tasks = [
            api_client.async_request("GET", "/user"),
            api_client.async_request("GET", "/application"),
            api_client.async_request("GET", "/device"),
        ]

        results = await asyncio.gather(*tasks)

        # All requests should succeed
        assert all(result["result"] == "success" for result in results)
        assert api_client._session.request.call_count == 3


class TestAPIErrorHandling:
    """Test comprehensive API error handling scenarios."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for error testing."""
        return BalenaCloudAPIClient(mock_aiohttp_session, "test_token")

    async def test_http_error_codes(self, api_client):
        """Test handling of various HTTP error codes."""
        error_scenarios = [
            (400, "Bad Request"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
        ]

        for status_code, reason in error_scenarios:
            mock_response = AsyncMock()
            mock_response.status = status_code
            mock_response.reason = reason
            mock_response.text.return_value = f"HTTP {status_code} Error"

            api_client._session.request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_request("GET", "/test")

    async def test_malformed_json_response(self, api_client):
        """Test handling of malformed JSON responses."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError):
            await api_client.async_request("GET", "/test")

    async def test_rate_limit_with_reset_time(self, api_client):
        """Test rate limit handling with reset time."""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"X-RateLimit-Reset": str(int(datetime.now().timestamp()) + 60)}
        mock_response.text.return_value = "Rate limit exceeded"

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # Should raise rate limit error and set reset time
        with pytest.raises(BalenaCloudRateLimitError):
            await api_client.async_request("GET", "/test")

        assert api_client._rate_limit_reset is not None

    async def test_connection_timeout_scenarios(self, api_client):
        """Test various connection timeout scenarios."""
        timeout_errors = [
            asyncio.TimeoutError(),
            ClientError("Connection timeout"),
            ConnectionError("Connection refused"),
        ]

        for error in timeout_errors:
            api_client._session.request.side_effect = error

            with pytest.raises(BalenaCloudAPIError):
                await api_client.async_request("GET", "/test")


class TestAPISecurityValidation:
    """Test API security and input validation."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for security testing."""
        return BalenaCloudAPIClient(mock_aiohttp_session, "test_token")

    async def test_secure_token_handling(self, mock_aiohttp_session):
        """Test secure token handling."""
        # Token should not appear in logs or error messages
        api_client = BalenaCloudAPIClient(mock_aiohttp_session, "sensitive_token_12345")

        headers = api_client.headers
        assert "Bearer sensitive_token_12345" in headers["Authorization"]

        # Verify token is properly masked in string representation
        client_str = str(api_client)
        assert "sensitive_token_12345" not in client_str

    async def test_input_sanitization(self, api_client, security_test_scenarios):
        """Test input sanitization for security."""
        malicious_inputs = security_test_scenarios["malicious_inputs"]

        # Test device UUID sanitization
        for malicious_uuid in malicious_inputs["device_uuid"]:
            if isinstance(malicious_uuid, str):
                try:
                    await api_client.async_get_device(malicious_uuid)
                except Exception as e:
                    # Should handle gracefully without executing malicious code
                    assert "script" not in str(e).lower()
                    assert "passwd" not in str(e).lower()

    async def test_request_parameter_validation(self, api_client):
        """Test request parameter validation."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # Test with valid parameters
        await api_client.async_request("GET", "/test", params={"valid": "param"})

        # Test with None parameters (should be handled gracefully)
        await api_client.async_request("GET", "/test", params=None)

        # Test with empty parameters
        await api_client.async_request("GET", "/test", params={})


class TestAPIPerformanceAndReliability:
    """Test API performance and reliability characteristics."""

    @pytest.fixture
    def api_client(self, mock_aiohttp_session):
        """Create API client for performance testing."""
        return BalenaCloudAPIClient(mock_aiohttp_session, "test_token")

    async def test_request_timing(self, api_client):
        """Test request timing and timeout handling."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"data": "test"}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        start_time = datetime.now()
        await api_client.async_request("GET", "/test")
        end_time = datetime.now()

        request_time = (end_time - start_time).total_seconds()
        assert request_time < API_TIMEOUT

    async def test_memory_usage_with_large_responses(self, api_client, performance_test_data):
        """Test memory usage with large API responses."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "d": performance_test_data["devices"]  # 1000 devices
        }

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # This should not cause memory issues
        result = await api_client.async_get_devices()
        assert len(result) == 1000

    async def test_rate_limit_backoff_strategy(self, api_client):
        """Test rate limit backoff strategy."""
        # Mock rate limit response followed by success
        rate_limit_response = AsyncMock()
        rate_limit_response.status = 429
        rate_limit_response.headers = {}

        success_response = AsyncMock()
        success_response.status = 200
        success_response.json.return_value = {"success": True}

        api_client._session.request.return_value.__aenter__.side_effect = [
            rate_limit_response,
            success_response,
        ]

        start_time = datetime.now()

        # Should retry after rate limit
        with patch("asyncio.sleep") as mock_sleep:
            try:
                await api_client.async_request("GET", "/test")
            except BalenaCloudRateLimitError:
                pass  # Expected on first attempt

            # Should have called sleep for backoff
            mock_sleep.assert_called()

    async def test_concurrent_request_limit(self, api_client):
        """Test handling of concurrent request limits."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"data": "test"}

        api_client._session.request.return_value.__aenter__.return_value = mock_response

        # Create many concurrent requests
        tasks = [
            api_client.async_request("GET", f"/test/{i}")
            for i in range(50)
        ]

        # Should handle all requests without issues
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most requests should succeed
        success_count = sum(1 for r in results if isinstance(r, dict))
        assert success_count >= 40  # Allow for some rate limiting