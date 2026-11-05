"""配置管理模块"""

import os
from pathlib import Path
from typing import List, Dict, Any
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
# 首先尝试加载当前目录的.env
load_dotenv()

class Settings(BaseSettings):
    """应用配置"""

    # 应用基本配置
    app_name: str = "travellucky"
    app_version: str = "2.0.0"
    debug: bool = False

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS配置 - 使用字符串,在代码中分割
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 高德地图API配置
    vite_amap_web_key: str = ""
    vite_amap_web_js_key: str = ""


    # 小红书配置
    xhs_cookie: str = ""

    # LLM配置 (从环境变量读取,由HelloAgents管理)
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "LLM_BASE_URL"),
    )
    openai_model: str = Field(
        default="gpt-4",
        validation_alias=AliasChoices("OPENAI_MODEL", "LLM_MODEL_ID"),
    )

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.cors_origins.split(',')]


# 创建全局配置实例
settings = Settings()
def _sync_env_from_settings() -> None:
    """将运行时配置同步到环境变量，兼容读取 env 的第三方组件。"""
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        os.environ["LLM_API_KEY"] = settings.openai_api_key
    if settings.openai_base_url:
        os.environ["OPENAI_BASE_URL"] = settings.openai_base_url
        os.environ["LLM_BASE_URL"] = settings.openai_base_url
    if settings.openai_model:
        os.environ["OPENAI_MODEL"] = settings.openai_model
        os.environ["LLM_MODEL_ID"] = settings.openai_model


_sync_env_from_settings()

_SECRET_SETTING_KEYS = {
    "openai_api_key",
    "xhs_cookie",
    "vite_amap_web_key",
}
_MASK_CHAR = "\u2022"


def _mask_secret(value: str) -> str:
    """返回不可还原掩码，仅保留少量首尾字符供用户辨认。"""
    if not value:
        return ""
    if len(value) <= 8:
        return _MASK_CHAR * 8
    return f"{value[:4]}{_MASK_CHAR * 8}{value[-4:]}"


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def get_runtime_settings() -> Dict[str, str]:
    """获取当前运行时配置（供前端设置页读取）。

    机密字段以掩码返回；进程内部需要真实值时直接读取 settings。
    """
    raw = {
        "vite_amap_web_key": settings.vite_amap_web_key or "",
        "vite_amap_web_js_key": settings.vite_amap_web_js_key or "",
        "xhs_cookie": settings.xhs_cookie or "",
        "openai_api_key": settings.openai_api_key or "",
        "openai_base_url": settings.openai_base_url or "",
        "openai_model": settings.openai_model or "",
    }
    return {
        key: _mask_secret(value) if key in _SECRET_SETTING_KEYS else value
        for key, value in raw.items()
    }


# 验证必要的配置
def validate_config():
    """验证配置是否完整"""
    warnings = []

    if not settings.vite_amap_web_key:
        warnings.append("VITE_AMAP_WEB_KEY未配置，景点地理编码等功能将不可用")

    llm_api_key = settings.openai_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        warnings.append("LLM API Key未配置，AI 生成功能将不可用")

    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")

    return True


# 打印配置信息(用于调试)
def print_config():
    """打印当前配置(隐藏敏感信息)"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"高德地图API Key: {'已配置' if settings.vite_amap_web_key else '未配置'}")
    print(f"高德地图JS Key: {'已配置' if settings.vite_amap_web_js_key else '未配置'}")
    print(f"小红书Cookie: {'已配置' if settings.xhs_cookie else '未配置'}")

    # 检查LLM配置
    llm_api_key = settings.openai_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_base_url = settings.openai_base_url
    llm_model = settings.openai_model

    print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    print(f"LLM Base URL: {llm_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"日志级别: {settings.log_level}")

