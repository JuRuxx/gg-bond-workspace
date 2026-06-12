"""
巡检路线管理模块。

定义巡检路线关键点 (Waypoint) 和路线 (Route)。
每个关键点可配置：x/y坐标、检测动作集（拍照/测温/测距）。

Author: 超人强 💪
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Waypoint:
    """
    巡检路线关键点。

    Attributes:
        name: 站点名称 (可选)。
        x: 坐标 X (米)。
        y: 坐标 Y (米)。
        actions: 此站点要执行的检测动作列表。
            支持: "photo" (拍照), "temp" (测温), "distance" (测距)。
        tolerance: 到达判定容差 (米)。距离小于此值视为"到达"。
        extra: 附加配置 (如拍摄角度、检测参数等)。
    """

    x: float
    y: float
    name: Optional[str] = None
    actions: List[str] = field(default_factory=lambda: ["photo", "temp", "distance"])
    tolerance: float = 0.3
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Waypoint":
        """从字典创建。"""
        return cls(**data)

    def __repr__(self) -> str:
        name_str = f"({self.name})" if self.name else ""
        actions_str = "+".join(self.actions)
        return f"Waypoint{name_str}[{self.x:.1f},{self.y:.1f}]/{actions_str}"


class Route:
    """
    巡检路线。由一组有序的关键点组成。

    Args:
        waypoints: 关键点列表。
        name: 路线名称。
        loop: 是否循环巡检（到达最后一个点后回到第一个）。
    """

    def __init__(
        self,
        waypoints: Optional[List[Waypoint]] = None,
        name: str = "default_route",
        loop: bool = True,
    ):
        self.name = name
        self.loop = loop
        self._waypoints: List[Waypoint] = waypoints or []
        self._current_index: int = 0

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "Route":
        """
        从配置字典创建路线。

        Args:
            config: 配置中 "route" 段。
                {
                    "waypoints": [{"x": 0, "y": 0, "actions": [...], ...}, ...],
                    ...
                }

        Returns:
            Route 实例。
        """
        waypoints_data = config.get("waypoints", [])
        waypoints = [Waypoint.from_dict(wp) for wp in waypoints_data]
        return cls(
            waypoints=waypoints,
            name=config.get("name", "config_route"),
            loop=config.get("loop", True),
        )

    # ------------------------------------------------------------------
    # 路线遍历
    # ------------------------------------------------------------------

    @property
    def total_points(self) -> int:
        """获取总关键点数量。"""
        return len(self._waypoints)

    @property
    def current_index(self) -> int:
        """获取当前关键点索引。"""
        return self._current_index

    def current(self) -> Optional[Waypoint]:
        """
        获取当前关键点。

        Returns:
            Optional[Waypoint]: 当前关键点，路线为空时返回 None。
        """
        if not self._waypoints:
            return None
        return self._waypoints[self._current_index]

    def next(self) -> Optional[Waypoint]:
        """
        移动到下一个关键点。如果路线已循环，回到第一个。

        Returns:
            Optional[Waypoint]: 下一个关键点，路线为空时返回 None。
        """
        if not self._waypoints:
            return None

        if self._current_index + 1 < len(self._waypoints):
            self._current_index += 1
        elif self.loop:
            self._current_index = 0
        else:
            return None

        return self.current()

    def reset(self):
        """重置到第一个关键点。"""
        self._current_index = 0

    def is_last_point(self) -> bool:
        """当前是否在最后一个关键点。"""
        return self._current_index == len(self._waypoints) - 1

    def is_first_point(self) -> bool:
        """当前是否在第一个关键点。"""
        return self._current_index == 0

    def get_waypoints(self) -> List[Waypoint]:
        """获取所有关键点列表（副本，非引用）。"""
        return list(self._waypoints)

    def add_waypoint(self, waypoint: Waypoint, index: Optional[int] = None):
        """
        添加关键点。

        Args:
            waypoint: 要添加的关键点。
            index: 插入位置。None 表示追加到末尾。
        """
        if index is None:
            self._waypoints.append(waypoint)
        else:
            self._waypoints.insert(index, waypoint)

    def remove_waypoint(self, index: int) -> Optional[Waypoint]:
        """
        移除指定索引的关键点。

        Args:
            index: 要移除的关键点索引。

        Returns:
            Optional[Waypoint]: 被移除的关键点，索引无效时返回 None。
        """
        if 0 <= index < len(self._waypoints):
            removed = self._waypoints.pop(index)
            if self._current_index >= len(self._waypoints):
                self._current_index = max(0, len(self._waypoints) - 1)
            return removed
        return None

    # ------------------------------------------------------------------
    # 距离与导航
    # ------------------------------------------------------------------

    def distance_to_current(self, x: float, y: float) -> float:
        """
        计算当前位置到当前关键点的距离。

        Args:
            x: 当前 X 坐标。
            y: 当前 Y 坐标。

        Returns:
            float: 欧几里得距离 (米)。
        """
        wp = self.current()
        if wp is None:
            return float("inf")
        return ((x - wp.x) ** 2 + (y - wp.y) ** 2) ** 0.5

    def is_at_current(self, x: float, y: float) -> bool:
        """
        判断当前是否已到达当前关键点。

        Args:
            x: 当前 X 坐标。
            y: 当前 Y 坐标。

        Returns:
            bool: 是否在容差范围内。
        """
        wp = self.current()
        if wp is None:
            return False
        return self.distance_to_current(x, y) <= wp.tolerance

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典。"""
        return {
            "name": self.name,
            "loop": self.loop,
            "waypoints": [wp.to_dict() for wp in self._waypoints],
        }

    def __len__(self) -> int:
        return len(self._waypoints)

    def __repr__(self) -> str:
        return f"Route[{self.name}] {self._current_index}/{len(self._waypoints)} wp"


# ==================================================================
# 测试代码
# ==================================================================
if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    print("=" * 50)
    print("巡检路线管理模块测试")
    print("=" * 50)

    # 创建路线
    route = Route(
        name="产线A",
        waypoints=[
            Waypoint(0.0, 0.0, "起点", ["photo", "temp"]),
            Waypoint(2.0, 1.5, "工位1", ["photo", "temp", "distance"]),
            Waypoint(4.0, 3.0, "工位2", ["temp", "distance"]),
            Waypoint(6.0, 4.5, "终点", ["photo"]),
        ],
        loop=True,
    )

    print(f"\n路线: {route.name}")
    print(f"站点数: {route.total_points}")

    # 模拟巡检
    print("\n模拟巡检:")
    current_pos = [0.0, 0.0]
    for step in range(8):  # 走两圈
        wp = route.current()
        print(f"  [步骤 {step+1}] → {wp}")

        # 模拟移动
        dist = route.distance_to_current(current_pos[0], current_pos[1])
        print(f"    距离: {dist:.2f}m")

        # 模拟到达
        if route.is_at_current(current_pos[0], current_pos[1]):
            print(f"    ✅ 到达！执行: {wp.actions}")
            route.next()

        # 模拟前进
        if wp and wp.x > current_pos[0]:
            current_pos[0] += 0.5
        if wp and wp.y > current_pos[1]:
            current_pos[1] += 0.3

        time.sleep(0.1)

    print(f"\n最终位置: ({current_pos[0]:.1f}, {current_pos[1]:.1f})")
    print(f"当前索引: {route.current_index} / {route.total_points}")

    print("\n✅ 路线模块一切正常！出发！🚀💪")
