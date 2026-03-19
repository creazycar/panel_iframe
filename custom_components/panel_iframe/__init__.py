"""
Panel Iframe Integration for Home Assistant
Complete implementation for latest HA versions
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

    # Process configured panels
    for panel_id, options in conf.items():
        try:
            # Validate URL format
            parsed_url = urlparse(options[CONF_URL])
            if not parsed_url.scheme or not parsed_url.netloc:
                _LOGGER.error("Invalid URL format for panel %s: %s", panel_id, options[CONF_URL])
                continue

            # Set default values
            panel_options = {
                CONF_URL: options[CONF_URL],
                CONF_TITLE: options[CONF_TITLE],
                CONF_ICON: options.get(CONF_ICON, DEFAULT_ICON),
                CONF_REQUIRE_ADMIN: options.get(CONF_REQUIRE_ADMIN, False),
                CONF_DISABLE_PINNING: options.get(CONF_DISABLE_PINNING, False),
                CONF_RELATIVE_PANEL_URL: options.get(CONF_RELATIVE_PANEL_URL)
            }

            # Register panel
            await async_register_panel(
                hass,
                panel_id,
                panel_options
            )
        except Exception as e:
            _LOGGER.error("Failed to register panel %s: %s", panel_id, e)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panel IFrame entry."""
    try:
        # Prepare panel options from config entry
        panel_options = {
            CONF_URL: entry.data[CONF_URL],
            CONF_TITLE: entry.data[CONF_TITLE],
            CONF_ICON: entry.data.get(CONF_ICON, DEFAULT_ICON),
            CONF_REQUIRE_ADMIN: entry.data.get(CONF_REQUIRE_ADMIN, False),
            CONF_DISABLE_PINNING: entry.data.get(CONF_DISABLE_PINNING, False),
            CONF_RELATIVE_PANEL_URL: None  # Will be auto-generated
        }
        
        # Register panel
        await async_register_panel(
            hass,
            entry.entry_id,
            panel_options
        )
        return True
    except Exception as e:
        _LOGGER.error("Failed to setup entry %s: %s", entry.entry_id, e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Panel IFrame entry."""
    try:
        # Remove panel using the correct frontend method
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
        # Ensure frontend is loaded
        if frontend.DOMAIN not in hass.config.components:
            raise HomeAssistantError("Frontend is not loaded")

        # Generate relative panel URL if not provided
        relative_panel_url = options.get(CONF_RELATIVE_PANEL_URL)
        if relative_panel_url is None:
            relative_panel_url = f"/local/panel_iframe/{slugify(panel_id)}"

        # Prepare panel configuration
        panel_config = {
            "url": options[CONF_URL],
            "require_admin": options[CONF_REQUIRE_ADMIN],
            "disable_pinning": options[CONF_DISABLE_PINNING],
        }

        # Register the built-in panel with error handling
        frontend.async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title=options[CONF_TITLE],
            sidebar_icon=options[CONF_ICON],
            frontend_url_path=panel_id,
            config=panel_config,
            require_admin=options[CONF_REQUIRE_ADMIN],
        )
        
        _LOGGER.info("Successfully registered panel '%s' with URL: %s", panel_id, options[CONF_URL])
        
    except ValueError as e:
        # This catches duplicate panel registration errors
        if "Panel id already registered" in str(e):
            _LOGGER.warning("Panel %s already exists, removing and re-registering", panel_id)
            try:
                frontend.async_remove_panel(hass, panel_id)
                # Retry registration
                frontend.async_register_built_in_panel(
                    hass,
                    component_name="iframe",
                    sidebar_title=options[CONF_TITLE],
                    sidebar_icon=options[CONF_ICON],
                    frontend_url_path=panel_id,
                    config=panel_config,
                    require_admin=options[CONF_REQUIRE_ADMIN],
                )
            except Exception as retry_error:
                _LOGGER.error("Retry registration failed for panel %s: %s", panel_id, retry_error)
        else:
            _LOGGER.error("ValueError registering panel %s: %s", panel_id, e)
    except Exception as e:
        _LOGGER.error("Unexpected error registering panel %s: %s", panel_id, e)
        raise


# For backward compatibility
async def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup function for older Home Assistant versions."""
    return await async_setup(hass, config)


# Additional helper functions for iframe rendering
async def async_render_iframe_panel(hass: HomeAssistant, panel_id: str, options: Dict[str, Any]):
    """Render an iframe panel directly."""
    from aiohttp import web
    
    async def iframe_handler(request):
        """Handle iframe requests."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{options[CONF_TITLE]}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    overflow: hidden;
                    background-color: white;
                }}
                iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
            </style>
        </head>
        <body>
            <iframe 
                src="{options[CONF_URL]}" 
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-top-navigation"
                referrerpolicy="no-referrer"
            ></iframe>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    # Register the handler
    hass.http.app.router.add_get(f"/local/panel_iframe/{slugify(panel_id)}", iframe_handler)
