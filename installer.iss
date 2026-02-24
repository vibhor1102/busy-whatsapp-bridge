; Inno Setup Script for Busy Whatsapp Bridge
; This script creates a professional Windows installer
; Compile with: iscc installer.iss

#define MyAppName "Busy Whatsapp Bridge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Busy Software Solutions"
#define MyAppURL "https://github.com/yourusername/busy-whatsapp-bridge"
#define MyAppExeName "Start-Gateway.bat"

[Setup]
AppId={{BUSYWHATSAPPBRIDGE-2024-PROD}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=.
OutputBaseFilename=BusyWhatsappBridge-v{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
UninstallDisplayIcon={app}\app\icon.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically on Windows login (Task Scheduler)"; GroupDescription: "Startup options:"

[Files]
; Application source code
Source: "app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs

; Baileys server
Source: "baileys-server\*"; DestDir: "{app}\baileys-server"; Flags: ignoreversion recursesubdirs

; Bundled Python
Source: "python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs

; Virtual environment
Source: "venv\*"; DestDir: "{app}\venv"; Flags: ignoreversion recursesubdirs

; Dashboard
Source: "dashboard\*"; DestDir: "{app}\dashboard"; Flags: ignoreversion recursesubdirs

; Python scripts
Source: "setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "Start-Gateway.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "migrate-to-appdata.py"; DestDir: "{app}"; Flags: ignoreversion

; Batch scripts
Source: "manage-task.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "configure-firewall.bat"; DestDir: "{app}"; Flags: ignoreversion

; Configuration templates
Source: "conf.json.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "USER-GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tray"
Name: "{autoprograms}\{#MyAppName} (Console)"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tray"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName}\Manage Auto-Start"; Filename: "{app}\manage-task.bat"
Name: "{autoprograms}\{#MyAppName}\Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\python\python.exe"; Parameters: ""