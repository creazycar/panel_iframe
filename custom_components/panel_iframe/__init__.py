"""
Custom Panel Iframe Integration for Home Assistant
Designed to work with the latest Home Assistant versions
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ICON, CONF_REQUIRE_ADMIN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

CONF_TITLE = "title"
CONF_DISABLE_PINNING = "disable_pinning"

DOMAIN = "panel_iframe"

DEFAULT_ICON = "mdi:iframe"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                cv.slug: vol.All(
                    vol.Schema(
                        {
                            vol.Required(CONF_TITLE): cv.string,
                            vol.Required(CONF_URL): cv.string,
                            vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.icon,
                            vol.Optional(CONF_REQUIRE_ADMIN, default=False): cv.boolean,
                            vol.Optional(CONF_DISABLE_PINNING, default=False): cv.boolean,
                        }
                    ),
                    # Validate URL
                    lambda val: validate_url(val[CONF_URL]) or val
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

def validate_url(url: str) -> bool:
    """Validate URL format."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise vol.Invalid(f"Invalid URL: {url}")
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Panel IFrame component."""
    hass.data.setdefault(DOMAIN, {})
    
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    # Process configured panels
    for panel_id, options in conf.items():
        try:
            # Validate URL format
            validate_url(options[CONF_URL])

            # Register panel
            await async_register_panel(
                hass,
                panel_id,
                options
            )
        except Exception as e:
            _LOGGER.error("Failed to register panel %s: %s", panel_id, e)
            continue

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panel IFrame entry."""
    try:
        # Register panel from config entry
        await async_register_panel(
            hass,
            entry.entry_id,
            {
                CONF_URL: entry.data[CONF_URL],
                CONF_TITLE: entry.data[CONF_TITLE],
                CONF_ICON: entry.data.get(CONF_ICON, DEFAULT_ICON),
                CONF_REQUIRE_ADMIN: entry.data.get(CONF_REQUIRE_ADMIN, False),
                CONF_DISABLE_PINNING: entry.data.get(CONF_DISABLE_PINNING, False),
            }
        )
        return True
    except Exception as e:
        _LOGGER.error("Failed to setup entry %s: %s", entry.entry_id, e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Panel IFrame entry."""
    try:
        # Remove panel
        frontend.async_remove_panel(hass, entry.entry_id)
        _LOGGER.debug("Successfully removed panel %s", entry.entry_id)
        return True
    except Exception as e:
        _LOGGER.error("Failed to remove panel %s: %s", entry.entry_id, e)
        return False


async def async_register_panel(
    hass: HomeAssistant,
    panel_id: str,
    options: Dict[str, Any]
) -> None:
    """Register a new panel."""
    try:
        # Verify frontend is loaded
        if frontend.DOMAIN not in hass.config.components:
            raise HomeAssistantError("Frontend is not loaded")

        # Prepare panel configuration
        panel_config = {
            "url": options[CONF_URL],
            "require_admin": options.get(CONF_REQUIRE_ADMIN, False),
            "disable_pinning": options.get(CONF_DISABLE_PINNING, False),
        }

        # Register the built-in panel
        frontend.async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title=options[CONF_TITLE],
            sidebar_icon=options.get(CONF_ICON, DEFAULT_ICON),
            frontend_url_path=panel_id,
            config=panel_config,
            require_admin=options.get(CONF_REQUIRE_ADMIN, False),
        )
        
        _LOGGER.info("Successfully registered panel '%s' with URL: %s", panel_id, options[CONF_URL])
        
    except ValueError as e:
        # Handle duplicate panel errors
        if "already registered" in str(e).lower():
            _LOGGER.warning("Panel %s already exists, removing and re-registering", panel_id)
            try:
                frontend.async_remove_panel(hass, panel_id)
                # Retry registration
                frontend.async_register_built_in_panel(
                    hass,
                    component_name="iframe",
                    sidebar_title=options[CONF_TITLE],
                    sidebar_icon=options.get(CONF_ICON, DEFAULT_ICON),
                    frontend_url_path=panel_id,
                    config=panel_config,
                    require_admin=options.get(CONF_REQUIRE_ADMIN, False),
                )
            except Exception as retry_error:
                _LOGGER.error("Retry registration failed for panel %s: %s", panel_id, retry_error)
        else:
            _LOGGER.error("ValueError registering panel %s: %s", panel_id, e)
    except Exception as e:
        _LOGGER.error("Unexpected error registering panel %s: %s", panel_id, e)
        raise


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Panel Iframe entry from version %s", entry.version)
    
    if entry.version == 1:
        # Update to version 2 with new schema
        new_data = {**entry.data}
        hass.config_entries.async_update_entry(
            entry, data=new_data, version=2
        )
        _LOGGER.info("Migration to version %s successful", entry.version)
    
    return True
