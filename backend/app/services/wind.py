"""
风场模型服务。

提供固定风场的创建与管理。
"""

from app.models.wind import WindField
from app.schemas.base import WindConfig


def create_wind_field(config: WindConfig) -> WindField:
    """
    创建固定风场。

    Args:
        config: 风场配置

    Returns:
        风场对象
    """
    return WindField(
        wind_speed=config.wind_speed,
        wind_direction_deg=config.wind_direction_deg,
        reference_height_m=config.reference_height_m,
    )
