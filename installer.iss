; Inno Setup Script for Busy Whatsapp Bridge
; This script creates a professional Windows installer
; 
; To compile:
;   Option 1: Install Inno Setup, right-click this file → Compile
;   Option 2: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;
; For versioned builds, pass /DMyAppVersion=X.X.X to ISCC

#ifndef MyAppVersion
  ; Read version from app/version.py if not passed via /D flag
  #define VersionFile FileOpen("app\version.py")
  #define VersionLine ""
  #define MyAppVersion "0.0.0-fallback"
  #if VersionFile
    #define VersionContent FileRead(VersionFile)
    ; Fallback: version will be set by build-installer.bat via /D flag
    #expr FileClose(VersionFile)
  #endif
#endif

#define MyAppName "Busy Whatsapp Bridge"
#define MyAppPublisher "vibhor1102"
#define MyAppURL "https://github.com/vibhor1102/busy-whatsapp-bridge"
#define MyAppExeName "BusyWhatsappBridge.exe"

[Setup]
; Application info
AppId={{BUSYWHATSAPPBRIDGE-2024-PROD-V1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
LicenseFile=LICENSE
OutputDir=.
OutputBaseFilename=BusyWhatsappBridge-v{#MyAppVersion}-Setup
SetupIconFile=app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\app.ico
SetupLogging=yes

; Version info for the installer itself
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "autostart"; Description: "Start automatically on Windows login"; GroupDescription: "Startup options:"; Flags: checkedonce

[Dirs]
; Only apply users-modify for user installs (not admin installs)
Name: "{app}"; Permissions: users-modify; Check: not IsAdminInstallMode

[Files]
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

; Main executable launcher
Source: "BusyWhatsappBridge.exe"; DestDir: "{app}"; Flags: ignoreversion

; Application source code
Source: "app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc"

; Production launcher and entry point
Source: "run.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "Start-Gateway.py"; DestDir: "{app}"; Flags: ignoreversion

; Baileys server (Node.js) - exclude auth dir and logs
Source: "baileys-server\server.js"; DestDir: "{app}\baileys-server"; Flags: ignoreversion
Source: "baileys-server\baileys-client.js"; DestDir: "{app}\baileys-server"; Flags: ignoreversion
Source: "baileys-server\package.json"; DestDir: "{app}\baileys-server"; Flags: ignoreversion
Source: "baileys-server\package-lock.json"; DestDir: "{app}\baileys-server"; Flags: ignoreversion
Source: "baileys-server\node_modules\*"; DestDir: "{app}\baileys-server\node_modules"; Flags: ignoreversion recursesubdirs createallsubdirs

; Bundled Python runtime
Source: "python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; Virtual environment with all dependencies
Source: "venv\*"; DestDir: "{app}\venv"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.pyc,__pycache__"

; Pre-built dashboard (dist only - not source code)
Source: "dashboard-react\dist\*"; DestDir: "{app}\dashboard-react\dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; Setup and management scripts
Source: "setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "manage-task.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "configure-firewall.bat"; DestDir: "{app}"; Flags: ignoreversion

; Application icon
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

; Configuration templates
Source: "conf.json.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "USER-GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcuts
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{autoprograms}\{#MyAppName}\Manage Auto-Start"; Filename: "{app}\manage-task.bat"
Name: "{autoprograms}\{#MyAppName}\Configure Firewall"; Filename: "{app}\configure-firewall.bat"; Check: IsAdminInstallMode
Name: "{autoprograms}\{#MyAppName}\User Guide"; Filename: "{app}\USER-GUIDE.md"

; Desktop shortcut (optional, user can choose during install)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
; Post-installation: Run setup.py to configure the application
; This runs silently and sets up the virtual environment and AppData
Filename: "{app}\python\python.exe"; Parameters: "{app}\setup.py --silent"; \
    Description: "Configuring application..."; Flags: runhidden waituntilterminated; \
    StatusMsg: "Setting up Busy Whatsapp Bridge (this may take a few minutes)..."

; Launch the application after installation (optional, ask user)
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch Busy Whatsapp Bridge"; Flags: postinstall nowait skipifsilent unchecked

; Configure auto-start with Windows if selected
Filename: "{app}\manage-task.bat"; Parameters: "install"; \
    Description: "Configure auto-start"; Flags: runhidden; Tasks: autostart

[UninstallRun]
; Remove Task Scheduler task if it exists
Filename: "schtasks"; Parameters: "/delete /tn ""BusyWhatsappBridge_AutoStart"" /f"; \
    RunOnceId: "RemoveTask"; Flags: runhidden

; Run uninstall script before removing files
Filename: "{app}\python\python.exe"; Parameters: "{app}\uninstall.py --silent"; \
    RunOnceId: "CleanUp"; Flags: runhidden

[Code]
// Check if previous version exists and handle upgrade
function InitializeSetup(): Boolean;
begin
  if RegKeyExists(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\BusyWhatsappBridge_is1') or
     RegKeyExists(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\BusyWhatsappBridge_is1') then
  begin
    Log('Previous installation detected - performing upgrade');
  end;
  
  Result := true;
end;

// Show completion message
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('Installation completed successfully');
  end;
end;
