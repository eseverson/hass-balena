"""Config flow for Balena Cloud integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BalenaCloudAPIClient, BalenaCloudAPIError, BalenaCloudAuthenticationError
from .const import (
    CONF_API_TOKEN,
    CONF_FLEETS,
    CONF_INCLUDE_OFFLINE_DEVICES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_INCLUDE_OFFLINE_DEVICES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_AUTH_FAILED,
    ERROR_INVALID_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class BalenaCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Balena Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.api_token: Optional[str] = None
        self.fleets: Dict[int, str] = {}
        self.user_info: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the API token
                await self._async_validate_input(user_input)

                # Store the token for the next step
                self.api_token = user_input[CONF_API_TOKEN]

                # Move to fleet selection step
                return await self.async_step_fleets()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show the initial form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_TOKEN): str,
            }),
            errors=errors,
            description_placeholders={
                "api_docs_url": "https://www.balena.io/docs/reference/api/overview/",
            },
        )

    async def async_step_fleets(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle fleet selection step."""
        errors: Dict[str, str] = {}

        # Fetch fleets if not already done
        if not self.fleets:
            try:
                await self._async_fetch_fleets()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Failed to fetch fleets: %s", err)
                errors["base"] = "cannot_connect"

        if user_input is not None:
            try:
                # Validate fleet selection
                selected_fleets = user_input.get(CONF_FLEETS, [])

                # Create the config entry
                title = f"Balena Cloud ({self.user_info.get('username', 'Unknown')})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_TOKEN: self.api_token,
                        CONF_FLEETS: selected_fleets,
                    },
                    options={
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                        CONF_INCLUDE_OFFLINE_DEVICES: DEFAULT_INCLUDE_OFFLINE_DEVICES,
                    },
                )

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if not self.fleets:
            # If no fleets available, show error and go back
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_API_TOKEN): str,
                }),
                errors={"base": "no_fleets"},
            )

        # Create fleet selection schema
        fleet_options = {
            fleet_id: f"{fleet_name} (ID: {fleet_id})"
            for fleet_id, fleet_name in self.fleets.items()
        }

        return self.async_show_form(
            step_id="fleets",
            data_schema=vol.Schema({
                vol.Optional(CONF_FLEETS, default=list(self.fleets.keys())): vol.All(
                    cv.multi_select(fleet_options),
                    vol.Length(min=0),
                ),
            }),
            errors=errors,
            description_placeholders={
                "fleet_count": str(len(self.fleets)),
            },
        )

    async def _async_validate_input(self, data: Dict[str, Any]) -> None:
        """Validate the user input allows us to connect."""
        api = BalenaCloudAPIClient(data[CONF_API_TOKEN])

        try:
            # Test the connection and get user info
            self.user_info = await api.async_get_user_info()

        except BalenaCloudAuthenticationError as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise InvalidAuth from err
        except BalenaCloudAPIError as err:
            _LOGGER.error("Cannot connect to Balena Cloud: %s", err)
            raise CannotConnect from err

    async def _async_fetch_fleets(self) -> None:
        """Fetch available fleets."""
        api = BalenaCloudAPIClient(self.api_token)

        try:
            fleets_data = await api.async_get_fleets()
            self.fleets = {
                fleet["id"]: fleet["app_name"]
                for fleet in fleets_data
                if fleet.get("id") and fleet.get("app_name")
            }

        except BalenaCloudAPIError as err:
            _LOGGER.error("Failed to fetch fleets: %s", err)
            raise

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BalenaCloudOptionsFlowHandler:
        """Create the options flow."""
        return BalenaCloudOptionsFlowHandler(config_entry)


class BalenaCloudOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Balena Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(
                    CONF_INCLUDE_OFFLINE_DEVICES,
                    default=self.config_entry.options.get(
                        CONF_INCLUDE_OFFLINE_DEVICES, DEFAULT_INCLUDE_OFFLINE_DEVICES
                    ),
                ): bool,
            }),
        )