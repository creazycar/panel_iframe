from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from .manifest import manifest

DOMAIN = manifest.domain
mode_list = {
    '0': '默认',
    '1': '全屏',
    '2': '新页面',
    '3': '内置页面'
}

class SimpleConfigFlow(ConfigFlow, domain=DOMAIN):
    """配置流"""
    VERSION = 1
    reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """用户配置步骤"""
        errors = {}
        
        # 防止重复配置
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            DATA_SCHEMA = vol.Schema({
                vol.Required("title", description={"suggested_value": "侧边栏面板"}): str,
            })
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors=errors
            )

        # 检查标题唯一性
        await self.async_set_unique_id(user_input["title"])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=user_input['title'],
            data=user_input
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        """获取选项流"""
        return OptionsFlowHandler(entry)

class OptionsFlowHandler(OptionsFlow):
    """选项配置流"""
    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """用户选项配置步骤"""
        errors = {}
        options = self.config_entry.options

        if user_input is not None:
            # 清理输入
            user_input['icon'] = user_input['icon'].strip().replace('mdi-', 'mdi:')
            user_input['url'] = user_input['url'].strip()

            # 内置页面禁止代理
            if user_input['mode'] == '3':
                user_input['proxy_access'] = False

            # 更新选项
            return self.async_create_entry(title='', data=user_input)

        # 构建Schema（适配新版 HA 的 description 格式）
        DATA_SCHEMA = vol.Schema({
            vol.Required(
                "icon", 
                default=options.get('icon', 'mdi:link-box-outline'),
                description={"suggested_value": options.get('icon', 'mdi:link-box-outline'), "name": "图标"}
            ): str,
            vol.Required(
                "url", 
                default=options.get('url', ''),
                description={"suggested_value": options.get('url', ''), "name": "链接"}
            ): str,
            vol.Required(
                "mode", 
                default=options.get('mode', '0'),
                description={"suggested_value": options.get('mode', '0'), "name": "显示模式"}
            ): vol.In(mode_list),
            vol.Required(
                "require_admin", 
                default=options.get('require_admin', False),
                description={"suggested_value": options.get('require_admin', False), "name": "管理员可见"}
            ): bool,
            vol.Required(
                "proxy_access", 
                default=options.get('proxy_access', False),
                description={"suggested_value": options.get('proxy_access', False), "name": "代理访问（不懂勿选）"}
            ): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )
