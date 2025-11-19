"""
海浪环境模型业务服务包。

按功能拆分为：
- `wind`：风场模型（当前为固定风模型，后续可扩展为随时间变化模型）
- `spectrum`：波浪谱模型（Pierson-Moskowitz、JONSWAP 等）
- `simulation`：区域海浪模拟（在离散网格上计算海浪高度场）
- `interpolation`：单点查询插值（空间双线性插值）
"""


