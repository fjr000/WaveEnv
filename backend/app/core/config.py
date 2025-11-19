"""
全局配置与模型参数配置占位模块。

后续可在此处集中管理：
- 时间步长（默认 200ms，可配置）
- 区域离散化间隔与点数上限
- 默认风场模型 / 波浪谱模型选择
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Pydantic 1.x 兼容
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用配置（仅结构占位，具体字段后续补充）。"""

    app_name: str = "WaveEnv Backend"


settings = Settings()


