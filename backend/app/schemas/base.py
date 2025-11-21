"""
基础配置 Schema 定义。

包含区域、风场、波浪谱、离散化、时间等配置模型。
"""

from typing import Optional

from pydantic import BaseModel, Field, validator


class Region(BaseModel):
    """矩形区域定义（经纬度 + 深度）。"""

    lon_min: float = Field(..., description="最小经度（度）")
    lat_min: float = Field(..., description="最小纬度（度）")
    depth_min: float = Field(..., description="对应点水深（米）")
    lon_max: float = Field(..., description="最大经度（度）")
    lat_max: float = Field(..., description="最大纬度（度）")
    depth_max: float = Field(..., description="对应点水深（米）")

    @validator("lon_max")
    def validate_lon_range(cls, v, values):
        """验证经度范围合理性。"""
        if "lon_min" in values and v <= values["lon_min"]:
            raise ValueError("lon_max must be greater than lon_min")
        return v

    @validator("lat_max")
    def validate_lat_range(cls, v, values):
        """验证纬度范围合理性。"""
        if "lat_min" in values and v <= values["lat_min"]:
            raise ValueError("lat_max must be greater than lat_min")
        return v


class WindConfig(BaseModel):
    """风场模型参数（当前版本为固定风场）。"""

    wind_speed: float = Field(
        default=10.0, ge=0, le=40, description="风速（m/s）"
    )
    wind_direction_deg: float = Field(
        default=270.0,
        ge=0,
        le=360,
        description="风向（度），0°表示从北向南，角度顺时针增加",
    )
    reference_height_m: float = Field(
        default=10.0, description="风速参考高度（米）"
    )


class SpectrumConfig(BaseModel):
    """波浪谱模型参数（Pierson-Moskowitz or JONSWAP）。"""

    spectrum_model_type: str = Field(
        default="PM", description="光谱模型类型", pattern="^(PM|JONSWAP)$"
    )
    Hs: float = Field(
        default=2.0, ge=0, le=15, description="显著波高（m）"
    )
    Tp: float = Field(
        default=8.0, ge=2, le=20, description="峰值周期（s）"
    )
    main_wave_direction_deg: Optional[float] = Field(
        default=None, ge=0, le=360, description="主浪向（度），通常与风向接近"
    )
    directional_spread_deg: float = Field(
        default=30.0, ge=5, le=90, description="波向扩散宽度（度）"
    )
    gamma: float = Field(
        default=3.3,
        ge=1,
        le=7,
        description="JONSWAP 峰锐系数，仅 spectrum_model_type = JONSWAP 时使用",
    )


class DiscretizationConfig(BaseModel):
    """空间离散化配置。"""

    dx: float = Field(
        default=0.05,
        gt=0,
        description="经度方向离散间隔（度或等效距离）",
    )
    dy: float = Field(
        default=0.05,
        gt=0,
        description="纬度方向离散间隔（度或等效距离）",
    )
    max_points: int = Field(
        default=5000,
        ge=1,
        description="最大离散点数量上限，用于控制性能和内存",
    )


class TimeConfig(BaseModel):
    """时间离散配置。"""

    dt_backend: float = Field(
        default=0.2,
        gt=0,
        description="后端仿真时间步长（秒），例如 0.2 表示 200ms",
    )
    T_total: Optional[float] = Field(
        default=None,
        description="总仿真时长（秒），None 或 -1 表示无限制持续运行",
    )
    cache_retention_time: Optional[float] = Field(
        default=None,
        gt=0,
        description="缓存保留时间（秒），None 表示不限制，超过此时间的旧帧将被淘汰。例如 60 表示只保留最近 60 秒的帧",
    )

    @validator("T_total")
    def validate_T_total(cls, v):
        """验证 T_total，-1 转换为 None 表示无限制。"""
        if v is None or v == -1:
            return None
        if v <= 0:
            raise ValueError("T_total must be greater than 0, or use -1/None for unlimited")
        return v

