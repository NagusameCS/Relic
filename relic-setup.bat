@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title RELIC Setup Wizard
color 07
cls

echo.
echo  ============================================================
echo.
echo   ████████╗ ███████╗ ██╗      ██╗  ██████╗
echo   ██╔═══██║ ██╔════╝ ██║      ██║ ██╔════╝
echo   ████████║ █████╗   ██║      ██║ ██║
echo   ██╔═══██╝ ██╔══╝   ██║      ██║ ██║
echo   ██║   ██║ ███████╗ ███████╗ ██║ ╚██████╗
echo   ╚═╝   ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═════╝
echo.
echo   Automated Penetration Testing Framework
echo   Setup Wizard v1.0
echo.
echo  ============================================================
echo.
echo.
echo  ┌──────────────────────────────────────────────────────────┐
echo  │               TERMS AND CONDITIONS                       │
echo  └──────────────────────────────────────────────────────────┘
echo.
echo   1. AUTHORIZED USE ONLY
echo      RELIC is designed exclusively for authorized security
echo      testing. You MUST have explicit written permission from
echo      the system owner before testing any target. Unauthorized
echo      access to computer systems is illegal under the CFAA
echo      and equivalent laws worldwide.
echo.
echo   2. USER RESPONSIBILITY
echo      You are solely responsible for your actions while using
echo      RELIC. The developers assume no liability for misuse,
echo      damage, or legal consequences resulting from use of
echo      this software.
echo.
echo   3. EDUCATIONAL PURPOSE
echo      RELIC is provided as an educational and professional
echo      security tool. It must be used responsibly, ethically,
echo      and only within legal boundaries.
echo.
echo   4. SCOPE ENFORCEMENT
echo      RELIC includes built-in scope enforcement. You must
echo      configure authorized targets before scanning. Attempting
echo      to bypass scope restrictions is prohibited.
echo.
echo   5. LOCAL PROCESSING
echo      RELIC uses local LLMs via Ollama. Your data stays on
echo      your machine. No data is sent to external servers beyond
echo      the targets you explicitly scan.
echo.
echo   6. NO WARRANTY
echo      This software is provided "AS IS" without warranty of
echo      any kind, express or implied. No guarantees are made
echo      about accuracy, reliability, or completeness of results.
echo.
echo   7. COMPLIANCE
echo      You must comply with all applicable local, state,
echo      national, and international laws when using RELIC.
echo.
echo   8. MIT LICENSE
echo      RELIC is open-source software released under the MIT
echo      License. See LICENSE file for full terms.
echo.
echo  ──────────────────────────────────────────────────────────
echo.
choice /C YN /M "  Do you accept the Terms and Conditions"
if errorlevel 2 (
    echo.
    echo   Setup cancelled. You must accept the terms to continue.
    echo.
    pause
    exit /b 1
)

echo.
echo   Terms accepted. Starting automated setup...
echo.
echo  ============================================================
echo.

REM === Launch embedded PowerShell installer ===
set "RELIC_SELF=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$lines = Get-Content -LiteralPath $env:RELIC_SELF -Encoding UTF8;" ^
    "$start = -1;" ^
    "for ($i = 0; $i -lt $lines.Count; $i++) {" ^
    "  if ($lines[$i] -match '^\#\ ===RELIC_PS_BEGIN===') { $start = $i + 1; break }" ^
    "};" ^
    "if ($start -lt 0) { Write-Error 'PowerShell section not found'; exit 1 };" ^
    "$script = $lines[$start..($lines.Count - 1)] -join [char]10;" ^
    "Invoke-Expression $script"

set "EXITCODE=%ERRORLEVEL%"

if %EXITCODE% neq 0 (
    echo.
    echo   [!] Setup encountered errors. See messages above.
    echo.
)

pause
exit /b %EXITCODE%

# ===RELIC_PS_BEGIN===
# ══════════════════════════════════════════════════════════════
# RELIC Setup Wizard — PowerShell Installer
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

# ── Configuration ──────────────────────────────────────────────

$REPO_URL   = "https://github.com/NagusameCS/Relic.git"
$OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
$OLLAMA_API = "http://127.0.0.1:11434"

$MODEL_TABLE = @(
    @{ Name="GLM-4.7-Flash"; Ollama="glm4-flash";     SizeGB=19; MinVRAM=8;  MinRAM=24; Tier="Recommended" }
    @{ Name="Gemma 3 12B";   Ollama="gemma3:12b";     SizeGB=8;  MinVRAM=8;  MinRAM=16; Tier="High-end"    }
    @{ Name="Qwen 2.5 7B";   Ollama="qwen2.5:7b";     SizeGB=5;  MinVRAM=4;  MinRAM=12; Tier="Mid-range"   }
    @{ Name="Gemma 3 4B";    Ollama="gemma3:4b";       SizeGB=3;  MinVRAM=3;  MinRAM=8;  Tier="Mid-range"   }
    @{ Name="Qwen 2.5 3B";   Ollama="qwen2.5:3b";     SizeGB=2;  MinVRAM=2;  MinRAM=8;  Tier="Low-end"     }
    @{ Name="Phi-3.5 Mini";  Ollama="phi3.5:latest";   SizeGB=2;  MinVRAM=2;  MinRAM=8;  Tier="Low-end"     }
)

# ── Helpers ────────────────────────────────────────────────────

function Write-Step {
    param([int]$Num, [string]$Title)
    Write-Host ""
    Write-Host "  [$Num/7] $Title" -ForegroundColor White
    Write-Host "  ────────────────────────────────────────────" -ForegroundColor DarkGray
}

function Write-OK   { param([string]$Msg) Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  [!]  $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "  [X]  $Msg" -ForegroundColor Red }
function Write-Info { param([string]$Msg) Write-Host "       $Msg" -ForegroundColor Gray }

# ── Step 1: Detect Python ─────────────────────────────────────

Write-Step 1 "Checking Python"

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match 'Python\s+3\.(\d+)') {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $pythonCmd = $cmd
                Write-OK "Found: $ver"
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Warn "Python 3.10+ not found. Attempting install via winget..."
    try {
        & winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Null
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                     [System.Environment]::GetEnvironmentVariable("PATH", "User")
        $pythonCmd = "python"
        $ver = & python --version 2>&1
        Write-OK "Installed: $ver"
    } catch {
        Write-Fail "Could not install Python automatically."
        Write-Info "Please install Python 3.10+ from https://python.org/downloads"
        Write-Info "Make sure to check 'Add Python to PATH' during installation."
        exit 1
    }
}

# Verify pip
try {
    & $pythonCmd -m pip --version 2>&1 | Out-Null
    Write-OK "pip available"
} catch {
    Write-Warn "pip not found, installing..."
    & $pythonCmd -m ensurepip --upgrade 2>&1 | Out-Null
}

# ── Step 2: Detect / Install Ollama ───────────────────────────

Write-Step 2 "Checking Ollama"

$ollamaCmd = $null
$ollamaPaths = @(
    "ollama",
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe"
)

foreach ($p in $ollamaPaths) {
    try {
        $v = & $p --version 2>&1
        if ($v -match 'ollama') {
            $ollamaCmd = $p
            Write-OK "Found: $v"
            break
        }
    } catch {}
}

if (-not $ollamaCmd) {
    Write-Warn "Ollama not found. Downloading installer..."

    $installerPath = Join-Path $env:TEMP "OllamaSetup.exe"
    try {
        Write-Info "Downloading from ollama.com..."
        Invoke-WebRequest -Uri $OLLAMA_URL -OutFile $installerPath -UseBasicParsing
        Write-OK "Download complete"
    } catch {
        Write-Fail "Failed to download Ollama: $_"
        Write-Info "Please install manually from https://ollama.com/download"
        exit 1
    }

    Write-Info "Running Ollama installer (this may take a moment)..."
    try {
        $proc = Start-Process -FilePath $installerPath -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            # Try without silent flags (older installer versions)
            Write-Warn "Silent install failed, launching interactive installer..."
            $proc = Start-Process -FilePath $installerPath -Wait -PassThru
        }
    } catch {
        Write-Warn "Silent install not supported, launching installer..."
        Start-Process -FilePath $installerPath -Wait
    }

    # Clean up
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                 [System.Environment]::GetEnvironmentVariable("PATH", "User")

    # Verify
    $ollamaCmd = $null
    foreach ($p in $ollamaPaths) {
        try {
            $v = & $p --version 2>&1
            if ($v -match 'ollama') {
                $ollamaCmd = $p
                Write-OK "Installed: $v"
                break
            }
        } catch {}
    }

    if (-not $ollamaCmd) {
        Write-Fail "Ollama installation could not be verified."
        Write-Info "Please install manually from https://ollama.com/download"
        Write-Info "Then re-run this setup."
        exit 1
    }
}

# ── Step 3: Ensure Ollama service is running ──────────────────

Write-Step 3 "Starting Ollama Service"

$ollamaReady = $false
try {
    $resp = Invoke-WebRequest -Uri "$OLLAMA_API/api/tags" -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) { $ollamaReady = $true }
} catch {}

if (-not $ollamaReady) {
    Write-Info "Starting Ollama service..."

    # Try starting via ollama serve in background
    $ollamaServe = Start-Process -FilePath $ollamaCmd -ArgumentList "serve" -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue

    # Wait up to 30 seconds for it to be ready
    $retries = 0
    while ($retries -lt 15) {
        Start-Sleep -Seconds 2
        $retries++
        try {
            $resp = Invoke-WebRequest -Uri "$OLLAMA_API/api/tags" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) { $ollamaReady = $true; break }
        } catch {}
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ""
}

if ($ollamaReady) {
    Write-OK "Ollama service is running"
} else {
    Write-Fail "Ollama service did not start within 30 seconds."
    Write-Info "Try running 'ollama serve' manually, then re-run this setup."
    exit 1
}

# ── Step 4: Install RELIC ─────────────────────────────────────

Write-Step 4 "Installing RELIC"

Write-Info "Installing from GitHub (this may take a minute)..."
$pipOutput = & $pythonCmd -m pip install "relic[web] @ git+https://$REPO_URL" --upgrade 2>&1
$pipExit = $LASTEXITCODE

if ($pipExit -ne 0) {
    # Try alternate install syntax
    Write-Warn "Primary install method failed, trying alternate..."
    $pipOutput = & $pythonCmd -m pip install "git+https://github.com/NagusameCS/Relic.git#egg=relic[web]" --upgrade 2>&1
    $pipExit = $LASTEXITCODE
}

if ($pipExit -ne 0) {
    Write-Fail "Failed to install RELIC."
    Write-Info "Error output:"
    $pipOutput | Select-Object -Last 10 | ForEach-Object { Write-Info "  $_" }
    Write-Info ""
    Write-Info "Try manually: pip install `"git+https://github.com/NagusameCS/Relic.git#egg=relic[web]`""
    exit 1
}

# Verify entry point
try {
    $relicVer = & $pythonCmd -c "import relic; print('OK')" 2>&1
    if ($relicVer -match 'OK') {
        Write-OK "RELIC installed successfully"
    } else {
        Write-OK "RELIC package installed (could not verify import)"
    }
} catch {
    Write-OK "RELIC package installed"
}

# ── Step 5: Detect Hardware & Select Model ────────────────────

Write-Step 5 "Detecting Hardware"

# RAM
$ramGB = 0
try {
    $ramBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    $ramGB = [math]::Round($ramBytes / 1GB)
} catch {
    $ramGB = 8  # Safe default
}
Write-Info "System RAM: ${ramGB} GB"

# VRAM (NVIDIA)
$vramGB = 0
try {
    $nvsmi = & "nvidia-smi" --query-gpu=memory.total --format=csv,noheader,nounits 2>&1
    if ($LASTEXITCODE -eq 0 -and $nvsmi -match '^\d+') {
        $vramMB = [int]($nvsmi -split "`n" | Select-Object -First 1).Trim()
        $vramGB = [math]::Round($vramMB / 1024)
    }
} catch {}

# Fallback: WMI adapter RAM (less accurate, includes integrated)
if ($vramGB -eq 0) {
    try {
        $adapters = Get-CimInstance Win32_VideoController | Where-Object { $_.AdapterRAM -gt 0 }
        $maxAdapterRAM = ($adapters | Measure-Object -Property AdapterRAM -Maximum).Maximum
        if ($maxAdapterRAM -gt 0) {
            $vramGB = [math]::Round($maxAdapterRAM / 1GB)
            Write-Info "GPU VRAM: ~${vramGB} GB (estimated from WMI)"
        } else {
            Write-Info "GPU VRAM: Unknown (will use CPU inference)"
        }
    } catch {
        Write-Info "GPU VRAM: Could not detect"
    }
} else {
    Write-Info "GPU VRAM: ${vramGB} GB (NVIDIA)"
}

# Select best model
$selectedModel = $null
foreach ($m in $MODEL_TABLE) {
    if ($vramGB -ge $m.MinVRAM -and $ramGB -ge $m.MinRAM) {
        $selectedModel = $m
        break
    }
}

# Fallback to smallest model
if (-not $selectedModel) {
    $selectedModel = $MODEL_TABLE[-1]
}

Write-Host ""
Write-Host "  Selected Model: $($selectedModel.Name)" -ForegroundColor Cyan
Write-Info "Tier: $($selectedModel.Tier) | Size: $($selectedModel.SizeGB) GB"
Write-Info "Requires: VRAM >= $($selectedModel.MinVRAM) GB, RAM >= $($selectedModel.MinRAM) GB"

# ── Step 6: Pull Model ────────────────────────────────────────

Write-Step 6 "Downloading AI Model"

# Check if model already exists
$modelExists = $false
try {
    $tagResp = Invoke-WebRequest -Uri "$OLLAMA_API/api/tags" -UseBasicParsing -TimeoutSec 5
    $tags = $tagResp.Content | ConvertFrom-Json
    foreach ($existing in $tags.models) {
        if ($existing.name -match $selectedModel.Ollama.Replace(":","\:").Replace(".","\\.")) {
            $modelExists = $true
            break
        }
        # Also check without tag
        $baseName = ($selectedModel.Ollama -split ":")[0]
        if ($existing.name -match "^$baseName") {
            $modelExists = $true
            break
        }
    }
} catch {}

if ($modelExists) {
    Write-OK "Model '$($selectedModel.Ollama)' is already downloaded"
} else {
    Write-Info "Pulling $($selectedModel.Ollama) ($($selectedModel.SizeGB) GB)..."
    Write-Info "This may take several minutes depending on your connection."
    Write-Host ""

    & $ollamaCmd pull $selectedModel.Ollama 2>&1 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkGray
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Model download failed."
        Write-Info "Try manually: ollama pull $($selectedModel.Ollama)"
        Write-Info "Then re-run this setup or just run: relic-web"
        exit 1
    }

    Write-OK "Model downloaded successfully"
}

# ── Step 7: Create Launcher & Start ───────────────────────────

Write-Step 7 "Finalizing"

# Create desktop launcher
$desktopPath = [Environment]::GetFolderPath("Desktop")
$launcherPath = Join-Path $desktopPath "Launch RELIC.bat"

$launcherContent = @"
@echo off
title RELIC - Penetration Testing Framework
chcp 65001 >nul 2>&1
echo.
echo   Starting RELIC server...
echo   The web UI will open in your browser shortly.
echo   Press Ctrl+C to stop the server.
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8746"
relic-web
pause
"@

try {
    Set-Content -Path $launcherPath -Value $launcherContent -Encoding UTF8
    Write-OK "Desktop launcher created: Launch RELIC.bat"
} catch {
    Write-Warn "Could not create desktop launcher: $_"
}

# Summary
Write-Host ""
Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "   Model:    $($selectedModel.Name) ($($selectedModel.Tier))" -ForegroundColor White
Write-Host "   Hardware: ${ramGB} GB RAM / ${vramGB} GB VRAM" -ForegroundColor White
Write-Host "   Web UI:   http://127.0.0.1:8746" -ForegroundColor Cyan
Write-Host ""
Write-Host "   How to launch:" -ForegroundColor White
Write-Host "     - Double-click 'Launch RELIC.bat' on your Desktop" -ForegroundColor Gray
Write-Host "     - Or run 'relic-web' in any terminal" -ForegroundColor Gray
Write-Host ""
Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

# Ask to launch now
Write-Host "  Launching RELIC now..." -ForegroundColor Cyan

# Start relic-web in a new window
try {
    Start-Process cmd -ArgumentList "/k", "title RELIC Server & relic-web" -WindowStyle Normal
    Start-Sleep -Seconds 4
    Start-Process "http://127.0.0.1:8746"
    Write-OK "RELIC is running! Browser opened to http://127.0.0.1:8746"
} catch {
    Write-Warn "Could not auto-launch. Run 'relic-web' manually."
}

Write-Host ""
Write-Host "  Setup wizard complete. You can close this window." -ForegroundColor Green
Write-Host ""
