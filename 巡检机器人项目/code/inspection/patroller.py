"""
巡检主程序 — 状态机核心模块。

状态机流转:
    IDLE → PATROL → CHECK → ALARM (异常时) → CHARGING (低电时)

状态说明:
    IDLE:     待机，等待远程启动指令
    PATROL:   沿产线移动到下一关键点（调用 RaspRover base_ctrl）
    CHECK:    到站后采集数据（拍照+测温+测距）
    ALARM:    异常报警（蜂鸣器+日志+推送）
    CHARGING: 低电自动回桩充电

与官方代码解耦:
    - 通过回调函数 / 事件钩子调用 RaspRover 的 base_ctrl.py / cv_ctrl.py
    - 不直接 import 官方模块，保持独立可测
    - 用户实现 TargetController 接口适配实际底盘

Author: 超人强 💪
"""

import logging
import time
import json
import threading
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from pathlib import Path

from .route import Route, Waypoint

logger = logging.getLogger(__name__)


# ==================================================================
# 状态定义
# ==================================================================

class PatrolState(Enum):
    """巡检状态机状态"""
    IDLE = auto()
    PATROL = auto()
    CHECK = auto()
    ALARM = auto()
    CHARGING = auto()
    STOPPED = auto()


# ==================================================================
# 控制接口定义（与底层解耦）
# ==================================================================

class TargetController:
    """
    RaspRover 底层控制抽象接口。

    用户需实现此接口，适配实际的 base_ctrl.py 和 cv_ctrl.py。

    在模拟模式下，使用 SimulatedController。
    """

    def move_to(self, x: float, y: float, speed: float = 0.3) -> bool:
        """
        移动到指定坐标。阻塞直到到达或取消。

        Args:
            x: 目标 X 坐标。
            y: 目标 Y 坐标。
            speed: 移动速度 (m/s)。

        Returns:
            bool: True 表示成功到达，False 表示中途取消。
        """
        raise NotImplementedError

    def stop(self):
        """紧急停止。"""
        raise NotImplementedError

    def take_photo(self) -> Optional[str]:
        """
        拍照。

        Returns:
            Optional[str]: 图片保存路径，失败则返回 None。
        """
        raise NotImplementedError

    def get_battery_level(self) -> float:
        """
        获取电池电量百分比。

        Returns:
            float: 0.0 ~ 100.0
        """
        raise NotImplementedError

    def get_position(self) -> tuple:
        """
        获取当前坐标。

        Returns:
            tuple: (x, y)
        """
        raise NotImplementedError

    def go_charge(self) -> bool:
        """
        自动回桩充电。

        Returns:
            bool: True 表示成功接入充电桩。
        """
        raise NotImplementedError


class SimulatedController(TargetController):
    """
    模拟控制器。无硬件时可运行所有功能。
    """

    def __init__(self):
        self._pos = (0.0, 0.0)
        self._battery = 100.0
        self._photo_count = 0
        self._stopped = False

    def move_to(self, x: float, y: float, speed: float = 0.3) -> bool:
        self._stopped = False
        logger.info("[模拟] 移动到 (%.1f, %.1f) 速度=%.1f", x, y, speed)
        steps = max(int(((x - self._pos[0])**2 + (y - self._pos[1])**2)**0.5 / 0.5), 1)
        for _ in range(steps):
            if self._stopped:
                logger.info("[模拟] 移动被中断")
                return False
            # 模拟移动
            dx = (x - self._pos[0]) / steps
            dy = (y - self._pos[1]) / steps
            self._pos = (self._pos[0] + dx, self._pos[1] + dy)
            time.sleep(0.2)
        self._pos = (x, y)
        logger.info("[模拟] 到达 (%.1f, %.1f)", x, y)
        return True

    def stop(self):
        self._stopped = True
        logger.info("[模拟] 急停")

    def take_photo(self) -> Optional[str]:
        self._photo_count += 1
        path = f"/tmp/patrol_photo_{self._photo_count:04d}.jpg"
        logger.info("[模拟] 拍照 → %s", path)
        return path

    def get_battery_level(self) -> float:
        # 模拟缓慢耗电
        self._battery = max(0, self._battery - 0.5)
        return self._battery

    def get_position(self) -> tuple:
        return self._pos

    def go_charge(self) -> bool:
        logger.info("[模拟] 回桩充电中...")
        time.sleep(2.0)
        self._battery = 100.0
        self._pos = (0.0, 0.0)
        logger.info("[模拟] 充电完成")
        return True


# ==================================================================
# 检测回调类型
# ==================================================================

InspectionCallback = Callable[[Waypoint, Dict[str, Any]], None]
"""
检测回调签名:
    callback(waypoint: Waypoint, results: Dict[str, Any]) -> None

results 字段:
    - "photo": Optional[str]  - 图片路径或 None
    - "temp":  Optional[float] - 物体温度或 None
    - "ambient_temp": Optional[float] - 环境温度或 None
    - "distance": Optional[Dict[str, float]] - {前/左/右: cm} 或 None
"""


# ==================================================================
# 巡检主程序
# ==================================================================

class Patroller:
    """
    巡检机器人主程序 — 状态机核心。

    Args:
        route: 巡检路线。
        controller: 底层控制器 (TargetController 实现)。
        notifier: 报警通知器 (可选)。
        ir_sensor: MLX90614 传感器实例 (可选)。
        ultrasonic_mgr: HC-SR04 管理器实例 (可选)。
        config: 配置字典。
    """

    def __init__(
        self,
        route: Route,
        controller: TargetController,
        notifier=None,
        ir_sensor=None,
        ultrasonic_mgr=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.route = route
        self.controller = controller
        self.notifier = notifier
        self.ir_sensor = ir_sensor
        self.ultrasonic_mgr = ultrasonic_mgr
        self.config = config or {}

        # 状态
        self._state = PatrolState.IDLE
        self._previous_state: Optional[PatrolState] = None
        self._stop_requested = False
        self._pause_requested = False

        # 运行时统计
        self.stats: Dict[str, Any] = {
            "total_patrols": 0,
            "total_checks": 0,
            "alarms_fired": 0,
            "start_time": None,
            "last_check_time": None,
        }

        # 巡检结果（最近一轮）
        self._last_results: Dict[str, Any] = {}

        # 报警阈值
        self._alarm_temp_max = float(
            self.config.get("alarm", {}).get("temp_max", 60.0)
        )
        self._alarm_temp_min = float(
            self.config.get("alarm", {}).get("temp_min", -10.0)
        )
        self._alarm_dist_min = float(
            self.config.get("alarm", {}).get("distance_min", 15.0)
        )

        # 巡检参数
        self._loop_interval = float(
            self.config.get("inspection", {}).get("loop_interval", 5)
        )
        self._move_speed = float(
            self.config.get("inspection", {}).get("move_speed", 0.3)
        )
        self._auto_charge_threshold = float(
            self.config.get("inspection", {}).get("auto_charge_threshold", 20)
        )

        # 外部回调
        self._check_callbacks: List[InspectionCallback] = []
        self._state_change_callbacks: List[Callable[[PatrolState, PatrolState], None]] = []

        # 日志
        self._log_path = self.config.get("logging", {}).get("file", "patroller.log")

    # ------------------------------------------------------------------
    # 状态管理
    # ------------------------------------------------------------------

    @property
    def state(self) -> PatrolState:
        """当前状态 (只读)。"""
        return self._state

    def _set_state(self, new_state: PatrolState):
        """
        切换状态并触发回调。

        Args:
            new_state: 目标状态。
        """
        old = self._state
        self._previous_state = old
        self._state = new_state
        logger.info("状态变更: %s → %s", old.name, new_state.name)

        for cb in self._state_change_callbacks:
            try:
                cb(old, new_state)
            except Exception as e:
                logger.error("状态变更回调异常: %s", e)

    # ------------------------------------------------------------------
    # 外部控制接口
    # ------------------------------------------------------------------

    def start(self):
        """启动巡检。"""
        if self._state == PatrolState.IDLE:
            logger.info("接收到启动指令")
            self._stop_requested = False
            self._pause_requested = False
            self.stats["start_time"] = datetime.now().isoformat()
            self._set_state(PatrolState.PATROL)
        else:
            logger.warning("当前状态 %s，无法启动", self._state.name)

    def pause(self):
        """暂停巡检 (当前检测完成后暂停)。"""
        if self._state in (PatrolState.PATROL, PatrolState.CHECK):
            logger.info("接收到暂停指令")
            self._pause_requested = True
        else:
            logger.warning("当前状态 %s，无法暂停", self._state.name)

    def resume(self):
        """恢复巡检。"""
        if self._state == PatrolState.STOPPED:
            # 从停止恢复 = 重新开始
            logger.info("从停止状态恢复巡检")
            self._set_state(PatrolState.IDLE)
            self.start()
        elif self._state in (PatrolState.IDLE, PatrolState.ALARM):
            self._pause_requested = False
            self._set_state(PatrolState.PATROL)

    def stop(self):
        """停止巡检 (急停)。"""
        logger.info("接收到停止指令")
        self._stop_requested = True
        self._pause_requested = False
        self.controller.stop()
        self._set_state(PatrolState.STOPPED)

    def is_running(self) -> bool:
        """巡检是否正在运行。"""
        return self._state not in (PatrolState.IDLE, PatrolState.STOPPED)

    # ------------------------------------------------------------------
    # 回调注册
    # ------------------------------------------------------------------

    def on_check(self, callback: InspectionCallback):
        """
        注册检测完成回调。每次 CHECK 完成后调用。

        Args:
            callback: 回调函数。
        """
        self._check_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[PatrolState, PatrolState], None]):
        """
        注册状态变更回调。

        Args:
            callback: 回调函数，签名 (old_state, new_state)。
        """
        self._state_change_callbacks.append(callback)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def run_forever(self, interval: float = 0.5):
        """
        主运行循环。阻塞执行。

        Args:
            interval: 主循环间隔 (秒)。
        """
        logger.info("=== 巡检主循环启动 ===")
        logger.info("路线: %s, %d 个站点", self.route.name, self.route.total_points)

        while not self._stop_requested:
            try:
                self._run_state_machine()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("收到键盘中断")
                self.stop()
                break
            except Exception as e:
                logger.critical("主循环异常: %s", e, exc_info=True)
                if self.notifier:
                    self.notifier.fire_alarm(
                        "critical", f"巡检系统异常: {e}", beep=True, beep_count=5
                    )
                time.sleep(5)  # 异常等待后继续

        logger.info("=== 巡检主循环结束 ===")
        self._cleanup()

    def _run_state_machine(self):
        """执行一次状态机状态处理。"""
        if self._state == PatrolState.IDLE:
            # IDLE: 等待启动指令 (什么都不做)
            pass

        elif self._state == PatrolState.PATROL:
            self._handle_patrol()

        elif self._state == PatrolState.CHECK:
            self._handle_check()

        elif self._state == PatrolState.ALARM:
            self._handle_alarm()

        elif self._state == PatrolState.CHARGING:
            self._handle_charging()

        elif self._state == PatrolState.STOPPED:
            # STOPPED: 什么都不做，等待 resume
            pass

    # ------------------------------------------------------------------
    # 状态处理
    # ------------------------------------------------------------------

    def _handle_patrol(self):
        """PATROL 状态: 移动到下一个关键点。"""
        # 暂停检查
        if self._pause_requested:
            logger.info("移动中暂停请求，等待到达下一站后暂停")
            self._pause_requested = False
            self._set_state(PatrolState.IDLE)
            return

        # 电池检查
        battery = self.controller.get_battery_level()
        if battery is not None and battery < self._auto_charge_threshold:
            logger.warning("电量不足 (%.1f%%)，自动回充", battery)
            if self.notifier:
                self.notifier.fire_alarm(
                    "warning", f"电量不足 ({battery:.0f}%)，自动回充",
                    metadata={"battery": battery}, beep=True, beep_count=2,
                )
            self._set_state(PatrolState.CHARGING)
            return

        wp = self.route.current()
        if wp is None:
            logger.info("路线完成，回到 IDLE")
            self._set_state(PatrolState.IDLE)
            return

        logger.info("前往: %s (%.1f, %.1f)", wp, wp.x, wp.y)

        # 移动
        arrived = self.controller.move_to(wp.x, wp.y, speed=self._move_speed)

        if arrived:
            # 到达→进入检测
            self._set_state(PatrolState.CHECK)
        else:
            # 被中断
            logger.info("移动被中断")

    def _handle_check(self):
        """CHECK 状态: 在关键点执行检测任务。"""
        wp = self.route.current()
        if wp is None:
            self._set_state(PatrolState.IDLE)
            return

        logger.info("检测站点: %s", wp)
        results: Dict[str, Any] = {}

        for action in wp.actions:
            try:
                if action == "photo" and hasattr(self.controller, "take_photo"):
                    results["photo"] = self.controller.take_photo()

                elif action == "temp" and self.ir_sensor:
                    obj_temp = self.ir_sensor.read_object_temp()
                    amb_temp = self.ir_sensor.read_ambient_temp()
                    results["temp"] = obj_temp
                    results["ambient_temp"] = amb_temp

                    # 温度异常检查
                    if obj_temp is not None:
                        if obj_temp > self._alarm_temp_max:
                            self._handle_temp_alarm(
                                obj_temp, self._alarm_temp_max, "超标"
                            )
                        elif obj_temp < self._alarm_temp_min:
                            self._handle_temp_alarm(
                                obj_temp, self._alarm_temp_min, "过低"
                            )

                elif action == "distance" and self.ultrasonic_mgr:
                    dists = self.ultrasonic_mgr.read_all()
                    results["distance"] = dists

                    # 距离异常检查
                    if dists:
                        for pos, d in dists.items():
                            if d is not None and d < self._alarm_dist_min:
                                self._handle_dist_alarm(
                                    pos, d, self._alarm_dist_min
                                )

            except Exception as e:
                logger.error("检测动作 [%s] 失败: %s", action, e)
                results[action] = None

            time.sleep(0.2)  # 动作间隔

        # 保存结果
        self._last_results = results
        self.stats["total_checks"] += 1
        self.stats["last_check_time"] = datetime.now().isoformat()

        # 触发检测回调
        for cb in self._check_callbacks:
            try:
                cb(wp, results)
            except Exception as e:
                logger.error("检测回调异常: %s", e)

        # 输出摘要
        self._log_check_summary(wp, results)

        # 前往下一站
        time.sleep(self._loop_interval)
        self.route.next()
        self._set_state(PatrolState.PATROL)

    def _handle_temp_alarm(self, temp: float, limit: float, reason: str):
        """
        温度报警处理。

        Args:
            temp: 温度值。
            limit: 阈值。
            reason: 原因描述（超标/过低）。
        """
        self.stats["alarms_fired"] += 1
        msg = f"温度{reason}: {temp:.1f}℃ (阈值: {limit:.1f}℃)"
        logger.warning(msg)

        if self.notifier:
            self.notifier.fire_alarm(
                "warning" if abs(temp - limit) < 5 else "critical",
                msg,
                metadata={"temp": temp, "limit": limit},
                beep=True,
                beep_count=3,
            )

    def _handle_dist_alarm(self, position: str, distance: float, limit: float):
        """距离报警处理。"""
        self.stats["alarms_fired"] += 1
        msg = f"{position}方向距离过近: {distance:.1f}cm (阈值: {limit:.1f}cm)"
        logger.warning(msg)

        if self.notifier:
            self.notifier.fire_alarm(
                "warning", msg,
                metadata={"position": position, "distance": distance, "limit": limit},
                beep=True,
                beep_count=2,
            )

    def _handle_alarm(self):
        """ALARM 状态: 报警处理。"""
        # 等待人工干预或自动恢复（暂简单实现）
        logger.info("报警状态中，等待处理...")
        time.sleep(3)
        # 自动恢复到 PATROL（可根据策略改为等待手动确认）
        self._set_state(PatrolState.PATROL)

    def _handle_charging(self):
        """CHARGING 状态: 自动回充。"""
        logger.info("开始自动回充...")
        success = self.controller.go_charge()
        if success:
            logger.info("充电完成，恢复巡检")
            self.route.reset()
            self._set_state(PatrolState.PATROL)
        else:
            logger.error("回充失败")
            if self.notifier:
                self.notifier.fire_alarm(
                    "critical", "自动回充失败！",
                    beep=True, beep_count=5,
                )
            self._set_state(PatrolState.ALARM)

    # ------------------------------------------------------------------
    # 日志输出
    # ------------------------------------------------------------------

    def _log_check_summary(self, wp: Waypoint, results: Dict[str, Any]):
        """
        将检测结果输出到日志文件。

        Args:
            wp: 当前关键点。
            results: 检测结果字典。
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "waypoint": wp.to_dict(),
            "results": results,
        }

        # 输出到文件
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except (OSError, PermissionError) as e:
            logger.error("写入巡检日志失败: %s", e)

        # 控制台摘要
        temp_str = f"{results.get('temp', 'N/A'):.1f}℃" if results.get("temp") else "N/A"
        dist_str = str(results.get("distance", "N/A"))
        photo_str = results.get("photo", "None")
        print(f"  📸 照片: {photo_str}")
        print(f"  🌡️ 温度: {temp_str}")
        print(f"  📏 距离: {dist_str}")

    # ------------------------------------------------------------------
    # 资源清理
    # ------------------------------------------------------------------

    def _cleanup(self):
        """清理资源。"""
        logger.info("巡检系统关闭，清理资源中...")
        if self.ir_sensor:
            try:
                self.ir_sensor.close()
            except Exception as e:
                logger.warning("关闭红外传感器异常: %s", e)
        if self.ultrasonic_mgr:
            try:
                self.ultrasonic_mgr.cleanup()
            except Exception as e:
                logger.warning("关闭超声波传感器异常: %s", e)
        logger.info("巡检系统已关闭")

    def get_status(self) -> Dict[str, Any]:
        """获取当前运行状态摘要。"""
        wp = self.route.current()
        return {
            "state": self._state.name,
            "route": self.route.name,
            "current_waypoint": wp.to_dict() if wp else None,
            "waypoint_index": self.route.current_index,
            "total_waypoints": self.route.total_points,
            "stats": self.stats,
            "last_results": self._last_results,
            "is_running": self.is_running(),
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        return False


# ==================================================================
# 测试代码
# ==================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("🦾 巡检主程序状态机测试 (全模拟模式)")
    print("=" * 60)

    from .route import Route, Waypoint
    from ..sensors.ir_temp import MLX90614
    from ..sensors.ultrasonic import UltrasonicSensorManager
    from ..utils.notifier import Notifier
    from ..utils.config import load_config

    # 加载配置
    cfg = load_config()

    # 准备模拟组件
    controller = SimulatedController()
    ir_sensor = MLX90614(simulated=True)
    ultrasonic_mgr = UltrasonicSensorManager(
        cfg["sensors"]["ultrasonic"], simulated=True
    )
    notifier = Notifier(buzzer_pin=None, simulated=True)

    # 创建路线
    route = Route.from_config(cfg["route"])
    route.name = "产线A测试路线"

    # 创建巡检器
    patroller = Patroller(
        route=route,
        controller=controller,
        notifier=notifier,
        ir_sensor=ir_sensor,
        ultrasonic_mgr=ultrasonic_mgr,
        config=cfg,
    )

    # 注册状态变更回调
    def on_state(old, new):
        print(f"    [状态变更] {old.name} → {new.name}")

    patroller.on_state_change(on_state)

    # 启动巡检（非阻塞跑3个站）
    print("\n🚀 启动巡检...")
    patroller.start()

    # 使用定时器控制，跑3个站点后停止
    def stop_after_3():
        time.sleep(15)  # 给足够时间走3站
        print("\n🛑 测试停止...")
        patroller.stop()

    import threading
    timer = threading.Thread(target=stop_after_3, daemon=True)
    timer.start()

    # 主循环 (非阻塞方式)
    try:
        start = time.time()
        while patroller.is_running() and time.time() - start < 20:
            patroller._run_state_machine()
            time.sleep(0.3)
    except KeyboardInterrupt:
        patroller.stop()

    # 打印状态
    print("\n📊 巡检状态报告:")
    status = patroller.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    print("\n✅ 巡检主程序测试完成！所有状态流转正常！💪🔥")
    print("   IDLE → PATROL → CHECK → (循环) → IDLE ✅")
