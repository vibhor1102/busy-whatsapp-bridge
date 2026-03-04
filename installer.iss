; Inno Setup Script for Busy Whatsapp Bridge
; This script creates a professional Windows installer
;
; This file is called by build-all.bat which passes /DMyAppVersion=X.X.X
; Do NOT compile this file directly — always use build-all.bat

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
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
LicenseFile=release_dist\LICENSE
OutputDir=.
OutputBaseFilename=BusyWhatsappBridge-v{#MyAppVersion}-Setup
SetupIconFile=release_dist\app.ico
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
; Use the staging directory prepared by build-all.bat
; This automatically includes all files/folders gathered in Step 2.5
Source: "release_dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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
