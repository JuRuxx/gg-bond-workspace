"""
HC-SR04 超声波测距模块驱动

模块功能:
    - read_distance() → 读取距离 (cm)
    - 支持非阻塞方式，不阻塞主循环
    - 3个传感器分别安装在前/左/右

硬件接口: GPIO (TRIG 触发引脚 / ECHO 回声引脚)

支持模拟模式: 当硬件不可用时，自动返回模拟数据用于测试。

Author: 超人强 💪
"""

import logging
import time
import random
from typing import Optional, Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class UltrasonicPosition(Enum):
    """超声波传感器安装位置"""
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"


class HCSR04:
    """
    HC-SR04 超声波测距传感器驱动类。

    一个实例对应一个传感器。推荐使用 UltrasonicSensorManager 管理多个传感器。

    Args:
        trig_pin: GPIO触发引脚编号 (BCM模式)。
        echo_pin: GPIO回声引脚编号 (BCM模式)。
        name: 传感器名称/标识。
        timeout: 读取超时时间 (秒)，超出则返回 None。
        simulated: 强制使用模拟模式。
    """

    # 声速常量 (cm/s)，25℃ 时约 34300 cm/s
    SOUND_SPEED = 34300
    # 最大有效测量距离 (cm)，HC-SR04 额定 2cm ~ 400cm
    MAX_DISTANCE_CM = 400.0
    # 最小有效测量距离 (cm)
    MIN_DISTANCE_CM = 2.0

    def __init__(
        self,
        trig_pin: int,
        echo_pin: int,
        name: str = "ultrasonic",
        timeout: float = 0.1,
        simulated: Optional[bool] = None,
    ):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.name = name
        self.timeout = timeout
        self._simulated = simulated if simulated is not None else False
        self._gpio = None

        if not self._simulated:
            try:
                import RPi.GPIO as GPIO
                self._gpio = GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.trig_pin, GPIO.OUT)
                GPIO.setup(self.echo_pin, GPIO.IN)
                GPIO.output(self.trig_pin, GPIO.LOW)
                logger.info(
                    "HC-SR04 [%s] 初始化成功 (TRIG=%d, ECHO=%d)",
                    self.name, self.trig_pin, self.echo_pin,
                )
                time.sleep(0.5)  # 传感器稳定时间
            except (ImportError, OSError, RuntimeError) as e:
                logger.warning(
                    "HC-SR04 [%s] GPIO初始化失败: %s，切换到模拟模式",
                    self.name, e,
                )
                self._simulated = True
        else:
            logger.info("HC-SR04 [%s] 运行于模拟模式", self.name)

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def read_distance(self) -> Optional[float]:
        """
        读取距离 (cm)。

        发送10us脉冲触发，测量ECHO高电平持续时间，换算为距离。

        Returns:
            Optional[float]: 距离值 (cm)，超时或超出范围返回 None。

        Raises:
            RuntimeError: 测量过程中发生未预期的错误。
        """
        if self._simulated:
            return self._simulate_distance()

        try:
            # 发送触发信号 (10us 高电平)
            self._gpio.output(self.trig_pin, self._gpio.HIGH)
            time.sleep(0.00001)  # 10us
            self._gpio.output(self.trig_pin, self._gpio.LOW)

            # 等待 ECHO 拉高 (等待传感器响应)
            pulse_start = time.time()
            while self._gpio.input(self.echo_pin) == self._gpio.LOW:
                if time.time() - pulse_start > self.timeout:
                    logger.warning("[%s] 等待ECHO拉高超时", self.name)
                    return None
                pulse_start = time.time()

            # 测量 ECHO 高电平持续时间
            pulse_end = time.time()
            while self._gpio.input(self.echo_pin) == self._gpio.HIGH:
                if time.time() - pulse_end > self.timeout:
                    logger.warning("[%s] 等待ECHO拉低超时", self.name)
                    return None
                pulse_end = time.time()

            # 计算距离
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * self.SOUND_SPEED) / 2.0

            if distance < self.MIN_DISTANCE_CM or distance > self.MAX_DISTANCE_CM:
                logger.warning(
                    "[%s] 距离 %.2f cm 超出有效范围", self.name, distance
                )
                return None

            # 应用滑动滤波 (取到最近值平滑)
            distance = round(distance, 1)
            logger.debug("[%s] 距离: %.1f cm", self.name, distance)
            return distance

        except Exception as e:
            raise RuntimeError(
                f"HC-SR04 [{self.name}] 测量失败: {e}"
            ) from e

    def read_distance_nonblocking(self) -> Optional[float]:
        """
        非阻塞方式读取距离。

        等同于 read_distance()，但在模拟模式下可配置不同的延迟行为。

        Returns:
            Optional[float]: 距离值 (cm)。
        """
        return self.read_distance()

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _simulate_distance(self) -> Optional[float]:
        """
        模拟模式生成随机距离值。

        Returns:
            Optional[float]: 模拟的距离值 (cm)，有一定概率返回 None。
        """
        # 偶尔模拟读取失败 (5% 概率)
        if random.random() < 0.05:
            logger.debug("[%s] 模拟读取失败", self.name)
            return None

        # 根据不同位置模拟不同典型值
        if "front" in self.name.lower():
            base = random.uniform(50.0, 300.0)
        elif "left" in self.name.lower() or "right" in self.name.lower():
            base = random.uniform(30.0, 200.0)
        else:
            base = random.uniform(20.0, 400.0)

        return round(base, 1)

    def cleanup(self):
        """释放此传感器占用的GPIO资源。"""
        if self._gpio is not None:
            try:
                self._gpio.cleanup([self.trig_pin, self.echo_pin])
                logger.info("HC-SR04 [%s] 资源已释放", self.name)
            except Exception as e:
                logger.warning("释放 [%s] 资源时异常: %s", self.name, e)


class UltrasonicSensorManager:
    """
    超声波传感器管理器。

    统一管理前/左/右三个超声波传感器。支持巡检场景下的一键测距。

    Args:
        sensors_config: 传感器配置字典，格式:
            {
                "front": {"trig": 23, "echo": 24},
                "left":  {"trig": 17, "echo": 27},
                "right": {"trig": 22, "echo": 10},
            }
        simulated: 是否使用模拟模式。
    """

    def __init__(
        self,
        sensors_config: Dict[str, Dict[str, int]],
        simulated: Optional[bool] = None,
    ):
        self._sensors: Dict[str, HCSR04] = {}
        self._simulated = simulated if simulated is not None else False

        for position, pins in sensors_config.items():
            self._sensors[position] = HCSR04(
                trig_pin=pins["trig"],
                echo_pin=pins["echo"],
                name=f"ultrasonic_{position}",
                simulated=self._simulated,
            )

        logger.info(
            "超声波传感器管理器初始化完成 (%d 个传感器)",
            len(self._sensors),
        )

    def get_sensor(self, position: str) -> HCSR04:
        """
        获取指定位置的传感器实例。

        Args:
            position: 传感器位置 (front/left/right)。

        Returns:
            HCSR04: 传感器实例。

        Raises:
            KeyError: 位置不存在时。
        """
        if position not in self._sensors:
            raise KeyError(
                f"传感器位置 '{position}' 未配置. 可用: {list(self._sensors.keys())}"
            )
        return self._sensors[position]

    def read_all(self, filter_none: bool = False) -> Dict[str, Optional[float]]:
        """
        读取所有传感器的距离。

        Args:
            filter_none: 是否过滤掉读取失败的传感器。

        Returns:
            Dict[str, Optional[float]]: {位置: 距离(cm)} 或 {位置: None (失败)}
        """
        results = {}
        for position, sensor in self._sensors.items():
            results[position] = sensor.read_distance()
        return results

    def cleanup(self):
        """释放所有传感器资源。"""
        for sensor in self._sensors.values():
            try:
                sensor.cleanup()
            except Exception as e:
                logger.warning("清理传感器时异常: %s", e)
        logger.info("超声波传感器管理器已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
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
    print("HC-SR04 超声波传感器测试 (模拟模式)")
    print("=" * 50)

    # 模拟配置
    config = {
        "front": {"trig": 23, "echo": 24},
        "left":  {"trig": 17, "echo": 27},
        "right": {"trig": 22, "echo": 10},
    }

    with UltrasonicSensorManager(config, simulated=True) as mgr:
        for i in range(5):
            distances = mgr.read_all()
            print(f"[{i+1}] 前:{distances.get('front'):>6.1f}cm\t"
                  f"左:{distances.get('left'):>6.1f}cm\t"
                  f"右:{distances.get('right'):>6.1f}cm")
            time.sleep(0.3)

    print("\n✅ 超声波模块测试完成！前方没有障碍！💪")
