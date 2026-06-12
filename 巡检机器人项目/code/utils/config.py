"""
配置文件管理模块。

支持 YAML / JSON 格式的配置文件。
自动加载巡检路线、传感器参数、报警阈值、通信设置等。

配置文件结构示例（config.yaml）:
--------------------------------------------------------------------------------
robot:
  name: "巡警一号"
  version: "1.0.0"

sensors:
  ir_temp:
    i2c_bus: 1
    address: 0x5A
  ultrasonic:
    front:  { trig: 23, echo: 24 }
    left:   { trig: 17, echo: 27 }
    right:  { trig: 22, echo: 10 }

inspection:
  loop_interval: 5           # 每个站点停留检测时间 (秒)
  move_speed: 0.3            # 移动速度 (m/s)
  auto_charge_threshold: 20  # 电量低于此百分比自动回充

alarm:
  temp_max: 60.0             # 温度上限 (℃)
  temp_min: -10.0            # 温度下限 (℃)
  distance_min: 15.0         # 最小安全距离 (cm)
  buzzer_pin: 18             # 蜂鸣器GPIO引脚

route:
  waypoints:
    - { x: 0.0,  y: 0.0,  actions: ["photo", "temp", "distance"] }
    - { x: 2.0,  y: 1.5,  actions: ["photo", "temp"] }
    - { x: 4.0,  y: 3.0,  actions: ["photo", "distance"] }
    - { x: 6.0,  y: 4.5,  actions: ["temp", "distance"] }

logging:
  level: "INFO"
  file: "/var/log/patroller.log"

communication:
  mqtt:
    enabled: false
    broker: "localhost"
    port: 1883
    topic_prefix: "factory/patrol"
  websocket:
    enabled: false
    host: "0.0.0.0"
    port: 8765

Author: 超人强 💪
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置文件内容（内嵌，无外部文件时可用）
DEFAULT_CONFIG: Dict[str, Any] = {
    "robot": {
        "name": "巡警一号",
        "version": "1.0.0",
    },
    "sensors": {
        "ir_temp": {
            "i2c_bus": 1,
            "address": 0x5A,
        },
        "ultrasonic": {
            "front": {"trig": 23, "echo": 24},
            "left": {"trig": 17, "echo": 27},
            "right": {"trig": 22, "echo": 10},
        },
    },
    "inspection": {
        "loop_interval": 5,
        "move_speed": 0.3,
        "auto_charge_threshold": 20,
    },
    "alarm": {
        "temp_max": 60.0,
        "temp_min": -10.0,
        "distance_min": 15.0,
        "buzzer_pin": 18,
    },
    "route": {
        "waypoints": [
            {"x": 0.0, "y": 0.0, "actions": ["photo", "temp", "distance"]},
            {"x": 2.0, "y": 1.5, "actions": ["photo", "temp"]},
            {"x": 4.0, "y": 3.0, "actions": ["photo", "distance"]},
            {"x": 6.0, "y": 4.5, "actions": ["temp", "distance"]},
        ],
    },
    "logging": {
        "level": "INFO",
        "file": "/var/log/patroller.log",
    },
    "communication": {
        "mqtt": {
            "enabled": False,
            "broker": "localhost",
            "port": 1883,
            "topic_prefix": "factory/patrol",
        },
        "websocket": {
            "enabled": False,
            "host": "0.0.0.0",
            "port": 8765,
        },
    },
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件，支持 YAML 和 JSON 格式。

    加载顺序:
        1. 指定的 config_path
        2. 环境变量 PATROLLER_CONFIG
        3. 当前目录下的 config.yaml / config.json
        4. 如均不可用，返回默认配置

    Args:
        config_path: 配置文件路径。如果为 None，自动搜索。

    Returns:
        Dict[str, Any]: 配置字典。

    Raises:
        ValueError: 配置文件格式不支持。
    """
    # 确定配置路径
    if config_path is None:
        config_path = os.environ.get("PATROLLER_CONFIG", "")
        if not config_path:
            # 在当前目录下搜索
            for candidate in ["config.yaml", "config.yml", "config.json"]:
                if Path(candidate).exists():
                    config_path = candidate
                    break

    if config_path and Path(config_path).exists():
        logger.info("加载配置文件: %s", config_path)
        ext = Path(config_path).suffix.lower()
        with open(config_path, "r", encoding="utf-8") as f:
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                    config = yaml.safe_load(f)
                except ImportError:
                    logger.warning("PyYAML 未安装，尝试 JSON 解析")
                    config = json.load(f)
            elif ext == ".json":
                config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {ext}")

        if config is None:
            config = {}

        # 合并默认配置，确保所有必要键都存在
        return _merge_config(DEFAULT_CONFIG, config)

    logger.info("未找到外部配置文件，使用默认配置")
    return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any], config_path: str):
    """
    保存配置到文件。

    Args:
        config: 配置字典。
        config_path: 保存路径。扩展名决定格式 (.yaml / .json)。
    """
    ext = Path(config_path).suffix.lower()
    with open(config_path, "w", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            try:
                import yaml
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                logger.warning("PyYAML 未安装，使用 JSON 格式保存")
                json.dump(config, f, ensure_ascii=False, indent=2)
        else:
            json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info("配置已保存到: %s", config_path)


def _merge_config(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归合并两个配置字典。override 的键会覆盖 default 的同名键。

    Args:
        defaults: 基准配置。
        overrides: 覆盖配置。

    Returns:
        Dict[str, Any]: 合并后的配置。
    """
    merged = {}
    for key in set(defaults.keys()) | set(overrides.keys()):
        if key in defaults and key in overrides:
            if isinstance(defaults[key], dict) and isinstance(overrides[key], dict):
                merged[key] = _merge_config(defaults[key], overrides[key])
            else:
                merged[key] = overrides[key]
        elif key in defaults:
            merged[key] = defaults[key]
        else:
            merged[key] = overrides[key]
    return merged


def get_config_value(
    config: Dict[str, Any],
    key_path: str,
    default: Any = None,
) -> Any:
    """
    使用点分隔路径获取嵌套配置值。

    Args:
        config: 配置字典。
        key_path: 点分隔的键路径，如 "sensors.ir_temp.address"。
        default: 键不存在时返回的默认值。

    Returns:
        Any: 配置值或默认值。
    """
    keys = key_path.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def setup_logging(config: Dict[str, Any]):
    """
    根据配置设置日志系统。

    Args:
        config: 完整配置字典，需包含 "logging" 段。
    """
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_file = log_config.get("file")

    handlers = [logging.StreamHandler()]
    if log_file:
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except (OSError, PermissionError) as e:
            logger.warning("无法创建日志文件 %s: %s", log_file, e)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
    logger.info("日志系统初始化完成 (level=%s)", log_config.get("level", "INFO"))


# ==================================================================
# 测试代码
# ==================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 50)
    print("配置管理模块测试")
    print("=" * 50)

    # 1. 加载默认配置
    cfg = load_config()
    print(f"机器人名称: {cfg['robot']['name']}")
    print(f"版本: {cfg['robot']['version']}")
    print(f"站点数量: {len(cfg['route']['waypoints'])}")
    print(f"温度上限: {cfg['alarm']['temp_max']}℃")
    print(f"最小安全距离: {cfg['alarm']['distance_min']}cm")
    print(f"蜂鸣器引脚: GPIO {cfg['alarm']['buzzer_pin']}")

    # 2. 测试 get_config_value
    addr = get_config_value(cfg, "sensors.ir_temp.address")
    print(f"MLX90614 地址: 0x{addr:02X}")

    # 3. 测试写入再读取
    test_path = "/tmp/test_patroller_config.json"
    save_config(cfg, test_path)
    cfg2 = load_config(test_path)
    print(f"重载配置后站点数: {len(cfg2['route']['waypoints'])}")
    os.remove(test_path)

    print("\n✅ 配置管理模块一切正常！💪")
