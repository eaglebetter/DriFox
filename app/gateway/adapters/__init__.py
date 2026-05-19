# -*- coding: utf-8 -*-
"""
Gateway 平台适配器
"""
from app.gateway.adapters.wecom import WeComAdapter, check_wecom_requirements
from app.gateway.adapters.dingtalk import DingTalkAdapter, check_dingtalk_requirements

__all__ = [
    "WeComAdapter",
    "check_wecom_requirements",
    "DingTalkAdapter", 
    "check_dingtalk_requirements",
]