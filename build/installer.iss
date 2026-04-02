; Estate OS — Windows Installer Script
; Compiled with Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
; Run build_installer.bat to compile this automatically.

#define MyAppName      "Estate OS"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Estate OS"
#define MyAppExeName   "EstateOS.exe"
#define MyAppIcon      "..\icons\estate-capture-windows.ico"

[Setup]
AppId={{D4F8A3B1-9C2E-4F7A-8D1B-3E5C9A7F2B4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments=Personal Estate Planning — Private and Local
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=.\output
OutputBaseFilename=EstateOS_Setup
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=no
AllowNoIcons=yes
VersionInfoVersion=1.0.0.0
VersionInfoCompany=Estate OS
VersionInfoDescription=Personal Estate Planning Application

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Files]
Source: ".\dist\EstateOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; \
      Filename: "{app}\{#MyAppExeName}"; \
      IconFilename: "{app}\{#MyAppExeName}"; \
      Comment: "Personal Estate Plan — Private and Local"

Name: "{autodesktop}\{#MyAppName}"; \
      Filename: "{app}\{#MyAppExeName}"; \
      IconFilename: "{app}\{#MyAppExeName}"; \
      Comment: "Personal Estate Plan — Private and Local"; \
      Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
          Description: "Launch Estate OS now"; \
          Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave the profiles folder so answers are not deleted on uninstall
; Type: filesandordirs; Name: "{app}\profiles"

[Code]
// Show a friendly welcome message before the wizard starts
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install Estate OS on your computer.' + #13#10 + #13#10 +
    'Estate OS is a private estate planning tool. ' +
    'Everything you enter stays on this computer — ' +
    'nothing is sent to the internet.' + #13#10 + #13#10 +
    'Click Next to continue.';
end;
