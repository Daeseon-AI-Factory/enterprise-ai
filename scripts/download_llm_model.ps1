# ============================================================
# LLM 모델 다운로드 스크립트 (Windows, 인터넷 있는 PC에서 실행)
# 다운로드 후 ./models/llm/ 폴더를 폐쇄망 서버로 복사
#
# Usage:
#   .\scripts\download_llm_model.ps1                                     # 기본: Mistral 7B
#   .\scripts\download_llm_model.ps1 "meta-llama/Llama-3.1-8B-Instruct" # Llama 3.1 8B
# ============================================================

param(
    [string]$Model = "mistralai/Mistral-7B-Instruct-v0.3"
)

$TargetDir = "./models/llm"

Write-Host "======================================"
Write-Host "  LLM Model Downloader"
Write-Host "======================================"
Write-Host "Model:  $Model"
Write-Host "Target: $TargetDir"
Write-Host ""

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

# huggingface-cli 확인
$hfCli = Get-Command huggingface-cli -ErrorAction SilentlyContinue
if (-not $hfCli) {
    Write-Host "Installing huggingface_hub..."
    pip install -U huggingface_hub
}

Write-Host "Downloading model weights..."
huggingface-cli download $Model --local-dir "$TargetDir/$Model"

Write-Host ""
Write-Host "======================================"
Write-Host "  Download Complete!"
Write-Host "======================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy ./models/llm/ to the airgap server"
Write-Host "  2. Set VLLM_MODEL=$Model in .env.airgap"
Write-Host "  3. Run: docker compose -f docker-compose.vllm.yml up -d"
Write-Host "  4. Verify: curl http://localhost:8000/v1/models"
