#!/bin/bash
# =============================================================================
# 巡检机器人 — 一键安装脚本
# 适用于树莓派5 + RaspRover 底盘
#
# 使用: bash setup_extra.sh
# =============================================================================

set -e  # 出错即停

echo "========================================"
echo "  🦾 产线巡检机器人 — 环境安装脚本"
echo "  超人强出品 💪🔥"
echo "========================================"
echo ""

# -------------------- 1. 系统包 --------------------
echo "[1/4] 安装系统依赖..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-smbus \
    i2c-tools python3-rpi.gpio \
    || echo "⚠️  部分系统包安装失败，继续..."

# 启用 I2C 接口 (如果尚未启用)
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "  启用 I2C 接口..."
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/firmware/config.txt || true
    echo "  ⚠️  I2C 已启用，请重启树莓派后生效"
fi

# -------------------- 2. Python 虚拟环境 --------------------
echo ""
echo "[2/4] 设置 Python 虚拟环境..."

VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  ✅ 虚拟环境创建: $VENV_DIR"
else
    echo "  ℹ️  虚拟环境已存在"
fi

source "$VENV_DIR/bin/activate"

# -------------------- 3. Python 依赖 --------------------
echo ""
echo "[3/4] 安装 Python 依赖..."

# 先从官方代码安装基础依赖
OFFICIAL_REQS="../requirements.txt"
if [ -f "$OFFICIAL_REQS" ]; then
    echo "  -> 安装官方基础依赖..."
    pip install -r "$OFFICIAL_REQS" || echo "  ⚠️  部分官方依赖安装失败"
fi

# 安装巡检模块额外依赖
EXTRA_REQS="requirements_extra.txt"
if [ -f "$EXTRA_REQS" ]; then
    echo "  -> 安装巡检模块依赖..."
    pip install -r "$EXTRA_REQS" || echo "  ⚠️  部分额外依赖安装失败"
fi

pip install --upgrade pip

echo "  ✅ Python 依赖安装完成"

# -------------------- 4. 验证安装 --------------------
echo ""
echo "[4/4] 验证安装..."

echo "  检查 Python 模块..."
python3 -c "
try:
    import smbus2; print('    ✅ smbus2', smbus2.__version__)
except ImportError: print('    ❌ smbus2 — 未安装')

try:
    import yaml; print('    ✅ PyYAML', yaml.__version__)
except ImportError: print('    ℹ️  PyYAML — 未安装 (可使用JSON)')

try:
    import RPi; print('    ✅ RPi.GPIO')
except ImportError: print('    ℹ️  RPi.GPIO — 未在非树莓派环境中检查')

try:
    import cv2; print('    ✅ OpenCV', cv2.__version__)
except ImportError: print('    ℹ️  OpenCV — 未安装')

print()
print('    🎉 所有关键模块检查完成')
"

echo ""
echo "========================================"
echo "  🎉 安装完成！"
echo ""
echo "  使用方法:"
echo "    source $VENV_DIR/bin/activate"
echo "    python -m inspection.patroller    # 跑测试"
echo ""
echo "  配置:"
echo "    编辑 config.yaml 调整巡检路线和参数"
echo ""
echo "  祝巡检顺利！GG Bond，变身！💪🔥"
echo "========================================"
