import asyncio
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import aiohttp
from urllib.parse import urlparse, urljoin

from .manifest import manifest

DOMAIN = manifest.domain
VERSION = manifest.version

# 替换废弃的 HttpProxy，适配新版 HA
class AsyncHttpProxy:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.parsed_url = urlparse(target_url)

    async def proxy_handler(self, request):
        path = request.match_info.get('path', '')
        full_url = urljoin(self.target_url, path)
        
        # 复制请求头
        headers = dict(request.headers)
        headers.pop('Host', None)
        
        # 创建客户端会话
        session = async_create_clientsession(request.app['hass'])
        try:
            async with session.request(
                method=request.method,
                url=full_url,
                headers=headers,
                data=await request.read(),
                params=request.query,
                allow_redirects=False
            ) as resp:
                # 构建响应
                response_headers = dict(resp.headers)
                # 移除可能导致问题的头
                response_headers.pop('Content-Encoding', None)
                
                return aiohttp.web.Response(
                    body=await resp.read(),
                    status=resp.status,
                    headers=response_headers
                )
        except Exception as e:
            return aiohttp.web.Response(
                status=500,
                text=f"Proxy error: {str(e)}"
            )

    def register(self, router):
        router.add_route(
            '*',
            f"/panel_iframe_proxy/{id(self)}/{{path:.*}}",
            self.proxy_handler
        )

    def get_url(self):
        return f"/panel_iframe_proxy/{id(self)}/"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置集成"""
    # 注册静态资源（适配新版 HA 路径注册方式）
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            "/panel_iframe_www",
            hass.config.path(f"custom_components/{DOMAIN}/www"),
            cache_headers=False
        )
    ])

    # 读取配置
    cfg = entry.options
    url_path = entry.entry_id
    title = entry.title
    mode = cfg.get('mode', '0')
    icon = cfg.get('icon', 'mdi:link-box-outline')
    url = cfg.get('url', '')
    require_admin = cfg.get('require_admin', False)
    proxy_access = cfg.get('proxy_access', False)

    if url:
        module_url = f"/panel_iframe_www/panel_iframe.js?v={VERSION}"
        
        # 处理代理访问
        if proxy_access:
            try:
                proxy = AsyncHttpProxy(url)
                proxy.register(hass.http.app.router)
                url = proxy.get_url()
            except Exception as e:
                hass.logger.error(f"Panel iframe proxy error: {e}")

        # 注册面板（使用新版 async_register_built_in_panel）
        await async_register_built_in_panel(
            hass,
            component_name="iframe",
            frontend_url_path=url_path,
            sidebar_title=title,
            sidebar_icon=icon,
            module_url=module_url,
            config={
                'mode': mode,
                'url': url
            },
            require_admin=require_admin
        )

    # 监听配置更新
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """更新配置选项"""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成"""
    return True
