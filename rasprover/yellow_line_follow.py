#!/usr/bin/env python3
# 🚗 RaspRover 黄色循迹 🐷
# 用法：在树莓派终端运行：python3 yellow_line_follow.py
# 摄像头会识别地上的黄色胶带，自动跟着走！
# 按 Q 退出

import cv2
import numpy as np
import json
import time
import serial
import sys

# ─── 连接小车串口 ───
SERIAL_PORT = '/dev/ttyAMA0'  # RPi5
try:
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")
except:
    SERIAL_PORT = '/dev/serial0'  # RPi4B
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")

def cmd(data):
    ser.write((json.dumps(data) + '\n').encode('utf-8'))

def stop():
    cmd({"T":1, "L":0, "R":0})

# ─── 黄色HSV范围（可调） ───
YELLOW_LOWER = np.array([20, 80, 80])
YELLOW_UPPER = np.array([35, 255, 255])

# ─── 摄像头初始化 ───
# CSI摄像头（树莓派）
try:
    from picamera2 import Picamera2
    picam = Picamera2()
    picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
    picam.start()
    print("✅ CSI摄像头启动成功！")
    using_csi = True
except:
    # USB摄像头
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("✅ USB摄像头启动成功！")
    using_csi = False

# ─── 控制参数 ───
BASE_SPEED = 40       # 基础速度
TURN_SPEED = 30       # 转弯速度
MAX_TURN = 60         # 最大转向
FRAME_CENTER = 320    # 画面中心X
DEAD_ZONE = 40        # 死区，在中心±40内直走

print("""
╔══════════════════════════════════╗
║  🐷 黄色循迹启动！               ║
║  地上贴好黄色胶带，小车自己跑！  ║
║  按 Q 退出                       ║
╚══════════════════════════════════╝
""")

try:
    while True:
        # ── 获取画面 ──
        if using_csi:
            frame = picam.capture_array()
        else:
            ret, frame = cap.read()
            if not ret: continue

        # HSV转换 + 黄色掩膜
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)

        # 去噪
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # 找黄色区域的轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # 取最大的黄色区域
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if area > 500:  # 面积太小就忽略
                # 计算区域中心
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # 在画面上标记
                    cv2.drawContours(frame, [largest], -1, (0, 255, 255), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

                    # ── 循迹控制逻辑 ──
                    offset = cx - FRAME_CENTER  # 正=偏右，负=偏左

                    if abs(offset) < DEAD_ZONE:
                        # 在中心，直走
                        cmd({"T":1, "L":BASE_SPEED, "R":BASE_SPEED})
                        status = "⬆️ 直走"
                    else:
                        # 偏了，转向修正
                        # offset越大转向越猛
                        turn_factor = min(abs(offset) / FRAME_CENTER, 1.0)
                        turn = int(TURN_SPEED + turn_factor * (MAX_TURN - TURN_SPEED))

                        if offset > 0:  # 偏右→左转
                            cmd({"T":1, "L":-turn, "R":turn})
                            status = f"⬅️ 左转 (offset={offset})"
                        else:  # 偏左→右转
                            cmd({"T":1, "L":turn, "R":-turn})
                            status = f"➡️ 右转 (offset={offset})"

                    cv2.putText(frame, status, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.line(frame, (FRAME_CENTER, 0), (FRAME_CENTER, 480),
                             (0, 255, 0), 1)
                    cv2.line(frame, (cx, cy-10), (cx, cy+10), (0, 0, 255), 2)
                    cv2.line(frame, (cx-10, cy), (cx+10, cy), (0, 0, 255), 2)
            else:
                status = "⏸️ 未检测到黄色区域"
                stop()
                cv2.putText(frame, status, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            status = "⏸️ 未检测到黄色区域"
            stop()
            cv2.putText(frame, status, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ── 显示画面 ──
        cv2.imshow("🐷 黄色循迹 - 按Q退出", frame)
        cv2.imshow("黄色掩膜", mask)

        # ── 按Q退出 ──
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    stop()
    cmd({"T":133, "X":0, "Y":0, "SPD":30, "ACC":10})
    ser.close()
    if using_csi:
        picam.stop()
    else:
        cap.release()
    cv2.destroyAllWindows()
    print("✅ 安全停车，循迹结束！")
