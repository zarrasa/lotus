; Установщик Lotus (Inno Setup 6). Собирается из build.py: ISCC /DAppVersion=x.y.z installer.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E2F9C1A-4B7D-4F2E-9A51-7C3D2B8E1F40}
AppName=Lotus
AppVersion={#AppVersion}
AppVerName=Lotus {#AppVersion}
AppPublisher=Lotus
DefaultDirName={autopf}\Lotus
DefaultGroupName=Lotus
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=LotusSetup
SetupIconFile=icons\lotus.ico
UninstallDisplayIcon={app}\Lotus.exe
UninstallDisplayName=Lotus
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; при обновлении поверх — закрыть запущенный Lotus
CloseApplications=force
RestartApplications=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Lotus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Lotus"; Filename: "{app}\Lotus.exe"
Name: "{autodesktop}\Lotus"; Filename: "{app}\Lotus.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Lotus.exe"; Description: "{cm:LaunchProgram,Lotus}"; Flags: nowait postinstall skipifsilent shellexec
; автообновление ставит молча (/VERYSILENT) — после него запустить новую версию в трей
Filename: "{app}\Lotus.exe"; Parameters: "--updated"; Flags: nowait; Check: WizardSilent

[UninstallRun]
; остановить Lotus и его движки, убрать автозапуск
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Lotus.exe"; Flags: runhidden; RunOnceId: "KillLotus"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM winws.exe"; Flags: runhidden; RunOnceId: "KillWinws"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM goodbyedpi.exe"; Flags: runhidden; RunOnceId: "KillGdpi"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN Lotus /F"; Flags: runhidden; RunOnceId: "DelTask"

[UninstallDelete]
; настройки, логи и рабочие файлы движков
Type: filesandordirs; Name: "{userappdata}\Lotus"
