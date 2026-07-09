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

function Get-Py312Version {
    # No usamos 'python' del PATH: si hay otra instalacion de Python previa
    # (otra version, ej. 3.14, o el acceso directo de la Microsoft Store)
    # adelante en el PATH, 'python' puede terminar apuntando a esa y no a la
    # 3.12 que este script instala, rompiendo la instalacion de dependencias
    # en el paso 3/6 con errores de "no hay distribucion para tu entorno".
    # 'py' (Python Launcher for Windows) elige la version exacta por su
    # propio registro de instalaciones, sin depender del orden del PATH.
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { return $null }
    try {
        $out = [string](& py -3.12 --version 2>&1)
    } catch {
        return $null
    }
    if ($out -match '^Python 3\.12\.') { return $out.Trim() }
    return $null
}

Write-Paso "1/6 Herramientas base"
Ensure-Tool -Command git  -WingetId Git.Git           -Display "Git"
Ensure-Tool -Command node -WingetId OpenJS.NodeJS.LTS -Display "Node.js LTS"

$pyVersion = Get-Py312Version
if (-not $pyVersion) {
    Write-Host "Instalando Python 3.12..."
    winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $pyVersion = Get-Py312Version
    if (-not $pyVersion) {
        throw @"
No se encontro Python 3.12 a traves del Python Launcher (py -3.12) despues
de instalarlo. Para arreglarlo:

  1) Cerrar esta ventana de PowerShell, abrir una nueva (el PATH puede
     no haberse actualizado) y volver a correr este script.
  2) Si sigue fallando, reinstalar Python 3.12 desde
     https://www.python.org/downloads/ dejando tildada la opcion
     "py launcher" / "Install launcher for all users" durante la instalacion.
"@
    }
}
Write-Host "$pyVersion listo (via py -3.12)."

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
    py -3.12 -m venv (Join-Path $eco ".venv")
    if (-not (Test-Path $venvPython)) {
        throw "No se pudo crear el entorno virtual en '$venvPython'. Revisar el paso 1/6 (Python)."
    }
}
& $venvPython -m pip install --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo actualizar pip dentro del entorno virtual. Revisar la conexion a internet / proxy."
}
# Sin --quiet a proposito: si pip no puede resolver dependencias, esto
# muestra el detalle real del conflicto en vez de solo el resumen generico.
& $venvPython -m pip install -r (Join-Path $eco "pipeline\requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Fallo la instalacion de dependencias del pipeline. Revisar el detalle de pip mas arriba."
}

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
