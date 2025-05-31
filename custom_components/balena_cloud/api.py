"""Balena Cloud API client using balena-sdk."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps

from balena import Balena, exceptions as balena_exceptions
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ERROR_AUTH_FAILED,
    ERROR_NETWORK_ERROR,
    ERROR_RATE_LIMITED,
    MAX_RETRIES,
    RETRY_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class BalenaCloudAPIError(HomeAssistantError):
    """Base exception for Balena Cloud API errors."""


class BalenaCloudAuthenticationError(BalenaCloudAPIError):
    """Exception for authentication errors."""


class BalenaCloudRateLimitError(BalenaCloudAPIError):
    """Exception for rate limit errors."""


def async_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator to add retry logic to async methods."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (balena_exceptions.RequestError, balena_exceptions.BalenaError) as err:
                    last_exception = err
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)
                        _LOGGER.warning(
                            "Attempt %d failed for %s, retrying in %s seconds: %s",
                            attempt + 1, func.__name__, wait_time, err
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        _LOGGER.error(
                            "All %d attempts failed for %s: %s",
                            max_retries + 1, func.__name__, err
                        )

            if last_exception:
                raise BalenaCloudAPIError(f"Failed after {max_retries + 1} attempts") from last_exception

        return wrapper
    return decorator


class BalenaCloudAPIClient:
    """Balena Cloud API client using balena-sdk."""

    def __init__(self, api_token: str) -> None:
        """Initialize the API client."""
        self._api_token = api_token
        self._balena = Balena()

        # Set the API token
        self._balena.auth.login_with_token(api_token)

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous balena SDK calls in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    @async_retry()
    async def async_get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        try:
            user_info = await self._run_in_executor(self._balena.auth.get_user_info)
            return user_info
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get user info: %s", err)
            raise BalenaCloudAPIError(ERROR_NETWORK_ERROR) from err

    @async_retry()
    async def async_get_fleets(self) -> List[Dict[str, Any]]:
        """Get all accessible fleets (applications)."""
        try:
            applications = await self._run_in_executor(self._balena.models.application.get_all)
            return applications
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get fleets: %s", err)
            raise BalenaCloudAPIError(ERROR_NETWORK_ERROR) from err

    @async_retry()
    async def async_get_fleet(self, fleet_id: int) -> Dict[str, Any]:
        """Get fleet information by ID."""
        try:
            application = await self._run_in_executor(
                self._balena.models.application.get, fleet_id
            )
            return application
        except balena_exceptions.ApplicationNotFound:
            _LOGGER.warning("Fleet with ID %s not found", fleet_id)
            return {}
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get fleet %s: %s", fleet_id, err)
            raise BalenaCloudAPIError(ERROR_NETWORK_ERROR) from err

    @async_retry()
    async def async_get_devices(
        self, fleet_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get devices, optionally filtered by fleet."""
        try:
            if fleet_id:
                devices = await self._run_in_executor(
                    self._balena.models.device.get_all_by_application, fleet_id
                )
            else:
                devices = await self._run_in_executor(
                    self._balena.models.device.get_all
                )
            return devices
        except balena_exceptions.ApplicationNotFound:
            _LOGGER.warning("Fleet with ID %s not found", fleet_id)
            return []
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get devices: %s", err)
            raise BalenaCloudAPIError(ERROR_NETWORK_ERROR) from err

    @async_retry()
    async def async_get_device(self, device_uuid: str) -> Dict[str, Any]:
        """Get device information by UUID."""
        try:
            device = await self._run_in_executor(
                self._balena.models.device.get, device_uuid
            )
            return device
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return {}
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get device %s: %s", device_uuid, err)
            raise BalenaCloudAPIError(ERROR_NETWORK_ERROR) from err

    @async_retry()
    async def async_get_device_status(self, device_uuid: str) -> Dict[str, Any]:
        """Get device status and metrics."""
        try:
            # Get basic device info
            device = await self.async_get_device(device_uuid)
            if not device:
                return {}

            # Get device metrics if available
            metrics = await self._async_get_device_metrics(device_uuid)

            # Get device services
            services = await self._async_get_device_services(device_uuid)

            return {
                "device": device,
                "metrics": metrics,
                "services": services,
            }
        except Exception as err:
            _LOGGER.error("Failed to get device status for %s: %s", device_uuid, err)
            return {}

    async def _async_get_device_metrics(self, device_uuid: str) -> Dict[str, Any]:
        """Get device metrics (CPU, memory, etc.)."""
        try:
            # The balena-sdk doesn't have direct metrics API
            # but we can get some basic status information
            device = await self._run_in_executor(
                self._balena.models.device.get, device_uuid
            )

            # Extract what metrics we can from device status
            metrics = {
                "cpu_usage": device.get("cpu_usage"),
                "memory_usage": device.get("memory_usage"),
                "memory_total": device.get("memory_total"),
                "storage_usage": device.get("storage_usage"),
                "storage_total": device.get("storage_total"),
                "temperature": device.get("cpu_temp"),
            }

            # Filter out None values
            return {k: v for k, v in metrics.items() if v is not None}
        except Exception as err:
            _LOGGER.debug("Failed to get device metrics for %s: %s", device_uuid, err)
            return {}

    async def _async_get_device_services(self, device_uuid: str) -> List[Dict[str, Any]]:
        """Get services running on a device."""
        try:
            services = await self._run_in_executor(
                self._balena.models.service.get_all_by_device, device_uuid
            )
            return services
        except Exception as err:
            _LOGGER.debug("Failed to get device services for %s: %s", device_uuid, err)
            return []

    @async_retry()
    async def async_restart_application(
        self, device_uuid: str, service_name: Optional[str] = None
    ) -> bool:
        """Restart application on a device."""
        try:
            if service_name:
                # Restart specific service
                await self._run_in_executor(
                    self._balena.models.device.restart_service,
                    device_uuid,
                    service_name
                )
            else:
                # Restart all services
                await self._run_in_executor(
                    self._balena.models.device.restart_application,
                    device_uuid
                )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to restart application on %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_reboot_device(self, device_uuid: str) -> bool:
        """Reboot a device."""
        try:
            await self._run_in_executor(
                self._balena.models.device.reboot, device_uuid
            )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to reboot device %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_shutdown_device(self, device_uuid: str) -> bool:
        """Shutdown a device."""
        try:
            await self._run_in_executor(
                self._balena.models.device.shutdown, device_uuid
            )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to shutdown device %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_get_device_environment_variables(
        self, device_uuid: str
    ) -> List[Dict[str, Any]]:
        """Get environment variables for a device."""
        try:
            env_vars = await self._run_in_executor(
                self._balena.models.environment_variables.device.get_all,
                device_uuid
            )
            return env_vars
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return []
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to get environment variables for %s: %s", device_uuid, err)
            return []

    @async_retry()
    async def async_set_device_environment_variable(
        self, device_uuid: str, name: str, value: str
    ) -> bool:
        """Set an environment variable for a device."""
        try:
            await self._run_in_executor(
                self._balena.models.environment_variables.device.create,
                device_uuid,
                name,
                value
            )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to set environment variable for %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_update_environment_variables(
        self, device_uuid: str, variables: Dict[str, str]
    ) -> bool:
        """Update environment variables for a device."""
        try:
            # Get existing environment variables
            existing_vars = await self.async_get_device_environment_variables(device_uuid)
            existing_dict = {var["name"]: var for var in existing_vars}

            success = True
            for name, value in variables.items():
                try:
                    if name in existing_dict:
                        # Update existing variable
                        var_id = existing_dict[name]["id"]
                        await self._run_in_executor(
                            self._balena.models.environment_variables.device.update,
                            var_id,
                            value
                        )
                    else:
                        # Create new variable
                        await self._run_in_executor(
                            self._balena.models.environment_variables.device.create,
                            device_uuid,
                            name,
                            value
                        )
                except Exception as var_err:
                    _LOGGER.error("Failed to update variable %s: %s", name, var_err)
                    success = False

            return success
        except Exception as err:
            _LOGGER.error(
                "Failed to update environment variables for %s: %s", device_uuid, err
            )
            return False

    @async_retry()
    async def async_validate_token(self) -> bool:
        """Validate the API token."""
        try:
            await self.async_get_user_info()
            return True
        except BalenaCloudAuthenticationError:
            return False
        except Exception as err:
            _LOGGER.error("Token validation failed: %s", err)
            return False

    @async_retry()
    async def async_enable_device_url(self, device_uuid: str) -> bool:
        """Enable public device URL."""
        try:
            await self._run_in_executor(
                self._balena.models.device.enable_device_url,
                device_uuid
            )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to enable device URL for %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_disable_device_url(self, device_uuid: str) -> bool:
        """Disable public device URL."""
        try:
            await self._run_in_executor(
                self._balena.models.device.disable_device_url,
                device_uuid
            )
            return True
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return False
        except balena_exceptions.InvalidToken as err:
            raise BalenaCloudAuthenticationError(ERROR_AUTH_FAILED) from err
        except Exception as err:
            _LOGGER.error("Failed to disable device URL for %s: %s", device_uuid, err)
            return False

    @async_retry()
    async def async_get_device_url(self, device_uuid: str) -> Optional[str]:
        """Get the public device URL."""
        try:
            url = await self._run_in_executor(
                self._balena.models.device.get_device_url,
                device_uuid
            )
            return url
        except balena_exceptions.DeviceNotFound:
            _LOGGER.warning("Device with UUID %s not found", device_uuid)
            return None
        except Exception as err:
            _LOGGER.debug("Failed to get device URL for %s: %s", device_uuid, err)
            return None