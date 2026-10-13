; trace.iss — 윈도우 설치 파일 (Inno Setup 6 · v0.1 · 10/13).  직접 부르지 말고 build.py 로.
; 관리자 권한 없이 내 계정에 설치한다 (%LOCALAPPDATA%\Programs\Trace). 기록은 설치 폴더 밖 %LOCALAPPDATA%\Trace\data 라
; 새 버전을 덮어 깔거나 지워도 남는다.
; ★ AppId 는 바꾸지 않는다 — 바꾸면 윈도우가 다른 프로그램으로 보고 두 개가 깔린다.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{BCAA30B3-9B21-4163-99DF-09BD84685FF9}
AppName=Trace
AppVersion={#AppVersion}
AppVerName=Trace {#AppVersion}
AppPublisher=Trace (창의프로젝트1)
AppPublisherURL=https://trace-server-8aa0.onrender.com/download
DefaultDirName={localappdata}\Programs\Trace
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename=Trace-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Trace.exe
UninstallDisplayName=Trace
CloseApplications=yes
#ifdef IconFile
SetupIconFile={#IconFile}
#endif

[Languages]
#ifdef Korean
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#else
Name: "english"; MessagesFile: "compiler:Default.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 Trace 아이콘 만들기"

[InstallDelete]
; 지난 버전의 묶음을 지우고 새로 — 남은 옛 파일이 섞이지 않게
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Trace"; Filename: "{app}\Trace.exe"
Name: "{userprograms}\Trace 기록 시작"; Filename: "{app}\Trace.exe"; Parameters: "record"; IconFilename: "{app}\Trace.exe"
Name: "{userdesktop}\Trace"; Filename: "{app}\Trace.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Trace.exe"; Description: "Trace 열기"; Flags: nowait postinstall skipifsilent
