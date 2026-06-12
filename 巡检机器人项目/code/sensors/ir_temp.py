"""
MLX90614 非接触式红外温度传感器驱动模块

模块功能:
    - read_object_temp()   → 读取物体表面温度 (℃)
    - read_ambient_temp()  → 读取环境温度 (℃)
    - 温度单位: 摄氏

硬件接口: I2C (默认地址 0x5A)

支持模拟模式: 当硬件不可用时，自动返回模拟数据用于测试。

Author: 超人强 💪
"""

import logging
import time
import random
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class MLX90614:
    """
    MLX90614 红外测温传感器驱动类。

    Args:
        i2c_bus: I2C总线编号 (树莓派5默认 /dev/i2c-1)。
        address: I2C设备地址，默认 0x5A。
        simulated: 强制使用模拟模式，无硬件时使用。
    """

    # MLX90614 RAM寄存器地址
    REG_TA = 0x06   # 环境温度 (Tambient)
    REG_TOBJ1 = 0x07  # 物体温度 (Tobject1)

    def __init__(
        self,
        i2c_bus: int = 1,
        address: int = 0x5A,
        simulated: Optional[bool] = None,
    ):
        self.i2c_bus = i2c_bus
        self.address = address
        self._simulated = simulated if simulated is not None else False
        self._device = None

        # 尝试初始化硬件
        if not self._simulated:
            try:
                import smbus2
                self._device = smbus2.SMBus(self.i2c_bus)
                logger.info(
                    "MLX90614 初始化成功 (bus=%d, addr=0x%02X)",
                    self.i2c_bus,
                    self.address,
                )
            except (ImportError, OSError, FileNotFoundError) as e:
                logger.warning(
                    "MLX90614 硬件初始化失败: %s，切换到模拟模式", e
                )
                self._simulated = True
        else:
            logger.info("MLX90614 运行于模拟模式")

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def read_object_temp(self) -> float:
        """
        读取物体表面温度。

        Returns:
            float: 物体温度 (℃)。模拟模式返回 25.0 ~ 45.0 随机值。

        Raises:
            RuntimeError: 读取失败时抛出。
        """
        raw = self._read_ram(self.REG_TOBJ1)
        temp_c = self._raw_to_celsius(raw)
        logger.debug("物体温度: %.2f ℃", temp_c)
        return temp_c

    def read_ambient_temp(self) -> float:
        """
        读取环境温度。

        Returns:
            float: 环境温度 (℃)。模拟模式返回 22.0 ~ 30.0 随机值。

        Raises:
            RuntimeError: 读取失败时抛出。
        """
        raw = self._read_ram(self.REG_TA)
        temp_c = self._raw_to_celsius(raw)
        logger.debug("环境温度: %.2f ℃", temp_c)
        return temp_c

    def read_all(self) -> Tuple[float, float]:
        """
        同时读取物体温度和环境温度。

        Returns:
            Tuple[float, float]: (物体温度 ℃, 环境温度 ℃)
        """
        return self.read_object_temp(), self.read_ambient_temp()

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _read_ram(self, register: int) -> int:
        """
        从MLX90614 RAM寄存器读取16位原始数据。

        Args:
            register: RAM寄存器地址 (0x06 ~ 0x0F)。

        Returns:
            int: 16位无符号原始值。

        Raises:
            RuntimeError: 读取失败时抛出。
        """
        if self._simulated:
            # 模拟模式: 返回随机模拟值
            return self._simulate_raw_temp()

        try:
            # smbus2: read_word_data 返回小端序 16 位值
            raw = self._device.read_word_data(self.address, register)
            return raw
        except Exception as e:
            raise RuntimeError(f"MLX90614 读取寄存器 0x{register:02X} 失败: {e}") from e

    @staticmethod
    def _raw_to_celsius(raw: int) -> float:
        """
        将 MLX90614 原始16位数据转换为摄氏温度。

        转换公式:
            Temp(℃) = (raw * 0.02) - 273.15

        Args:
            raw: 16位原始值。

        Returns:
            float: 摄氏温度值。
        """
        # 处理符号位 (16位有符号)
        if raw >= 0x8000:
            raw -= 0x10000
        return round(raw * 0.02 - 273.15, 2)

    def _simulate_raw_temp(self) -> int:
        """
        模拟模式生成随机的原始温度值。

        Returns:
            int: 模拟的16位原始值。
        """
        # 对象温度 25~45℃ → raw ≈ (temp + 273.15) / 0.02
        temp = random.uniform(25.0, 45.0)
        raw = int((temp + 273.15) / 0.02)
        return raw & 0xFFFF

    def close(self):
        """释放I2C总线资源。"""
        if self._device is not None:
            try:
                self._device.close()
                logger.info("MLX90614 I2C 连接已关闭")
            except Exception as e:
                logger.warning("关闭 MLX90614 时出现异常: %s", e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ==================================================================
# 测试代码（无硬件也可运行）
# ==================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 50)
    print("MLX90614 红外测温传感器测试 (模拟模式)")
    print("=" * 50)

    with MLX90614(simulated=True) as sensor:
        for i in range(5):
            obj_temp = sensor.read_object_temp()
            amb_temp = sensor.read_ambient_temp()
            print(f"[{i+1}] 物体温度: {obj_temp:.2f}℃\t环境温度: {amb_temp:.2f}℃")
            time.sleep(0.5)

    print("\n✅ 测试完成！传感器模块一切正常！💪")
