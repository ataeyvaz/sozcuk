; Sözcük kurulum paketi (Inno Setup 6)
; Derleme:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\sozcuk.iss
; Önce PyInstaller paketi hazırlanmalı:  .venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm

#define AppName "Sözcük"
#define AppVersion "1.0"
#define AppPublisher "Usta ve Ata"
#define AppExe "Sozcuk.exe"

[Setup]
AppId={{6E1C0A9C-2E5B-4C9E-9C4B-5F2E0B9A7C11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Sozcuk-{#AppVersion}-kurulum
SetupIconFile=..\sozcuk.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
; Dil paketleriyle birlikte yaklaşık 2 GB yer gerekir
ExtraDiskSpaceRequired=209715200

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstünde kısayol oluştur"; GroupDescription: "Ek kısayollar:"
Name: "docxassoc"; Description: "Word belgelerini (.docx) Sözcük ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Flags: unchecked

[Files]
Source: "..\dist\Sozcuk\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Sozcuk\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; "Birlikte aç" listesinde görünsün
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".docx"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".doc"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".rtf"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".odt"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".txt"; ValueData: ""
; İsteğe bağlı: .docx dosyalarını doğrudan Sözcük açsın
Root: HKA; Subkey: "Software\Classes\.docx\OpenWithProgids"; ValueType: string; \
    ValueName: "Sozcuk.Belge"; ValueData: ""; Tasks: docxassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge"; ValueType: string; ValueName: ""; \
    ValueData: "Word Belgesi (Sözcük)"; Tasks: docxassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge\DefaultIcon"; ValueType: string; ValueName: ""; \
    ValueData: "{app}\{#AppExe},0"; Tasks: docxassoc
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge\shell\open\command"; ValueType: string; ValueName: ""; \
    ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: docxassoc

[Run]
Filename: "{app}\{#AppExe}"; Description: "Sözcük'ü şimdi çalıştır"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
