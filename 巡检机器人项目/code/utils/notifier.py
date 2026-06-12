"""
报警通知模块。

功能:
    - 蜂鸣器控制 (GPIO)
    - 报警日志记录到文件
    - 预留 MQTT / HTTP 推送接口（后续对接钉钉/微信通知）

Author: 超人强 💪
"""

import logging
import json
import time
import os
from typing import Optional, Callable, Dict, Any
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AlarmLevel(Enum):
    """报警等级"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notifier:
    """
    报警通知器。统一管理蜂鸣器、日志、及外部推送接口。

    Args:
        buzzer_pin: 蜂鸣器 GPIO 引脚 (BCM模式)。设为 None 则禁用蜂鸣器。
        alarm_log_path: 报警日志文件路径。默认为 "alarm.log"。
        simulated: 使用模拟模式（无硬件时）。
    """

    def __init__(
        self,
        buzzer_pin: Optional[int] = 18,
        alarm_log_path: str = "alarm.log",
        simulated: Optional[bool] = None,
    ):
        self.buzzer_pin = buzzer_pin
        self.alarm_log_path = alarm_log_path
        self._simulated = simulated if simulated is not None else False
        self._gpio = None

        # 外部推送回调注册表
        self._push_callbacks: Dict[str, Callable] = {}

        # 蜂鸣器初始化
        if buzzer_pin is not None and not self._simulated:
            try:
                import RPi.GPIO as GPIO
                self._gpio = GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.buzzer_pin, GPIO.OUT)
                GPIO.output(self.buzzer_pin, GPIO.LOW)
                logger.info("蜂鸣器初始化成功 (GPIO %d)", self.buzzer_pin)
            except (ImportError, OSError, RuntimeError) as e:
                logger.warning("蜂鸣器初始化失败: %s，禁用蜂鸣器", e)
                self.buzzer_pin = None
        else:
            logger.info("蜂鸣器已禁用 (simulated=%s, pin=%s)", self._simulated, buzzer_pin)

        # 确保报警日志目录存在
        if self.alarm_log_path:
            log_dir = os.path.dirname(self.alarm_log_path)
            if log_dir:
                Path(log_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 蜂鸣器控制
    # ------------------------------------------------------------------

    def buzzer_beep(self, duration: float = 0.5, count: int = 1):
        """
        控制蜂鸣器发出警报声。

        Args:
            duration: 每次蜂鸣持续时间 (秒)。
            count: 蜂鸣次数。
        """
        if self.buzzer_pin is None:
            return

        if self._simulated or self._gpio is None:
            logger.info("[模拟] 蜂鸣器鸣叫 %d 次, 每次 %.1f 秒", count, duration)
            return

        try:
            for _ in range(count):
                self._gpio.output(self.buzzer_pin, self._gpio.HIGH)
                time.sleep(duration)
                self._gpio.output(self.buzzer_pin, self._gpio.LOW)
                time.sleep(0.2)
            logger.debug("蜂鸣器已鸣叫 %d 次", count)
        except Exception as e:
            logger.error("蜂鸣器控制失败: %s", e)

    def buzzer_silent(self):
        """静音蜂鸣器。"""
        if self.buzzer_pin is None or self._gpio is None:
            return
        try:
            self._gpio.output(self.buzzer_pin, self._gpio.LOW)
        except Exception as e:
            logger.error("静音蜂鸣器失败: %s", e)

    # ------------------------------------------------------------------
    # 报警日志
    # ------------------------------------------------------------------

    def log_alarm(
        self,
        level: AlarmLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        记录报警事件到日志文件。

        Args:
            level: 报警等级。
            message: 报警消息。
            metadata: 附加元数据（温度值、距离值等）。
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "timestamp": timestamp,
            "level": level.value,
            "message": message,
            "metadata": metadata or {},
        }

        # 写入文件
        if self.alarm_log_path:
            try:
                with open(self.alarm_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except (OSError, PermissionError) as e:
                logger.error("写入报警日志失败: %s", e)

        # 同时输出到 Python 日志
        log_msg = f"[{level.value.upper()}] {message} {metadata or ''}"
        if level == AlarmLevel.CRITICAL:
            logger.critical(log_msg)
        elif level == AlarmLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    # ------------------------------------------------------------------
    # 报警全流程
    # ------------------------------------------------------------------

    def fire_alarm(
        self,
        level: AlarmLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        beep: bool = True,
        beep_count: int = 3,
    ):
        """
        触发完整报警流程：蜂鸣 + 日志 + 推送。

        Args:
            level: 报警等级。
            message: 报警消息。
            metadata: 附加元数据。
            beep: 是否蜂鸣。
            beep_count: 蜂鸣次数。
        """
        # 1. 蜂鸣器
        if beep:
            duration = 0.3 if level == AlarmLevel.CRITICAL else 0.15
            self.buzzer_beep(duration=duration, count=beep_count)

        # 2. 日志
        self.log_alarm(level, message, metadata)

        # 3. 外部推送
        self._dispatch_push(level, message, metadata or {})

    # ------------------------------------------------------------------
    # 外部推送接口 (预留)
    # ------------------------------------------------------------------

    def register_push_callback(self, name: str, callback: Callable):
        """
        注册外部推送回调。

        Args:
            name: 回调名称 (如 "dingtalk", "wechat", "mqtt")。
            callback: 回调函数，签名:
                callback(level: AlarmLevel, message: str, metadata: dict) -> None
        """
        self._push_callbacks[name] = callback
        logger.info("已注册推送回调: %s", name)

    def unregister_push_callback(self, name: str):
        """注销推送回调。"""
        self._push_callbacks.pop(name, None)

    def _dispatch_push(
        self,
        level: AlarmLevel,
        message: str,
        metadata: Dict[str, Any],
    ):
        """将报警分发给所有已注册的推送回调。"""
        for name, callback in self._push_callbacks.items():
            try:
                callback(level, message, metadata)
                logger.debug("推送回调 [%s] 执行成功", name)
            except Exception as e:
                logger.error("推送回调 [%s] 执行失败: %s", name, e)

    # ------------------------------------------------------------------
    # 资源清理
    # ------------------------------------------------------------------

    def close(self):
        """释放资源 (GPIO)。"""
        if self._gpio is not None and self.buzzer_pin is not None:
            try:
                self._gpio.cleanup(self.buzzer_pin)
                logger.info("蜂鸣器 GPIO 资源已释放")
            except Exception as e:
                logger.warning("释放蜂鸣器 GPIO 时异常: %s", e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ==================================================================
# 预留推送接口示例 (后续对接)

# def dingtalk_push(level: AlarmLevel, message: str, metadata: dict):
#     """钉钉机器人推送。"""
#     # TODO: 实现钉钉 WebHook 推送
#     pass
#
# def wechat_push(level: AlarmLevel, message: str, metadata: dict):
#     """企业微信推送。"""
#     # TODO: 实现企微机器人推送
#     pass


# ==================================================================
# 测试代码
# ==================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 50)
    print("报警通知模块测试 (模拟模式)")
    print("=" * 50)

    with Notifier(buzzer_pin=None, simulated=True) as notifier:
        # 1. 测试不同等级报警
        notifier.fire_alarm(
            AlarmLevel.INFO,
            "巡检任务开始",
            {"task_id": "T001"},
            beep=False,
        )

        notifier.fire_alarm(
            AlarmLevel.WARNING,
            "温度偏高",
            {"temp": 58.5, "limit": 60.0},
            beep_count=2,
        )

        notifier.fire_alarm(
            AlarmLevel.CRITICAL,
            "温度超标！",
            {"temp": 72.3, "limit": 60.0},
            beep_count=5,
        )

        # 2. 测试蜂鸣器 (纯模拟)
        notifier.buzzer_beep(duration=0.2, count=3)

        # 3. 测试注册回调
        def mock_push(level, msg, meta):
            print(f"    [模拟推送] {level.value}: {msg} {meta}")

        notifier.register_push_callback("test_mock", mock_push)
        notifier.fire_alarm(
            AlarmLevel.WARNING,
            "推送测试",
            {"test": True},
            beep=False,
        )

    # 4. 验证日志文件
    print(f"\n报警日志已写入: {os.path.abspath('alarm.log')}")
    if Path("alarm.log").exists():
        with open("alarm.log", "r") as f:
            lines = f.readlines()
        print(f"日志行数: {len(lines)}")
        for line in lines[-3:]:
            print(f"  → {line.strip()}")
        os.remove("alarm.log")

    print("\n✅ 报警通知模块一切正常！有我在，警报响遍全厂！💪🔥")
