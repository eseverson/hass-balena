"""Config flow for Balena Cloud integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_API_TOKEN
from homeassistant.helpers import config_validation as cv

from .api import (BalenaCloudAPIClient, BalenaCloudAPIError,
                  BalenaCloudAuthenticationError)
from .const import (CONF_FLEETS, CONF_INCLUDE_OFFLINE_DEVICES,
                    CONF_UPDATE_INTERVAL, DEFAULT_INCLUDE_OFFLINE_DEVICES,
                    DEFAULT_UPDATE_INTERVAL, DOMAIN)

_LOGGER = logging.getLogger(__name__)

ERRORS = {
    "invalid_auth": "Invalid authentication",
    "cannot_connect": "Cannot connect to Balena Cloud",
    "unknown": "Unexpected error occurred",
    "no_fleets": "No fleets found or accessible with this token",
}


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


@config_entries.HANDLERS.register(DOMAIN)
class BalenaCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Balena Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.api_token: str | None = None
        self.fleets: Dict[str, str] = {}
        self.user_info: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
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
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "api_docs_url": "https://www.balena.io/docs/reference/api/overview/",
            },
        )

    async def async_step_fleets(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.ConfigFlowResult:
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
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_API_TOKEN): str,
                    }
                ),
                errors={"base": "no_fleets"},
            )

        # Create fleet selection schema
        fleet_options = {
            str(fleet_id): f"{fleet_name} (ID: {fleet_id})"
            for fleet_id, fleet_name in self.fleets.items()
        }

        return self.async_show_form(
            step_id="fleets",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FLEETS, default=list(self.fleets.keys())
                    ): vol.All(
                        cv.multi_select(fleet_options),
                        vol.Length(min=0),
                    ),
                }
            ),
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
                str(fleet["id"]): fleet["app_name"]
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
        self.fleets: Dict[str, str] = {}

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}

        # Fetch fleets if not already done (non-blocking)
        if not self.fleets:
            try:
                await self._async_fetch_fleets()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Failed to fetch fleets for options flow: %s", err)
                # Continue without fleet selection

        if user_input is not None:
            try:
                # Get current fleet selection from entry.data
                current_fleets = self.config_entry.data.get(CONF_FLEETS, [])
                # Only update fleet selection if it was provided in user_input
                if CONF_FLEETS in user_input:
                    selected_fleets = user_input.get(CONF_FLEETS, current_fleets)
                else:
                    selected_fleets = current_fleets

                # Update the config entry data with new fleet selection
                # and options with other settings
                new_data = {**self.config_entry.data, CONF_FLEETS: selected_fleets}
                new_options = {
                    CONF_UPDATE_INTERVAL: user_input.get(
                        CONF_UPDATE_INTERVAL,
                        self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ),
                    CONF_INCLUDE_OFFLINE_DEVICES: user_input.get(
                        CONF_INCLUDE_OFFLINE_DEVICES,
                        self.config_entry.options.get(
                            CONF_INCLUDE_OFFLINE_DEVICES,
                            DEFAULT_INCLUDE_OFFLINE_DEVICES,
                        ),
                    ),
                }

                # Update entry.data with the fleet selection. entry.options is
                # written by HA when this flow returns async_create_entry below
                # — passing data={} there would clobber the options we just set.
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )

                # Schedule a reload through HA so the entry's state machine
                # transitions correctly (LOADED → NOT_LOADED → LOADED). The
                # previous manual reload bypassed this and left platforms in
                # a state where entities reported unavailable after reconfig.
                self.hass.config_entries.async_schedule_reload(
                    self.config_entry.entry_id
                )

                return self.async_create_entry(title="", data=new_options)

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Get current selections
        current_fleets = self.config_entry.data.get(CONF_FLEETS, [])
        if not current_fleets and self.fleets:
            # If no fleets selected, default to all fleets
            current_fleets = list(self.fleets.keys())

        # Create fleet selection schema
        fleet_options = {}
        if self.fleets:
            fleet_options = {
                str(fleet_id): f"{fleet_name} (ID: {fleet_id})"
                for fleet_id, fleet_name in self.fleets.items()
            }

        # Drop any previously-selected fleet IDs that no longer exist (e.g.
        # the fleet was deleted in Balena Cloud). Otherwise voluptuous rejects
        # the form default with "fleet id is not a valid option" and the user
        # can't reconfigure.
        if fleet_options:
            valid_keys = set(fleet_options.keys())
            current_fleets = [
                str(f) for f in current_fleets if str(f) in valid_keys
            ]

        schema_dict = {
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            vol.Optional(
                CONF_INCLUDE_OFFLINE_DEVICES,
                default=self.config_entry.options.get(
                    CONF_INCLUDE_OFFLINE_DEVICES,
                    DEFAULT_INCLUDE_OFFLINE_DEVICES,
                ),
            ): bool,
        }

        # Add fleet selection if we have fleets
        if fleet_options:
            schema_dict[
                vol.Optional(CONF_FLEETS, default=current_fleets)
            ] = vol.All(cv.multi_select(fleet_options), vol.Length(min=0))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def _async_fetch_fleets(self) -> None:
        """Fetch available fleets."""
        api_token = self.config_entry.data.get(CONF_API_TOKEN)
        if not api_token:
            _LOGGER.warning("No API token found in config entry")
            return

        try:
            api = BalenaCloudAPIClient(api_token)
            fleets_data = await api.async_get_fleets()
            self.fleets = {
                str(fleet["id"]): fleet["app_name"]
                for fleet in fleets_data
                if fleet.get("id") and fleet.get("app_name")
            }
            _LOGGER.debug("Fetched %d fleets for options flow", len(self.fleets))

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to fetch fleets: %s", err)
            # Don't raise - allow options flow to continue without fleet selection
            self.fleets = {}
