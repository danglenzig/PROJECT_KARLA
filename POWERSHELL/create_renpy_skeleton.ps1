<#
.SYNOPSIS
    Creates a minimal, linted Ren'Py project skeleton for automated build pipelines.
.DESCRIPTION
    Generates project structure, essential directories, script.rpy, options.rpy, and runs lint validation.
.PARAMETER RenpyExe
    Path to renpy.exe (default: C:\renpy-sdk\renpy.exe)
.PARAMETER ProjectsDir
    Base directory for projects (default: C:\Users\Admin\Documents\VNs)
.PARAMETER GameName
    Technical project name, no spaces (default: AI_Generated_Skeleton)
.EXAMPLE
    .\create_renpy_skeleton.ps1 -GameName "MyProject" -ProjectsDir "D:\Projects"
#>

param(
    [string]$RenpyExe = "C:\renpy-sdk\renpy.exe",
    [string]$ProjectsDir = "C:\Users\Admin\Documents\VNs",
    [string]$GameName = "AI_Generated_Skeleton"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$FullProjectPath = Join-Path $ProjectsDir $GameName
$Prefix = "[RENPY-SKELETON]"

# 1. Validate Ren'Py executable
if (-not (Test-Path $RenpyExe)) {
    throw "$Prefix Ren'Py executable not found: $RenpyExe"
}

# 2. Check if project exists
if (Test-Path $FullProjectPath) {
    Write-Warning "$Prefix Project already exists at $FullProjectPath. Skipping creation."
    return
}

Write-Host "$Prefix Creating project at $FullProjectPath..." -ForegroundColor Cyan

# 3. Create project via Ren'Py launcher
& $RenpyExe . launcher create $GameName --projects $ProjectsDir

# 4. Ensure asset directories
$AssetDirs = @("images", "audio", "gui", "fonts", "characters")
foreach ($Dir in $AssetDirs) {
    $Path = Join-Path "$FullProjectPath\game" $Dir
    if (!(Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "$Prefix Created /game/$Dir" -ForegroundColor Gray
    }
}

# 5. Inject script.rpy (with pipeline hooks and documentation)
$ScriptContent = @'
# --- Pipeline Hooks ---
# bg <room/office/etc>: Generic backgrounds for image generation agents
# character <name> <expression>: Character sprites (neutral, happy, sad, etc.)
# Do not remove these tags - they are injection points for content agents.

# --- Characters ---
define p = Character("Player", color="#c8ffc8")
define n = Character("Narrator", color="#ffffff")

# --- Game Start ---
label start:
    # Scene tags act as hooks for image generation agents
    scene bg room 
    
    "The game skeleton has been successfully initialized."
    
    show character neutral at center
    
    p "I am ready for my dialogue and assets to be injected."
    
    return
'@
$ScriptPath = Join-Path "$FullProjectPath\game" "script.rpy"
Set-Content -Path $ScriptPath -Value $ScriptContent -Encoding UTF8
Write-Host "$Prefix script.rpy initialized with pipeline hooks." -ForegroundColor Green

# 6. Inject options.rpy
$OptionsContent = @'
define config.name = _("AI_Generated_Skeleton")
define gui.show_name = True
define config.version = "1.0"
define build.name = "ai_generated_skeleton"

# Enable sound channels
define config.has_sound = True
define config.has_music = True
define config.has_voice = True

# Window Management
define config.window = "auto"
define config.save_directory = "ai_generated_skeleton-saves"
'@
$OptionsPath = Join-Path "$FullProjectPath\game" "options.rpy"
Set-Content -Path $OptionsPath -Value $OptionsContent -Encoding UTF8
Write-Host "$Prefix options.rpy initialized." -ForegroundColor Green

# 7. Lint validation
Write-Host "$Prefix Running Ren'Py lint..." -ForegroundColor Yellow
& $RenpyExe $FullProjectPath lint

Write-Host "$Prefix Skeleton creation complete. Ready for content agents." -ForegroundColor Magenta
