# -*- coding: utf-8 -*-
"""
Gateway 配置管理

使用统一的 Settings 配置管理。
"""
from __future__ import annotations

from typing import Optional

from app.gateway.base import Platform, PlatformConfig


def get_gateway_config() -> "GatewayConfigHelper":
    """获取 Gateway 配置辅助类"""
    return GatewayConfigHelper()


class GatewayConfigHelper:
    """
    Gateway 配置辅助类
    
    封装统一的 Settings 配置，提供便捷的访问接口。
    """
    
    @staticmethod
    def get_platform_config(platform: Platform) -> PlatformConfig:
        """
        获取平台配置
        
        Args:
            platform: 平台枚举
            
        Returns:
            PlatformConfig
        """
        from app.utils.config import Settings
        cfg = Settings.get_instance()
        
        if platform == Platform.WECOM:
            return PlatformConfig(
                enabled=cfg.gateway_wecom_enabled.value,
                platform=Platform.WECOM,
                bot_id=cfg.gateway_wecom_bot_id.value,
                secret=cfg.gateway_wecom_secret.value,
                websocket_url=cfg.gateway_wecom_websocket_url.value,
            )
        elif platform == Platform.DINGTALK:
            return PlatformConfig(
                enabled=cfg.gateway_dingtalk_enabled.value,
                platform=Platform.DINGTALK,
                client_id=cfg.gateway_dingtalk_client_id.value,
                client_secret=cfg.gateway_dingtalk_client_secret.value,
            )
        else:
            return PlatformConfig(enabled=False, platform=platform)
    
    @staticmethod
    def set_platform_config(platform: Platform, config: PlatformConfig) -> None:
        """
        设置平台配置
        
        Args:
            platform: 平台枚举
            config: 平台配置
        """
        from app.utils.config import Settings
        cfg = Settings.get_instance()
        
        if platform == Platform.WECOM:
            cfg.set(cfg.gateway_wecom_enabled, config.enabled, save=True)
            if config.bot_id is not None:
                cfg.set(cfg.gateway_wecom_bot_id, config.bot_id, save=True)
            if config.secret is not None:
                cfg.set(cfg.gateway_wecom_secret, config.secret, save=True)
            if config.websocket_url is not None:
                cfg.set(cfg.gateway_wecom_websocket_url, config.websocket_url, save=True)
        elif platform == Platform.DINGTALK:
            cfg.set(cfg.gateway_dingtalk_enabled, config.enabled, save=True)
            if config.client_id is not None:
                cfg.set(cfg.gateway_dingtalk_client_id, config.client_id, save=True)
            if config.client_secret is not None:
                cfg.set(cfg.gateway_dingtalk_client_secret, config.client_secret, save=True)
    
    @staticmethod
    def is_platform_enabled(platform: Platform) -> bool:
        """检查平台是否启用"""
        from app.utils.config import Settings
        cfg = Settings.get_instance()
        
        if platform == Platform.WECOM:
            return cfg.gateway_wecom_enabled.value
        elif platform == Platform.DINGTALK:
            return cfg.gateway_dingtalk_enabled.value
        return False
    
    @staticmethod
    def set_platform_enabled(platform: Platform, enabled: bool) -> None:
        """设置平台启用状态"""
        from app.utils.config import Settings
        cfg = Settings.get_instance()
        
        if platform == Platform.WECOM:
            cfg.set(cfg.gateway_wecom_enabled, enabled, save=True)
        elif platform == Platform.DINGTALK:
            cfg.set(cfg.gateway_dingtalk_enabled, enabled, save=True)
