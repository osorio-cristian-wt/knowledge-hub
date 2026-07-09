#Requires -Version 5.1
<#
 Knowledge Hub - bootstrap de la PC de Daiana (RF-01, D-12).
 Un unico comando; despues de esto todo lo guia Claw conversando (skill onboarding):

   irm https://raw.githubusercontent.com/osorio-cristian-wt/knowledge-hub/main/install.ps1 | iex

 Idempotente: se puede volver a correr sin romper nada.
 NOTA: este archivo se mantiene en ASCII puro a proposito. PowerShell 5.1 lee
 los .ps1 sin BOM como ANSI y los caracteres tipograficos (comillas, guiones
 largos) rompen el parseo de strings.
#>
param(
    [string]$ClawhubHome = "C:\clawhub",
    [string]$RepoUrl = "https://github.com/osorio-cristian-wt/knowledge-hub.git"
)

$ErrorActionPreference = "Stop"

function Write-Paso($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Ensure-Tool {
    param([string]$Command, [string]$WingetId, [string]$Display)
    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        Write-Host "$Display ya instalado."
        return
    }
    Write-Host "Instalando $Display..."
    winget install --id $WingetId -e --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Display no quedo disponible en PATH. Cerrar y reabrir PowerShell y volver a correr este comando."
    }
}

Write-Paso "Knowledge Hub / OpenClaw - bootstrap"

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget no esta disponible. Actualizar 'Instalador de aplicacion' desde Microsoft Store y reintentar."
}

Write-Paso "1/6 Herramientas base"
Ensure-Tool -Command git    -WingetId Git.Git            -Display "Git"
Ensure-Tool -Command python -WingetId Python.Python.3.12 -Display "Python 3.12"
Ensure-Tool -Command node   -WingetId OpenJS.NodeJS.LTS  -Display "Node.js LTS"

Write-Paso "2/6 Repo del ecosistema (canal de updates, RF-03)"
$eco = Join-Path $ClawhubHome "ecosystem"
if (Test-Path (Join-Path $eco ".git")) {
    git -C $eco pull --ff-only
} else {
    New-Item -ItemType Directory -Force $ClawhubHome | Out-Null
    git clone $RepoUrl $eco
}

Write-Paso "3/6 Entorno Python del pipeline"
$venvPython = Join-Path $eco ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv (Join-Path $eco ".venv")
}
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r (Join-Path $eco "pipeline\requirements.txt")

Write-Paso "4/6 OpenClaw"
npm install -g openclaw@latest

Write-Paso "5/6 Skills del ecosistema -> OpenClaw"
# Junctions: git pull actualiza las skills sin reinstalar nada (RF-03).
$skillsDst = Join-Path $env:USERPROFILE ".openclaw\skills"
New-Item -ItemType Directory -Force $skillsDst | Out-Null
Get-ChildItem (Join-Path $eco "skills") -Directory | ForEach-Object {
    $link = Join-Path $skillsDst $_.Name
    if (-not (Test-Path $link)) {
        New-Item -ItemType Junction -Path $link -Target $_.FullName | Out-Null
        Write-Host "  skill enlazada: $($_.Name)"
    }
}

Write-Paso "6/6 Arrancar OpenClaw"
# NOTA (Cristian): verificar el subcomando exacto segun la version de OpenClaw instalada.
openclaw onboard

Write-Host @"

Listo. Siguiente paso: cuando OpenClaw este conectado al chat,
escribile al bot: 'arranca el onboarding' - Claw guia todo lo demas
(Drive, seleccion curada, primer sync). Ver skills/onboarding/SKILL.md.
"@ -ForegroundColor Green
