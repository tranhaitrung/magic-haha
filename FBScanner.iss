; ============================================================
;  FB Affiliate Scanner - Inno Setup Script
;  Build: iscc FBScanner.iss
;  Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; ============================================================

#define AppName      "FB Affiliate Scanner"
#define AppVersion   "1.0"
#define AppPublisher "SSO Vietnam"
#define AppExeName   "launcher.bat"
#define InstallDir   "{autopf}\FBScanner"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://ecomobi.com
AppSupportURL=https://ecomobi.com
AppUpdatesURL=https://ecomobi.com
DefaultDirName={#InstallDir}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=FBScanner_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Icon cua installer
; SetupIconFile=assets\icon.ico
UninstallDisplayName={#AppName}
; Khong can quyen admin
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tao shortcut tren Desktop"; GroupDescription: "Shortcut:"; Flags: checked

[Files]
; Source code
Source: "gui.py";             DestDir: "{app}"; Flags: ignoreversion
Source: "fb_aff_scanner.py";  DestDir: "{app}"; Flags: ignoreversion
Source: "config.json";        DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt";   DestDir: "{app}"; Flags: ignoreversion
Source: "launcher.bat";       DestDir: "{app}"; Flags: ignoreversion
Source: "setup_env.bat";      DestDir: "{app}"; Flags: ignoreversion

; Source modules
Source: "src\*";              DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs

; Python embedded + dependencies + Chromium (phai chay setup_env.bat truoc)
Source: "python\*";           DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\data\inbox"
Name: "{app}\data\processing"
Name: "{app}\data\output"
Name: "{app}\data\archive"
Name: "{app}\data\error"
Name: "{app}\logs"

[Icons]
; Start Menu
Name: "{group}\{#AppName}";         Filename: "{app}\launcher.bat"; IconFilename: "{app}\python\python.exe"; WorkingDir: "{app}"
Name: "{group}\Ket qua Scan";        Filename: "{app}\data\output";  WorkingDir: "{app}"
Name: "{group}\Gỡ cai {#AppName}";  Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#AppName}";   Filename: "{app}\launcher.bat"; IconFilename: "{app}\python\python.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Mo thu muc ket qua sau khi cai xong (tuy chon)
Filename: "{app}\data\output"; Description: "Mo thu muc ket qua"; Flags: postinstall shellexec skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\python\__pycache__"
Type: filesandordirs; Name: "{app}\src\__pycache__"
