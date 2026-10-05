# windows-fix-vbcable.ps1
# Vocalis AI - VB-CABLE system check and repair (run as Administrator)
#
# What it does:
#   1. Checks that VB-CABLE is installed and its endpoints are present.
#   2. Resets the VB-CABLE "Internal SR" to 48000 Hz (the recommended value;
#      anything else forces extra sample-rate conversion and adds latency).
#      NOTE: the running driver picks this up after a reboot (or after applying
#      it in the VB-CABLE Control Panel, which must itself run as admin).
#   3. Prints the installed driver version and, if it is old (pre-3.x, e.g.
#      the 2015 1.0.3.5), recommends installing the current Driver Pack.
#   4. Optionally restarts the Windows Audio services so endpoint state
#      (newly installed / re-enabled devices) refreshes cleanly.
#
# Usage: right-click PowerShell -> Run as Administrator, then:
#   powershell -ExecutionPolicy Bypass -File tools\windows-fix-vbcable.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Continue"
$vbKey = "HKLM:\SOFTWARE\VB-Audio\Cable"
$RecommendedSR = 48000

Write-Host "== Vocalis AI - VB-CABLE check & fix ==" -ForegroundColor Cyan

# --- 1. Is VB-CABLE installed? --------------------------------------------
$cable = Get-PnpDevice -Class MEDIA -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like "*VB-Audio*" }
$endpoints = Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like "*VB-Audio*" -or $_.FriendlyName -like "*CABLE*" }

if (-not $cable -and -not $endpoints) {
    Write-Host "[ERROR] No VB-Audio/VB-CABLE devices found." -ForegroundColor Red
    Write-Host "  Install it from https://vb-audio.com/Cable/ (run VBCABLE_Setup_x64.exe as administrator), then REBOOT."
    exit 1
}
Write-Host "[OK] VB-CABLE device(s) present:" -ForegroundColor Green
$cable | ForEach-Object { Write-Host "     $($_.FriendlyName) ($($_.Status))" }
$endpoints | ForEach-Object { Write-Host "     endpoint: $($_.FriendlyName) ($($_.Status))" }

$disabled = @($endpoints + $cable) | Where-Object { $_.Status -ne "OK" }
if ($disabled.Count -gt 0) {
    Write-Host "[WARN] Some VB-CABLE devices are not active ($($disabled.Count))." -ForegroundColor Yellow
    Write-Host "       Enable them in the Sound control panel (mmsys.cpl) - right-click -> Enable."
}

# --- 2. Driver version ------------------------------------------------------
$driverVersion = $null
$classKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}"
if (Test-Path $classKey) {
    Get-ChildItem $classKey -ErrorAction SilentlyContinue | ForEach-Object {
        $desc = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DriverDesc
        if ($desc -like "*VB-Audio*") {
            $v = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DriverVersion
            if ($v) { $script:driverVersion = "$v" }
        }
    }
}
if ($driverVersion) {
    Write-Host ""
    Write-Host "Driver version: $driverVersion"
    $major = ($driverVersion -split "\.")[0]
    if ([int]$major -lt 3) {
        Write-Host "[WARN] This is an old (pre-2024) driver. Windows 10/11 (especially 24H2+) work best with Driver Pack 45+." -ForegroundColor Yellow
        Write-Host "       Download: https://vb-audio.com/Cable/ -> run setup as administrator -> REBOOT."
    } else {
        Write-Host "[OK] Driver version looks current." -ForegroundColor Green
    }
}

# --- 3. Internal SR ----------------------------------------------------------
if (Test-Path $vbKey) {
    $sr = (Get-ItemProperty $vbKey -ErrorAction SilentlyContinue).VBAudioCableWDM_SR
    $lat = (Get-ItemProperty $vbKey -ErrorAction SilentlyContinue).VBAudioCableWDM
    Write-Host ""
    Write-Host "VB-CABLE Internal SR : $sr Hz (recommended: $RecommendedSR Hz)"
    Write-Host "VB-CABLE Max Latency : $lat samples (default 7168)"
    if ($sr -and [int]$sr -ne $RecommendedSR) {
        Write-Host "[FIX] Setting Internal SR to $RecommendedSR Hz..." -ForegroundColor Yellow
        Set-ItemProperty -Path $vbKey -Name "VBAudioCableWDM_SR" -Value $RecommendedSR -Type DWord
        Write-Host "      Registry updated. The running driver applies it after a REBOOT" -ForegroundColor Yellow
        Write-Host "      (or immediately if you open the VB-CABLE Control Panel as admin and re-apply)." -ForegroundColor Yellow
        $script:needReboot = $true
    } else {
        Write-Host "[OK] Internal SR already $RecommendedSR Hz." -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] Registry key $vbKey not found - VB-CABLE may be installed per-user or damaged." -ForegroundColor Yellow
}

# --- 4. Optional: restart audio services -------------------------------------
Write-Host ""
$answer = Read-Host "Restart Windows Audio services now? (briefly stops all audio) [y/N]"
if ($answer -match "^[Yy]") {
    Write-Host "Restarting Audiosrv and AudioEndpointBuilder..."
    Restart-Service AudioEndpointBuilder -Force
    Restart-Service Audiosrv -Force
    Write-Host "[OK] Audio services restarted." -ForegroundColor Green
    Write-Host "     Re-enumerate devices by restarting apps (or stopping/starting audio in Vocalis)."
}

# --- 5. Checklist -------------------------------------------------------------
Write-Host ""
Write-Host "== Checklist for Vocalis AI routing ==" -ForegroundColor Cyan
Write-Host " 1. Vocalis: AUDIO = server, Output = cable PLAYBACK side ('Speakers (VB-Audio Virtual Cable)' / 'CABLE Input')."
Write-Host " 2. Vocalis: S.R. = 48000; input and output on the same API (Windows WASAPI recommended)."
Write-Host " 3. mmsys.cpl -> both cable devices -> Advanced -> '2 channel, 16 bit, 48000 Hz' (set while apps are closed)."
Write-Host " 4. Discord: Input Device = 'CABLE Output (VB-Audio Virtual Cable)'; disable Noise Suppression + Echo"
Write-Host "    Cancellation; disable automatic input sensitivity. Error 3002 = the cable is receiving silence."
Write-Host " 5. Windows Settings -> Sound -> check the cable devices are not muted and level is 100%."
if ($needReboot) {
    Write-Host ""
    Write-Host "REBOOT REQUIRED to apply the Internal SR change." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Done."
