#!/bin/bash
# ============================================================
# LLM 모델 다운로드 스크립트 (인터넷 있는 PC에서 실행)
# 다운로드 후 ./models/llm/ 폴더를 폐쇄망 서버로 복사
#
# Usage:
#   bash scripts/download_llm_model.sh                                    # 기본: Mistral 7B
#   bash scripts/download_llm_model.sh meta-llama/Llama-3.1-8B-Instruct  # Llama 3.1 8B
#   bash scripts/download_llm_model.sh Qwen/Qwen2.5-7B-Instruct          # Qwen 2.5 7B
# ============================================================

set -euo pipefail

MODEL="${1:-mistralai/Mistral-7B-Instruct-v0.3}"
TARGET_DIR="./models/llm"

echo "======================================"
echo "  LLM Model Downloader"
echo "======================================"
echo "Model:  $MODEL"
echo "Target: $TARGET_DIR"
echo ""

mkdir -p "$TARGET_DIR"

# huggingface-cli 확인
if ! command -v huggingface-cli &>/dev/null; then
    echo "huggingface-cli not found. Installing..."
    pip install -U huggingface_hub
fi

echo "Downloading model weights..."
huggingface-cli download "$MODEL" --local-dir "$TARGET_DIR/$MODEL"

echo ""
echo "======================================"
echo "  Download Complete!"
echo "======================================"
echo ""
echo "Model size:"
du -sh "$TARGET_DIR/$MODEL"
echo ""
echo "Next steps:"
echo "  1. Copy ./models/llm/ to the airgap server"
echo "  2. Set VLLM_MODEL=$MODEL in .env.airgap"
echo "  3. Run: docker compose -f docker-compose.vllm.yml up -d"
echo "  4. Verify: curl http://localhost:8000/v1/models"
