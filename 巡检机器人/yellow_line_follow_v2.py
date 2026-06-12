#!/usr/bin/env python3
# 🐷 RaspRover 黄色循迹 v2

import cv2
import numpy as np
import json
import time
import serial

# ─── 串口 ───
SERIAL_PORT = '/dev/ttyAMA0'
try:
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")
except:
    SERIAL_PORT = '/dev/serial0'
    ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
    print(f"✅ 串口 {SERIAL_PORT} 连接成功！")

def cmd(data):
    ser.write((json.dumps(data) + '\n').encode('utf-8'))

def stop():
    cmd({"T":1, "L":0, "R":0})

# ─── 摄像头 ───
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print(f"✅ USB摄像头启动成功！")

# ─── 黄色HSV ───
YELLOW_LOWER = np.array([20, 80, 80])
YELLOW_UPPER = np.array([35, 255, 255])

# ─── 控制参数 (m/s) ───
BASE_SPEED = 0.2
FRAME_CENTER = 320
DEAD_ZONE = 60

print("""
╔══════════════════════════════╗
║  🐷 黄色循迹 v2 启动！      ║
║  按 Q 退出                   ║
╚══════════════════════════════╝
""")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        status = "⏸️ 未检测到黄色"
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area > 500:
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cv2.drawContours(frame, [largest], -1, (0, 255, 255), 2)
                    cv2.circle(frame, (cx, 240), 5, (0, 0, 255), -1)

                    offset = cx - FRAME_CENTER

                    if abs(offset) < DEAD_ZONE:
                        # 直走
                        cmd({"T":1, "L":BASE_SPEED, "R":BASE_SPEED})
                        status = f"⬆️ 直走 ({offset})"
                    elif offset > 0:
                        # 黄色偏右 → 左转（左轮慢、右轮快）
                        cmd({"T":1, "L":BASE_SPEED * 0.3, "R":BASE_SPEED})
                        status = f"⬅️ 左转 ({offset})"
                    else:
                        # 黄色偏左 → 右转（右轮慢、左轮快）
                        cmd({"T":1, "L":BASE_SPEED, "R":BASE_SPEED * 0.3})
                        status = f"➡️ 右转 ({offset})"

                    cv2.putText(frame, status, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.line(frame, (FRAME_CENTER, 0), (FRAME_CENTER, 480), (0, 255, 0), 1)
            else:
                stop()
        else:
            stop()

        if not contours or area <= 500:
            cv2.putText(frame, status, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("🐷 黄色循迹 - 按Q退出", frame)
        cv2.imshow("黄色掩膜", mask)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    stop()
    cmd({"T":133, "X":0, "Y":0, "SPD":30, "ACC":10})
    ser.close()
    cap.release()
    cv2.destroyAllWindows()
    print("✅ 安全停车，循迹结束！")
