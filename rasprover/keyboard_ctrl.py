# 🚗 RaspRover 键盘遥控（Jupyter版）🐷
# 在Jupyter里新建一个Python3 Notebook，把这段贴进去运行
# 然后点击下面的Cell，按键盘就能遥控啦！

# 使用说明：
#   WASD     → 开车（前进/左转/后退/右转）
#   ↑↓←→    → 云台（上下左右）
#   空格键   → 急停
#   Q        → 退出

import sys, termios, tty, select, os, json, time
import serial

# ─── 连接串口 ───
# 树莓派5用 ttyAMA0，树莓派4B用 serial0
SERIAL_PORT = '/dev/ttyAMA0'
BAUD = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")
except Exception as e:
    print(f"❌ 串口连接失败: {e}")
    print("试试改成 /dev/serial0")

def send_cmd(data):
    ser.write((json.dumps(data) + '\n').encode('utf-8'))

# ─── 按键获取 ───
def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ─── 打印操作说明 ───
print("""
╔══════════════════════════════════════╗
║      🐷  RaspRover 键盘遥控         ║
╠══════════════════════════════════════╣
║  WASD  →  开车                       ║
║  ↑↓←→  →  云台                       ║
║  空格  →  急停 🛑                    ║
║  Q     →  退出                       ║
╚══════════════════════════════════════╝
⚠️  点一下这个Cell再按键盘！
""")

# ─── 主循环 ───
speed = 0
gimbal_x, gimbal_y = 0, 0

try:
    while True:
        ch = get_key()
        if ch:
            if ch == 'w':
                speed = min(speed + 20, 100)
                send_cmd({"T":1, "L":speed, "R":speed})
                print(f"🚗 前进  speed={speed}")
            elif ch == 's':
                speed = max(speed - 20, -100)
                send_cmd({"T":1, "L":speed, "R":speed})
                print(f"🚗 后退  speed={speed}")
            elif ch == 'a':
                send_cmd({"T":1, "L":-40, "R":40})
                print(f"🚗 左转")
            elif ch == 'd':
                send_cmd({"T":1, "L":40, "R":-40})
                print(f"🚗 右转")
            elif ch == ' ':
                speed = 0
                send_cmd({"T":1, "L":0, "R":0})
                print("🛑 急停！")
            # 方向键
            elif ch == '\x1b':
                n1 = get_key()
                n2 = get_key()
                if n1 == '[':
                    if n2 == 'A':  # ↑
                        gimbal_y = min(gimbal_y + 10, 90)
                        send_cmd({"T":133, "X":gimbal_x, "Y":gimbal_y, "SPD":30, "ACC":10})
                        print(f"📷 云台上  y={gimbal_y}")
                    elif n2 == 'B':  # ↓
                        gimbal_y = max(gimbal_y - 10, -30)
                        send_cmd({"T":133, "X":gimbal_x, "Y":gimbal_y, "SPD":30, "ACC":10})
                        print(f"📷 云台下  y={gimbal_y}")
                    elif n2 == 'C':  # →
                        gimbal_x = min(gimbal_x + 10, 180)
                        send_cmd({"T":133, "X":gimbal_x, "Y":gimbal_y, "SPD":30, "ACC":10})
                        print(f"📷 云台右  x={gimbal_x}")
                    elif n2 == 'D':  # ←
                        gimbal_x = max(gimbal_x - 10, -180)
                        send_cmd({"T":133, "X":gimbal_x, "Y":gimbal_y, "SPD":30, "ACC":10})
                        print(f"📷 云台左  x={gimbal_x}")
            elif ch == 'q':
                print("👋 退出")
                break
        
        time.sleep(0.05)

except KeyboardInterrupt:
    pass
finally:
    send_cmd({"T":1, "L":0, "R":0})  # 停车
    send_cmd({"T":133, "X":0, "Y":0, "SPD":30, "ACC":10})  # 云台回中
    ser.close()
    print("✅ 已安全停车")
