# Setup otomatis evey-converter di Windows 10 (64-bit).
#
# Menyiapkan: Python, paket Python, Ghostscript, Tesseract + bahasa Indonesia,
# LibreOffice, GTK (buat WeasyPrint), lalu bikin virtualenv dan menjalankan
# pemeriksaan akhir.
#
# Jalankan lewat PowerShell sebagai Administrator:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup-windows.ps1
#
# Idempoten: boleh dijalankan ulang. Yang sudah terpasang akan dilewati.

$ErrorActionPreference = "Stop"

function Section($text) {
    Write-Host ""
    Write-Host ("=" * 62) -ForegroundColor DarkGray
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 62) -ForegroundColor DarkGray
}
function Ok($text)   { Write-Host "  [OK]   $text" -ForegroundColor Green }
function Skip($text) { Write-Host "  [SKIP] $text" -ForegroundColor DarkYellow }
function Info($text) { Write-Host "  ->     $text" -ForegroundColor Gray }
function Warn($text) { Write-Host "  [!]    $text" -ForegroundColor Yellow }

function Have($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

# Apakah paket winget sudah terpasang.
function HaveWinget($id) {
    try {
        $out = winget list --id $id --exact --accept-source-agreements 2>$null
        return ($LASTEXITCODE -eq 0 -and $out -match [regex]::Escape($id))
    } catch { return $false }
}

# ---- 0. Cek prasyarat ----------------------------------------------------
Section "0. Cek prasyarat"

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "  Windows 32-bit tidak didukung. Batalkan." -ForegroundColor Red
    exit 1
}
Ok "Windows 64-bit"

if (-not (Have winget)) {
    Warn "winget tidak ditemukan."
    Warn "Pasang 'App Installer' dari Microsoft Store, tutup PowerShell, buka lagi, jalankan ulang skrip ini."
    exit 1
}
Ok "winget tersedia"

$admin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Warn "PowerShell ini tidak sebagai Administrator. Beberapa pemasangan akan gagal."
    Warn "Tutup, buka PowerShell sebagai Administrator, jalankan lagi."
    exit 1
}
Ok "berjalan sebagai Administrator"

# ---- 1. Python 3.12 -----------------------------------------------------
Section "1. Python 3.12"

if (Have python) {
    $v = (& python --version 2>&1) -join ""
    Skip "Python sudah ada: $v"
} else {
    Info "winget install Python.Python.3.12"
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    if (Have python) { Ok "Python terpasang: $((& python --version 2>&1) -join '')" }
    else { Warn "Python belum ada di PATH. Tutup PowerShell, buka lagi, jalankan ulang."; exit 1 }
}

# ---- 2. Tesseract + bahasa Indonesia ------------------------------------
Section "2. Tesseract OCR"

if (HaveWinget "UB-Mannheim.TesseractOCR" -or (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe")) {
    Skip "Tesseract sudah terpasang"
} else {
    Info "winget install UB-Mannheim.TesseractOCR"
    winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
    Ok "Tesseract terpasang"
}

# Data bahasa Indonesia tidak ikut di installer Tesseract. Aman diunduh ulang.
$tessDir = "C:\Program Files\Tesseract-OCR\tessdata"
if (Test-Path "$tessDir\ind.traineddata") {
    Skip "Data bahasa Indonesia sudah ada"
} else {
    Info "Mengunduh data bahasa Indonesia (ind.traineddata)"
    try {
        Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/ind.traineddata" `
            -OutFile "$tessDir\ind.traineddata" -UseBasicParsing
        Ok "ind.traineddata terpasang"
    } catch {
        Warn "Gagal mengunduh ind.traineddata. Unduh manual dari:"
        Warn "  https://github.com/tesseract-ocr/tessdata/raw/main/ind.traineddata"
        Warn "Simpan ke: $tessDir"
    }
}

# ---- 3. Ghostscript -----------------------------------------------------
Section "3. Ghostscript"

$gsExe = Get-ChildItem "C:\Program Files\gs" -Recurse -Filter "gswin64c.exe" -ErrorAction SilentlyContinue |
         Select-Object -First 1
if ($gsExe) {
    Skip "Ghostscript sudah ada: $($gsExe.FullName)"
} else {
    Info "winget install ArtifexSoftware.GhostScript"
    winget install -e --id ArtifexSoftware.GhostScript --accept-source-agreements --accept-package-agreements
    $gsExe = Get-ChildItem "C:\Program Files\gs" -Recurse -Filter "gswin64c.exe" -ErrorAction SilentlyContinue |
             Select-Object -First 1
    if ($gsExe) { Ok "Ghostscript terpasang: $($gsExe.FullName)" }
    else {
        Warn "Ghostscript belum ketemu. Kalau winget tidak punya paketnya, unduh manual:"
        Warn "  https://www.ghostscript.com/releases/gsdnld.html"
        Warn "Pilih 'Ghostscript AGPL Release', Windows 64-bit."
    }
}

# ---- 4. LibreOffice -----------------------------------------------------
Section "4. LibreOffice"

if (Test-Path "C:\Program Files\LibreOffice\program\soffice.exe") {
    Skip "LibreOffice sudah terpasang"
} else {
    Info "winget install TheDocumentFoundation.LibreOffice"
    winget install -e --id TheDocumentFoundation.LibreOffice --accept-source-agreements --accept-package-agreements
    if (Test-Path "C:\Program Files\LibreOffice\program\soffice.exe") { Ok "LibreOffice terpasang" }
    else { Warn "LibreOffice belum ketemu. Unduh manual: https://www.libreoffice.org/download/" }
}

# ---- 5. GTK (buat WeasyPrint / Web ke PDF) ------------------------------
Section "5. GTK runtime (WeasyPrint)"

if (Test-Path "C:\Program Files\GTK3-Runtime Win64\bin\libpango-1.0-0.dll") {
    Skip "GTK3 runtime sudah terpasang"
} else {
    Info "Mengunduh GTK3 runtime installer"
    $gtkUrl = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
    $gtkExe = "$env:TEMP\gtk3-runtime.exe"
    try {
        Invoke-WebRequest -Uri $gtkUrl -OutFile $gtkExe -UseBasicParsing
        Info "Menjalankan installer GTK (unattended)"
        Start-Process -FilePath $gtkExe -ArgumentList "/S" -Wait
        if (Test-Path "C:\Program Files\GTK3-Runtime Win64\bin\libpango-1.0-0.dll") {
            Ok "GTK3 runtime terpasang"
        } else {
            Warn "Installer GTK selesai tapi DLL belum ketemu. Coba jalankan installer-nya manual."
        }
    } catch {
        Warn "Gagal memasang GTK otomatis. Unduh manual dari:"
        Warn "  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases"
        Warn "Setelah dipasang, tool 'Web ke PDF' baru bisa jalan. Tool lain tidak terpengaruh."
    }
    # WeasyPrint membaca env var ini kalau PATH belum sepenuhnya ter-refresh.
    [Environment]::SetEnvironmentVariable(
        "WEASYPRINT_DLL_DIRECTORIES", "C:\Program Files\GTK3-Runtime Win64\bin", "Machine")
    Ok "WEASYPRINT_DLL_DIRECTORIES diset"
}

# ---- 6. Virtualenv + paket Python ---------------------------------------
Section "6. Virtualenv dan paket Python"

$proj = Split-Path -Parent $PSScriptRoot        # folder induk dari tools\, yaitu akar proyek
$venv = Join-Path $proj ".venv"
Info "Folder proyek: $proj"

if (Test-Path "$venv\Scripts\python.exe") {
    Skip "Virtualenv sudah ada: $venv"
} else {
    Info "Membuat virtualenv"
    & python -m venv $venv
    Ok "Virtualenv dibuat"
}

$vpy = "$venv\Scripts\python.exe"
Info "Memperbarui pip"
& $vpy -m pip install --upgrade pip --quiet

$req = Join-Path $proj "backend\requirements.txt"
if (Test-Path $req) {
    Info "Memasang paket dari backend\requirements.txt (3-8 menit, sabar)"
    & $vpy -m pip install -r $req
    Ok "Paket Python terpasang"
} else {
    Warn "requirements.txt tidak ditemukan di $req"
    exit 1
}

# ---- 7. Refresh PATH, lalu periksa --------------------------------------
Section "7. Pemeriksaan akhir"

$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path

$doctor = Join-Path $PSScriptRoot "doctor.py"
if (Test-Path $doctor) {
    & $vpy $doctor
} else {
    Warn "doctor.py tidak ditemukan, lewati pemeriksaan"
}

Section "Selesai"
Write-Host "  Kalau semua di atas hijau, jalankan aplikasinya dengan:" -ForegroundColor White
Write-Host "    .\tools\run-windows.ps1" -ForegroundColor White
Write-Host "  lalu buka http://127.0.0.1:8080 di browser." -ForegroundColor White
Write-Host ""
Write-Host "  Kalau ada yang belum hijau, tutup PowerShell, buka lagi, dan jalankan skrip ini ulang." -ForegroundColor Gray
