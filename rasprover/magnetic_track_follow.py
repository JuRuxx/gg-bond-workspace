#!/usr/bin/env python3
# 🧲 RaspRover 磁轨循迹 🐷
# 用法：在树莓派终端运行：python3 magnetic_track_follow.py
# 磁传感器探测地上磁条，自动沿着磁条走！
# 按 Q 退出

import json
import time
import serial
import sys
import RPi.GPIO as GPIO

# ═══════════════════════════════════
#  硬件配置
# ═══════════════════════════════════

# 磁传感器接线（3路探头）
# 探头装在RaspRover底部前方，间距约2cm
#   左探针  →  GPIO17   探测磁条偏左
#   中探针  →  GPIO27   探测磁条正中
#   右探针  →  GPIO22   探测磁条偏右
PIN_LEFT  = 17
PIN_CENTER = 27
PIN_RIGHT = 22

# 小车串口
SERIAL_PORT = '/dev/ttyAMA0'  # RPi5
try:
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")
except:
    SERIAL_PORT = '/dev/serial0'  # RPi4B
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")

# ─── 控制参数 ───
BASE_SPEED = 40       # 基础行进速度（0-100）
TURN_SPEED = 35       # 转弯差速幅度
LOST_TIMEOUT = 3      # 丢失磁条后多少秒停车

# ═══════════════════════════════════
#  初始化
# ═══════════════════════════════════

GPIO.setmode(GPIO.BCM)
GPIO.setup([PIN_LEFT, PIN_CENTER, PIN_RIGHT], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def read_sensors():
    """读取3路磁探头，返回 (左, 中, 右) 的布尔值"""
    return (GPIO.input(PIN_LEFT), GPIO.input(PIN_CENTER), GPIO.input(PIN_RIGHT))

def cmd(data):
    """通过串口发送指令给小车底层"""
    ser.write((json.dumps(data) + '\n').encode('utf-8'))

def drive(left_speed, right_speed):
    """设置左右轮速度（-100 到 100）"""
    cmd({"T":1, "L":int(left_speed), "R":int(right_speed)})

def stop():
    """急停"""
    drive(0, 0)

def gimbal_reset():
    """云台回中"""
    cmd({"T":133, "X":0, "Y":0, "SPD":30, "ACC":10})

# ═══════════════════════════════════
#  磁轨循迹状态机
# ═══════════════════════════════════
#
#  状态说明：
#    FOLLOW     — 正常循迹中，根据探头状态调整方向
#    SEARCH     — 丢失磁条，原地旋转搜索
#    STOPPED    — 搜索超时，停车报警
#

STATE_FOLLOW = "FOLLOW"
STATE_SEARCH = "SEARCH"
STATE_STOPPED = "STOPPED"

# ═══════════════════════════════════
#  巡检站点配置
# ═══════════════════════════════════
#
#  在磁条路线上设置断点或RFID标签作为"站点"，
#  机器人到达时执行定点操作（拍照、测温等）
#
#  站点检测方式（二选一）：
#  方式A：磁条断点——站点处磁条断开5cm，所有探头都读不到
#  方式B：RFID标签——在磁条旁贴RFID，用RC522模块读标签ID
#
#  以下是方式A（磁条断点）的配置示例：

CHECKPOINTS = [
    {"name": "工位A", "duration": 5},   # 到达后停5秒
    {"name": "工位B", "duration": 3},   # 到达后停3秒
    {"name": "工位C", "duration": 8},   # 到达后停8秒
]

# ═══════════════════════════════════
#  循迹主逻辑
# ═══════════════════════════════════

def follow_track():
    """
    核心循迹逻辑——基于磁探头状态的有限状态机
    
    探头状态（左,中,右）-> 动作：
    (0,0,0)  -> 丢失磁条，触发搜索
    (1,0,0)  -> 左探头独中，偏右了，左转
    (0,1,0)  -> 中探头独中，正中，直走
    (0,0,1)  -> 右探头独中，偏左了，右转
    (1,1,0)  -> 左+中同时中，微微偏右，微左转
    (0,1,1)  -> 中+右同时中，微微偏左，微右转
    (1,1,1)  -> 三个全中，可能到了磁条汇合口或断点前
    """
    state = STATE_FOLLOW
    lost_start = 0       # 丢失磁条的时间戳
    checkpoint_idx = 0   # 当前执行到第几个站点
    in_checkpoint = False
    checkpoint_start = 0

    print("""
╔═══════════════════════════════════╗
║  🧲  RaspRover 磁轨循迹启动！    ║
║                                   ║
║  磁探头状态：                     ║
║    L=左  C=中  R=右               ║
║                                   ║
║  按 Q 退出                        ║
╚═══════════════════════════════════╝
""")

    try:
        while True:
            # ── 检查键盘退出（非阻塞） ──
            # 使用 select 代替 input() 实现无阻塞按键检测
            import select
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch == 'q':
                        print("\n👋 退出")
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

            # ── 读取磁探头 ──
            left, center, right = read_sensors()
            probe_state = f"L={left} C={center} R={right}"
            action = ""

            # ── 站点处理（磁条断点检测） ──
            # 连续3帧全0且不在搜索状态，说明到了断点
            if state == STATE_FOLLOW and not (left or center or right):
                # 有可能是磁条断点（站点）
                if checkpoint_idx < len(CHECKPOINTS):
                    cp = CHECKPOINTS[checkpoint_idx]
                    print(f"\n📍 到达站点: {cp['name']}，停车{cp['duration']}秒")
                    stop()
                    # 这里可以插入定点操作：
                    #   - 调用摄像头拍照
                    #   - 读取红外温度
                    #   - 发送图片到服务器
                    # 示例：print(f"📷 {cp['name']} 拍照中...")
                    time.sleep(cp['duration'])
                    checkpoint_idx += 1
                    # 越过断点后继续向前，小车会重新检测到磁条
                    drive(BASE_SPEED, BASE_SPEED)
                    time.sleep(1)
                    continue
                # 不在站点列表中断开，进入搜索模式
                state = STATE_SEARCH
                lost_start = time.time()
                action = "🔍 丢失磁条，开始搜索"
                stop()

            # ── 循迹状态机 ──
            elif state == STATE_FOLLOW:
                if center:
                    # ── 正中 ──
                    if left and right:
                        # 三个全中，正常直走
                        drive(BASE_SPEED, BASE_SPEED)
                        action = "⬆️ 正中直走"
                    elif left:
                        # 左+中，微微偏右
                        drive(BASE_SPEED - 10, BASE_SPEED + 10)
                        action = "↗️ 微左转"
                    elif right:
                        # 中+右，微微偏左
                        drive(BASE_SPEED + 10, BASE_SPEED - 10)
                        action = "↖️ 微右转"
                    else:
                        # 只有中探头，完美正中
                        drive(BASE_SPEED, BASE_SPEED)
                        action = "⬆️ 正中直走"
                elif left:
                    # ── 只有左探头 —— 磁条偏左，需要右转 ──
                    if right:
                        # 左右都中但中间不中（异常，可能干扰）
                        drive(BASE_SPEED, BASE_SPEED)
                        action = "⚠️ 干扰直走"
                    else:
                        drive(TURN_SPEED, -TURN_SPEED)
                        action = "➡️ 磁条偏左→右转"
                elif right:
                    # ── 只有右探头 —— 磁条偏右，需要左转 ──
                    drive(-TURN_SPEED, TURN_SPEED)
                    action = "⬅️ 磁条偏右→左转"
                else:
                    # 全0，应该是刚过了断点或在断点
                    if checkpoint_idx < len(CHECKPOINTS):
                        # 可能有未处理的断点，从发现断点已经过了
                        pass
                    else:
                        # 异常丢失
                        state = STATE_SEARCH
                        lost_start = time.time()
                        action = "🔍 丢失磁条，开始搜索"
                        stop()

            elif state == STATE_SEARCH:
                # ── 搜索模式：原地旋转，找磁条 ──
                elapsed = time.time() - lost_start
                if elapsed > LOST_TIMEOUT:
                    state = STATE_STOPPED
                    action = f"🛑 搜索超时({LOST_TIMEOUT}s)，停车"
                    stop()
                else:
                    # 缓慢旋转，左轮正转右轮反转
                    drive(25, -25)
                    action = f"🔄 旋转搜索中... (已过{elapsed:.1f}s)"

                    # 如果重新读到磁条，恢复循迹
                    if left or center or right:
                        state = STATE_FOLLOW
                        action = "✅ 重新找到磁条！"
                        lost_start = 0

            elif state == STATE_STOPPED:
                # ── 停车等待人工干预 ──
                action = "🛑 已停车，等待人工干预"
                drive(0, 0)

            # ── 打印状态 ──
            status_line = f"[{probe_state}] {action}"
            if state == STATE_FOLLOW:
                print(f"\r{' ' * 60", end="")
                print(f"\r{status_line}", end="", flush=True)
            else:
                print(f"\n{status_line}")

            time.sleep(0.05)  # 每50ms控制一次循环

    except KeyboardInterrupt:
        print("\n⚠️  收到中断信号")
    finally:
        stop()
        gimbal_reset()
        ser.close()
        GPIO.cleanup()
        print("✅ 已安全停车，GPIO已清理")
        print("🧲 磁轨循迹结束")

# ═══════════════════════════════════
#  入口
# ═══════════════════════════════════

if __name__ == "__main__":
    follow_track()
