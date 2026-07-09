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

function Test-PythonReal {
    # Windows agrega un acceso directo en WindowsApps (python.exe / python3.exe)
    # que aparece en Get-Command pero solo redirige a la Microsoft Store.
    # Si no se detecta esto, el script cree que Python esta instalado y
    # despues falla en silencio al crear el venv (paso 3/6).
    param([string]$Command)
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { return $false }
    try {
        $out = & $Command --version 2>&1
    } catch {
        return $false
    }
    return [string]$out -match '^Python \d'
}

Write-Paso "1/6 Herramientas base"
Ensure-Tool -Command git  -WingetId Git.Git           -Display "Git"
Ensure-Tool -Command node -WingetId OpenJS.NodeJS.LTS -Display "Node.js LTS"

if (Test-PythonReal python) {
    Write-Host "Python 3.12 ya instalado."
} else {
    Write-Host "Instalando Python 3.12..."
    winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (-not (Test-PythonReal python)) {
        throw @"
Python quedo instalado pero 'python' en PATH sigue apuntando al acceso
directo de la Microsoft Store (comun en Windows 10). Para arreglarlo:

  1) Abrir Configuracion > Aplicaciones > Aplicaciones y caracteristicas
  2) Bajar hasta el link "Alias de ejecucion de aplicaciones" y entrar
  3) Apagar las llaves de "python.exe" y "python3.exe"
  4) Cerrar esta ventana de PowerShell, abrir una nueva y volver a
     correr este script.
"@
    }
}

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
