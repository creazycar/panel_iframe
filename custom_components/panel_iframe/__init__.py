"""
Panel Iframe Custom Component for Home Assistant
Compatible with latest Home Assistant versions
"""
import logging
from typing import Dict, Any
from homeassistant.components import frontend
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

DOMAIN = "panel_iframe"
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional("panels"): vol.Schema(
                    {
                        str: {
                            vol.Required("title"): str,
                            vol.Required("icon", default="mdi:iframe"): str,
                            vol.Required("url"): str,
                            vol.Optional("require_admin", default=False): bool,
                        }
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Panel Iframe component."""
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    panels = conf.get("panels", {})

    for panel_id, panel_data in panels.items():
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "manual"},
                data={
                    "panel_id": panel_id,
                    "title": panel_data["title"],
                    "icon": panel_data["icon"],
                    "url": panel_data["url"],
                    "require_admin": panel_data.get("require_admin", False),
                },
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panel Iframe entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register the custom panel
    hass.http.register_view(PanelIframeView(
        entry.entry_id,
        entry.data["panel_id"],
        entry.data["title"],
        entry.data["icon"],
        entry.data["url"],
        entry.data.get("require_admin", False)
    ))
    
    return True

class PanelIframeView:
    """Serve the iframe panel."""
    
    url = "/local/panel_iframe/{path:.*}"
    requires_auth = False
    
    def __init__(self, entry_id, panel_id, title, icon, url, require_admin):
        self.name = f"panel_iframe_{panel_id}"
        self.panel_id = panel_id
        self.title = title
        self.icon = icon
        self.url = url
        self.require_admin = require_admin
        self.registered = False
        
    def register(self, app):
        """Register the view with the HTTP app."""
        if not self.registered:
            app.router.add_get(f"/api/panel_iframe/{self.panel_id}", self.get_config)
            app.router.add_get(f"/panel_iframe/{self.panel_id}", self.get_panel)
            self.registered = True
            
    async def get_config(self, request):
        """Return panel configuration."""
        from aiohttp import web
        return web.json_response({
            "component_name": "iframe",
            "config": {
                "title": self.title,
                "icon": self.icon,
                "url": self.url,
                "require_admin": self.require_admin
            }
        })
        
    async def get_panel(self, request):
        """Serve the iframe panel."""
        from aiohttp import web
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.title}</title>
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
    <iframe src="{self.url}" sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-top-navigation"></iframe>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')

# Add a simple setup function that Home Assistant can call
async def setup(hass, config):
    """Setup function for Home Assistant."""
    _LOGGER.info("Setting up Panel Iframe integration")
    return True
