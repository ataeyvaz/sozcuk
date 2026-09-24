; Sözcük kurulum paketi (Inno Setup 6.5+; indirme ve arşiv açma için)
; Derleme:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\sozcuk.iss
; Önce PyInstaller paketi hazırlanmalı:  .venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm
;
; Pakette yalnızca Türkçe ↔ İngilizce çeviri vardır. Diğer diller "Özel" kurulumda işaretlenirse kurulum
; sırasında Argos Translate'in sunucusundan indirilip {app}\diller klasörüne açılır; Sözcük orayı okur.
; Adresler ve boyutlar Argos paket dizininden alındı (https://github.com/argosopentech/argospm-index).

#define AppName "Sözcük"
#define AppVersion "1.2"
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
; .argosmodel (zip) arşivlerini açmak için
ArchiveExtraction=full

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Types]
Name: "standart"; Description: "Standart kurulum (Türkçe ↔ İngilizce çeviri)"
Name: "ozel"; Description: "Özel kurulum (ek çeviri dilleri seçilebilir)"; Flags: iscustom

[Components]
Name: "program"; Description: "Sözcük (Türkçe ↔ İngilizce çeviri dahil)"; Types: standart ozel; Flags: fixed
Name: "diller"; Description: "Ek çeviri dilleri — kurulum sırasında internetten indirilir"; Types: ozel
Name: "diller\de"; Description: "Türkçe ↔ Almanca"; Types: ozel
Name: "diller\it"; Description: "Türkçe ↔ İtalyanca"; Types: ozel
Name: "diller\es"; Description: "Türkçe ↔ İspanyolca"; Types: ozel
Name: "diller\fr"; Description: "Türkçe ↔ Fransızca"; Types: ozel
Name: "diller\ru"; Description: "Türkçe ↔ Rusça"; Types: ozel
Name: "diller\zh"; Description: "Türkçe ↔ Çince"; Types: ozel
Name: "diller\ja"; Description: "Türkçe ↔ Japonca"; Types: ozel
Name: "diller\hi"; Description: "Türkçe ↔ Hintçe"; Types: ozel
Name: "diller\ko"; Description: "Türkçe ↔ Korece"; Types: ozel
Name: "diller\ar"; Description: "Türkçe ↔ Arapça"; Types: ozel
Name: "diller\pt"; Description: "Türkçe ↔ Portekizce"; Types: ozel

[Tasks]
Name: "desktopicon"; Description: "Masaüstünde kısayol oluştur"; GroupDescription: "Ek kısayollar:"
Name: "docxassoc"; Description: "Word belgelerini (.docx) Sözcük ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Flags: unchecked

[InstallDelete]
; eski sürümden kalanlar (1.0 torch/spacy ve gömülü dil paketleriyle ~2 GB idi): temiz kurulum
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Sozcuk\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Sozcuk\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ek çeviri dilleri (yalnızca seçilirse indirilir). DestName ".zip" olmalı: arşiv türü uzantıdan tanınıyor
Source: "https://argos-net.com/v1/translate-en_de-1_3.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_de-1_3.zip"; ExternalSize: 150508297; Components: diller\de; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-de_en-1_3.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-de_en-1_3.zip"; ExternalSize: 150512831; Components: diller\de; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_it-1_0.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_it-1_0.zip"; ExternalSize: 87660780; Components: diller\it; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-it_en-1_0.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-it_en-1_0.zip"; ExternalSize: 87190224; Components: diller\it; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_es-1_0.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_es-1_0.zip"; ExternalSize: 87503191; Components: diller\es; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-es_en-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-es_en-1_9.zip"; ExternalSize: 285208831; Components: diller\es; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_fr-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_fr-1_9.zip"; ExternalSize: 65472327; Components: diller\fr; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-fr_en-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-fr_en-1_9.zip"; ExternalSize: 66585033; Components: diller\fr; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ru-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_ru-1_9.zip"; ExternalSize: 195746693; Components: diller\ru; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ru_en-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-ru_en-1_9.zip"; ExternalSize: 156239112; Components: diller\ru; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_zh-1_9.zip"; ExternalSize: 70743021; Components: diller\zh; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-zh_en-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-zh_en-1_9.zip"; ExternalSize: 74481402; Components: diller\zh; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ja-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_ja-1_1.zip"; ExternalSize: 120470284; Components: diller\ja; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ja_en-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-ja_en-1_1.zip"; ExternalSize: 117155716; Components: diller\ja; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_hi-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_hi-1_1.zip"; ExternalSize: 106752178; Components: diller\hi; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-hi_en-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-hi_en-1_1.zip"; ExternalSize: 102381771; Components: diller\hi; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ko-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_ko-1_1.zip"; ExternalSize: 120789009; Components: diller\ko; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ko_en-1_1.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-ko_en-1_1.zip"; ExternalSize: 118852077; Components: diller\ko; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ar-1_0.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_ar-1_0.zip"; ExternalSize: 88502631; Components: diller\ar; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ar_en-1_0.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-ar_en-1_0.zip"; ExternalSize: 81869670; Components: diller\ar; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_pt-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-en_pt-1_9.zip"; ExternalSize: 66179184; Components: diller\pt; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-pt_en-1_9.argosmodel"; DestDir: "{app}\diller"; \
    DestName: "translate-pt_en-1_9.zip"; ExternalSize: 69447231; Components: diller\pt; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion

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
Type: filesandordirs; Name: "{app}\diller"
