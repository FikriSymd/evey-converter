# Menjalankan evey-converter di Windows.
#
#   .\tools\run-windows.ps1            mode pengembangan (auto-reload, buat edit kode)
#   .\tools\run-windows.ps1 -Prod      mode produksi (lebih cepat, tanpa reload)
#
# Buka http://127.0.0.1:8080 setelah jendela ini menampilkan
# "Uvicorn running on http://127.0.0.1:8080".

param(
    [switch]$Prod,
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$proj = Split-Path -Parent $PSScriptRoot
$venvPy = Join-Path $proj ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "Virtualenv belum ada di $venvPy" -ForegroundColor Red
    Write-Host "Jalankan dulu: .\tools\setup-windows.ps1" -ForegroundColor Yellow
    exit 1
}

# Tesseract dan Ghostscript tidak selalu masuk PATH saat installer-nya jalan.
$env:Path = "C:\Program Files\Tesseract-OCR;C:\Program Files\gs;C:\Program Files\LibreOffice\program;" +
            $env:Path
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\Program Files\GTK3-Runtime Win64\bin"

Set-Location (Join-Path $proj "backend")

Write-Host ""
Write-Host "  evey-converter" -ForegroundColor Cyan
Write-Host "  Mode    : $(if ($Prod) { 'produksi' } else { 'pengembangan (kode otomatis dimuat ulang)' })"
Write-Host "  Alamat  : http://127.0.0.1:$Port"
Write-Host "  Berhenti: tekan Ctrl+C"
Write-Host ""

$args = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port", "--log-level", "info")
if (-not $Prod) {
    $args += @("--reload", "--reload-dir", "app")
}

& $venvPy @args