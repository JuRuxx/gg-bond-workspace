#!/bin/bash
# TTS 脚本 - 让俺老猪开口说话！
# 用法: ./tts.sh "要说的话" [en|zh] [输出文件名]

set -e

TEXT="$1"
LANG="${2:-zh}"
OUTPUT="${3:-/tmp/ggbond-tts.wav}"

RUNTIME_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/runtime"
MODEL_DIR_BASE="$HOME/.openclaw/tools/sherpa-onnx-tts/models"

if [ "$LANG" = "zh" ]; then
  MODEL_DIR="$MODEL_DIR_BASE/zh-xiaoya"
  MODEL_FILE="$MODEL_DIR/zh_CN-xiao_ya-medium.onnx"
  TOKENS="$MODEL_DIR/tokens.txt"
  LEXICON="$MODEL_DIR/lexicon.txt"
  EXTRA="--vits-lexicon=$LEXICON"
else
  MODEL_DIR="$MODEL_DIR_BASE/en-lessac"
  MODEL_FILE="$MODEL_DIR/en_US-lessac-high.onnx"
  TOKENS="$MODEL_DIR/tokens.txt"
  LEXICON=""
  EXTRA="--vits-data-dir=$MODEL_DIR/espeak-ng-data"
fi

export DYLD_LIBRARY_PATH="$RUNTIME_DIR/lib:$DYLD_LIBRARY_PATH"

"$RUNTIME_DIR/bin/sherpa-onnx-offline-tts" \
  --vits-model="$MODEL_FILE" \
  --vits-tokens="$TOKENS" \
  $EXTRA \
  --output-filename="$OUTPUT" \
  "$TEXT" 2>&1

echo "OK: $OUTPUT"
