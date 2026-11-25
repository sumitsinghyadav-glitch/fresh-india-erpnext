# Wrapper for the second ERPNext bench. Usage: .\bench2.ps1 up -d | ps | logs -f | down | exec backend bash
$fd = Join-Path $PSScriptRoot "..\frappe_docker"
docker compose -p frappe_bench2 --project-directory $fd --env-file (Join-Path $PSScriptRoot "bench2.env") `
  -f "$fd\compose.yaml" `
  -f "$fd\overrides\compose.mariadb.yaml" `
  -f "$fd\overrides\compose.redis.yaml" `
  -f "$fd\overrides\compose.noproxy.yaml" `
  -f (Join-Path $PSScriptRoot "compose.bench2.yaml") @args
