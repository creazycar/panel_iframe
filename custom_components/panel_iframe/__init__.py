"""
Panel Iframe Component for Home Assistant
This module has been updated to work with the latest version of Home Assistant
"""
import asyncio
import logging
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ICON, CONF_REQUIRE_ADMIN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import collection
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

CONF_TITLE = "title"
CONF_DISABLE_PINNING = "disable_pinning"

DOMAIN = "panel_iframe"

CONF_RELATIVE_PANEL_URL = "relative_panel_url"

DEFAULT_ICON = "mdi:iframe"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                str: {
                    vol.Required(CONF_TITLE): cv.string,
                    vol.Required(CONF_URL): cv.string,
                    vol.Optional(CONF_RELATIVE_PANEL_URL): cv.string,
                    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.icon,
                    vol.Optional(CONF_REQUIRE_ADMIN, default=False): cv.boolean,
                    vol.Optional(CONF_DISABLE_PINNING, default=False): cv.boolean,
                }
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Panel IFrame component."""
    hass.data.setdefault(DOMAIN, {})
    
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    # Create panel iframes
    for panel_id, options in conf.items():
        # Make sure required values are set
        assert CONF_URL in options
        assert CONF_TITLE in options

        # Set default value for optional values
        if CONF_ICON not in options:
            options[CONF_ICON] = DEFAULT_ICON
        if CONF_REQUIRE_ADMIN not in options:
            options[CONF_REQUIRE_ADMIN] = False
        if CONF_DISABLE_PINNING not in options:
            options[CONF_DISABLE_PINNING] = False

        # Register panel
        await async_register_panel(
            hass,
            panel_id,
            options[CONF_URL],
            options.get(CONF_RELATIVE_PANEL_URL),
            options[CONF_TITLE],
            options[CONF_ICON],
            options[CONF_REQUIRE_ADMIN],
            options[CONF_DISABLE_PINNING],
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panel IFrame entry."""
    # Register panel
    await async_register_panel(
        hass,
        entry.entry_id,
        entry.data[CONF_URL],
        None,  # relative_panel_url
        entry.data[CONF_TITLE],
        entry.data.get(CONF_ICON, DEFAULT_ICON),
        entry.data.get(CONF_REQUIRE_ADMIN, False),
        entry.data.get(CONF_DISABLE_PINNING, False),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Panel IFrame entry."""
    try:
        hass.components.frontend.async_remove_panel(entry.entry_id)
        _LOGGER.debug("Successfully removed panel %s", entry.entry_id)
    except KeyError:
        _LOGGER.error("Panel %s could not be removed. Panel was not registered", entry.entry_id)
    return True


async def async_register_panel(
    hass,
    panel_id,
    url,
    relative_panel_url,
    title,
    icon,
    require_admin,
    disable_pinning,
) -> None:
    """Register a new panel."""
    # Ensure frontend is loaded
    if frontend.DOMAIN not in hass.config.components:
        raise HomeAssistantError("Frontend is not loaded")

    # Determine panel URL
    if relative_panel_url is None:
        relative_panel_url = f"/local/panel_iframe/{slugify(panel_id)}"

    # Register the panel
    try:
        hass.components.frontend.async_register_built_in_panel(
            component_name="iframe",
            sidebar_title=title,
            sidebar_icon=icon,
            frontend_url_path=panel_id,
            config={
                "_panel_custom": {
                    "html_url": f"{relative_panel_url}?{hass.data['lovelace']['mode']}",
                    "js_url": f"/local/panel_iframe/iframe.js?{hass.data['lovelace']['mode']}",
                },
                "url": url,
                "require_admin": require_admin,
                "disable_pinning": disable_pinning,
            },
            require_admin=require_admin,
        )
        _LOGGER.debug("Successfully registered panel %s", panel_id)
    except ValueError as e:
        _LOGGER.error("Could not register panel %s: %s", panel_id, e)
