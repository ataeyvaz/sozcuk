; Eagle Office kurulum paketi: Sözcük (kelime işlemci) + Tabcel (hesap tablosu) tek kurulumda (Inno Setup 6.5+).
; Derleme (Sözcük proje klasöründen):  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\eagle-office.iss
; Hızlı deneme (sıkıştırmasız, çıktı dist'e değil verilen klasöre):  ISCC.exe /DHIZLI=1 /O<klasör> kurulum\eagle-office.iss
;
; ÖNCE iki PyInstaller çıktısı güncel olmalı:
;   Sözcük:  (Sözcük klasöründe)  .venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm   -> dist\Sozcuk
;   Tabcel:  (Tabcel klasöründe)  .venv\Scripts\python.exe -m PyInstaller tabcel.spec --noconfirm   -> ..\tabcel\dist\Tabcel
; Görseller (logo): araclar\logo_hazirla.py <logo.png>  ->  kurulum\gorsel\ (yoksa Sözcük simgesi kullanılır).
;
; Kurulumda iki uygulama da varsayılan seçilidir; kullanıcı birini kaldırabilir ya da Cancel ile çıkabilir.
; Önceki AYRI kurulumlar (Sözcük 1.x, Tabcel 0.x) bulunursa çift kayıt olmasın diye kaldırma önerilir;
; belgeler ve ayarlar (%APPDATA%) silinmez.
; Ek çeviri dilleri Sözcük'ün "Özel kurulum"unda seçilebilir (kurulum sırasında internetten indirilir).

#define SuiteName "Eagle Office"
#define SuiteVersion "1.0"
#define AppPublisher "Eagle Office"
#define AppContact "mailto:ataeyvaz@gmail.com"
#define SozcukName "Sözcük"
#define SozcukExe "Sozcuk.exe"
#define TabcelName "Tabcel"
#define TabcelExe "Tabcel.exe"
#define SozcukDist "..\dist\Sozcuk"
#define TabcelDist "..\..\tabcel\dist\Tabcel"
#define Gorsel "gorsel"

[Setup]
AppId={{7D4A2B16-3C8E-4E55-A1F0-9B6C5E2D8A71}
AppName={#SuiteName}
AppVersion={#SuiteVersion}
AppVerName={#SuiteName} {#SuiteVersion}
AppPublisher={#AppPublisher}
AppSupportURL={#AppContact}
AppContact={#AppContact}
DefaultDirName={autopf}\{#SuiteName}
DefaultGroupName={#SuiteName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=EagleOffice-{#SuiteVersion}-kurulum
#ifexist "gorsel\eagle-office.ico"
SetupIconFile={#Gorsel}\eagle-office.ico
UninstallDisplayIcon={app}\eagle-office.ico
#else
SetupIconFile=..\sozcuk.ico
UninstallDisplayIcon={app}\Sözcük\{#SozcukExe}
#endif
#ifexist "gorsel\sihirbaz-buyuk.bmp"
WizardImageFile={#Gorsel}\sihirbaz-buyuk.bmp
#endif
#ifexist "gorsel\sihirbaz-kucuk.bmp"
WizardSmallImageFile={#Gorsel}\sihirbaz-kucuk.bmp
#endif
#ifdef HIZLI
Compression=none
SolidCompression=no
#else
Compression=lzma2/max
SolidCompression=yes
#endif
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
; .argosmodel (zip) arşivlerini açmak için
ArchiveExtraction=full

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Types]
Name: "tam"; Description: "Eagle Office — Sözcük ve Tabcel (önerilen)"
Name: "yalnizsozcuk"; Description: "Yalnızca Sözcük (kelime işlemci)"
Name: "yalniztabcel"; Description: "Yalnızca Tabcel (hesap tablosu)"
Name: "ozel"; Description: "Özel kurulum (uygulamaları ve ek çeviri dillerini seçin)"; Flags: iscustom

[Components]
Name: "sozcuk"; Description: "Sözcük — Türkçe kelime işlemci (Türkçe ↔ İngilizce çeviri dahil)"; Types: tam yalnizsozcuk ozel
Name: "sozcuk\diller"; Description: "Ek çeviri dilleri — kurulum sırasında internetten indirilir"; Types: ozel
Name: "sozcuk\diller\de"; Description: "Türkçe ↔ Almanca"; Types: ozel
Name: "sozcuk\diller\it"; Description: "Türkçe ↔ İtalyanca"; Types: ozel
Name: "sozcuk\diller\es"; Description: "Türkçe ↔ İspanyolca"; Types: ozel
Name: "sozcuk\diller\fr"; Description: "Türkçe ↔ Fransızca"; Types: ozel
Name: "sozcuk\diller\ru"; Description: "Türkçe ↔ Rusça"; Types: ozel
Name: "sozcuk\diller\zh"; Description: "Türkçe ↔ Çince"; Types: ozel
Name: "sozcuk\diller\ja"; Description: "Türkçe ↔ Japonca"; Types: ozel
Name: "sozcuk\diller\hi"; Description: "Türkçe ↔ Hintçe"; Types: ozel
Name: "sozcuk\diller\ko"; Description: "Türkçe ↔ Korece"; Types: ozel
Name: "sozcuk\diller\ar"; Description: "Türkçe ↔ Arapça"; Types: ozel
Name: "sozcuk\diller\pt"; Description: "Türkçe ↔ Portekizce"; Types: ozel
Name: "tabcel"; Description: "Tabcel — Türkçe hesap tablosu"; Types: tam yalniztabcel ozel

[Tasks]
Name: "sozcukdesktop"; Description: "Masaüstünde Sözcük kısayolu oluştur"; GroupDescription: "Ek kısayollar:"; Components: sozcuk
Name: "tabceldesktop"; Description: "Masaüstünde Tabcel kısayolu oluştur"; GroupDescription: "Ek kısayollar:"; Components: tabcel
Name: "docxassoc"; Description: "Word belgelerini (.docx) Sözcük ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Components: sozcuk; Flags: unchecked
Name: "xlsxassoc"; Description: "Excel çalışma kitaplarını (.xlsx) Tabcel ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Components: tabcel; Flags: unchecked
Name: "csvassoc"; Description: "CSV dosyalarını (.csv) Tabcel ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Components: tabcel; Flags: unchecked

[InstallDelete]
; eski sürümden kalanlar: temiz kurulum
Type: filesandordirs; Name: "{app}\Sözcük\_internal"; Components: sozcuk
Type: filesandordirs; Name: "{app}\Tabcel\_internal"; Components: tabcel

[Files]
#ifexist "gorsel\eagle-office.ico"
Source: "{#Gorsel}\eagle-office.ico"; DestDir: "{app}"; Flags: ignoreversion
#endif
Source: "{#SozcukDist}\{#SozcukExe}"; DestDir: "{app}\Sözcük"; Components: sozcuk; Flags: ignoreversion
Source: "{#SozcukDist}\_internal\*"; DestDir: "{app}\Sözcük\_internal"; Components: sozcuk; \
    Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#TabcelDist}\{#TabcelExe}"; DestDir: "{app}\Tabcel"; Components: tabcel; Flags: ignoreversion
Source: "{#TabcelDist}\_internal\*"; DestDir: "{app}\Tabcel\_internal"; Components: tabcel; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; Ek çeviri dilleri (yalnızca seçilirse indirilir). DestName ".zip" olmalı: arşiv türü uzantıdan tanınıyor
Source: "https://argos-net.com/v1/translate-en_de-1_3.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_de-1_3.zip"; ExternalSize: 150508297; Components: sozcuk\diller\de; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-de_en-1_3.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-de_en-1_3.zip"; ExternalSize: 150512831; Components: sozcuk\diller\de; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_it-1_0.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_it-1_0.zip"; ExternalSize: 87660780; Components: sozcuk\diller\it; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-it_en-1_0.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-it_en-1_0.zip"; ExternalSize: 87190224; Components: sozcuk\diller\it; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_es-1_0.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_es-1_0.zip"; ExternalSize: 87503191; Components: sozcuk\diller\es; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-es_en-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-es_en-1_9.zip"; ExternalSize: 285208831; Components: sozcuk\diller\es; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_fr-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_fr-1_9.zip"; ExternalSize: 65472327; Components: sozcuk\diller\fr; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-fr_en-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-fr_en-1_9.zip"; ExternalSize: 66585033; Components: sozcuk\diller\fr; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ru-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_ru-1_9.zip"; ExternalSize: 195746693; Components: sozcuk\diller\ru; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ru_en-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-ru_en-1_9.zip"; ExternalSize: 156239112; Components: sozcuk\diller\ru; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_zh-1_9.zip"; ExternalSize: 70743021; Components: sozcuk\diller\zh; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-zh_en-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-zh_en-1_9.zip"; ExternalSize: 74481402; Components: sozcuk\diller\zh; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ja-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_ja-1_1.zip"; ExternalSize: 120470284; Components: sozcuk\diller\ja; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ja_en-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-ja_en-1_1.zip"; ExternalSize: 117155716; Components: sozcuk\diller\ja; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_hi-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_hi-1_1.zip"; ExternalSize: 106752178; Components: sozcuk\diller\hi; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-hi_en-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-hi_en-1_1.zip"; ExternalSize: 102381771; Components: sozcuk\diller\hi; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ko-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_ko-1_1.zip"; ExternalSize: 120789009; Components: sozcuk\diller\ko; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ko_en-1_1.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-ko_en-1_1.zip"; ExternalSize: 118852077; Components: sozcuk\diller\ko; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_ar-1_0.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_ar-1_0.zip"; ExternalSize: 88502631; Components: sozcuk\diller\ar; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-ar_en-1_0.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-ar_en-1_0.zip"; ExternalSize: 81869670; Components: sozcuk\diller\ar; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-en_pt-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-en_pt-1_9.zip"; ExternalSize: 66179184; Components: sozcuk\diller\pt; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion
Source: "https://argos-net.com/v1/translate-pt_en-1_9.argosmodel"; DestDir: "{app}\Sözcük\diller"; \
    DestName: "translate-pt_en-1_9.zip"; ExternalSize: 69447231; Components: sozcuk\diller\pt; \
    Flags: external download extractarchive recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#SozcukName}"; Filename: "{app}\Sözcük\{#SozcukExe}"; Components: sozcuk
Name: "{group}\{#TabcelName}"; Filename: "{app}\Tabcel\{#TabcelExe}"; Components: tabcel
Name: "{group}\{#SuiteName} Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#SozcukName}"; Filename: "{app}\Sözcük\{#SozcukExe}"; Tasks: sozcukdesktop
Name: "{autodesktop}\{#TabcelName}"; Filename: "{app}\Tabcel\{#TabcelExe}"; Tasks: tabceldesktop

[Registry]
; --- Sözcük: "Birlikte aç" listesinde görünsün
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\Sözcük\{#SozcukExe}"" ""%1"""; \
    Components: sozcuk; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".docx"; ValueData: ""; Components: sozcuk; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".doc"; ValueData: ""; Components: sozcuk
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".rtf"; ValueData: ""; Components: sozcuk
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".odt"; ValueData: ""; Components: sozcuk
Root: HKA; Subkey: "Software\Classes\Applications\{#SozcukExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".txt"; ValueData: ""; Components: sozcuk
; İsteğe bağlı: .docx dosyalarını doğrudan Sözcük açsın
Root: HKA; Subkey: "Software\Classes\.docx\OpenWithProgids"; ValueType: string; \
    ValueName: "Sozcuk.Belge"; ValueData: ""; Tasks: docxassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge"; ValueType: string; ValueName: ""; \
    ValueData: "Word Belgesi (Sözcük)"; Tasks: docxassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge\DefaultIcon"; ValueType: string; ValueName: ""; \
    ValueData: "{app}\Sözcük\{#SozcukExe},0"; Tasks: docxassoc
Root: HKA; Subkey: "Software\Classes\Sozcuk.Belge\shell\open\command"; ValueType: string; ValueName: ""; \
    ValueData: """{app}\Sözcük\{#SozcukExe}"" ""%1"""; Tasks: docxassoc
; --- Tabcel: "Birlikte aç" listesinde görünsün
Root: HKA; Subkey: "Software\Classes\Applications\{#TabcelExe}"; ValueType: string; \
    ValueName: "FriendlyAppName"; ValueData: "{#TabcelName}"; Components: tabcel; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#TabcelExe}\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\Tabcel\{#TabcelExe}"" ""%1"""; Components: tabcel
Root: HKA; Subkey: "Software\Classes\Applications\{#TabcelExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".xlsx"; ValueData: ""; Components: tabcel
Root: HKA; Subkey: "Software\Classes\Applications\{#TabcelExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".csv"; ValueData: ""; Components: tabcel
; İsteğe bağlı: .xlsx / .csv için Tabcel "Birlikte aç" önerisi (varsayılan program seçimi Windows'ta kullanıcıdadır)
Root: HKA; Subkey: "Software\Classes\.xlsx\OpenWithProgids"; ValueType: string; \
    ValueName: "Tabcel.Kitap"; ValueData: ""; Tasks: xlsxassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.csv\OpenWithProgids"; ValueType: string; \
    ValueName: "Tabcel.Kitap"; ValueData: ""; Tasks: csvassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap"; ValueType: string; ValueName: ""; \
    ValueData: "Çalışma Kitabı ({#TabcelName})"; Tasks: xlsxassoc csvassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap\DefaultIcon"; ValueType: string; ValueName: ""; \
    ValueData: "{app}\Tabcel\{#TabcelExe},0"; Tasks: xlsxassoc csvassoc
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap\shell\open\command"; ValueType: string; ValueName: ""; \
    ValueData: """{app}\Tabcel\{#TabcelExe}"" ""%1"""; Tasks: xlsxassoc csvassoc

[Run]
Filename: "{app}\Sözcük\{#SozcukExe}"; Description: "Sözcük'ü şimdi çalıştır"; Components: sozcuk; \
    Flags: nowait postinstall skipifsilent
Filename: "{app}\Tabcel\{#TabcelExe}"; Description: "Tabcel'i şimdi çalıştır"; Components: tabcel; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\Sözcük\_internal"
Type: filesandordirs; Name: "{app}\Sözcük\diller"
Type: filesandordirs; Name: "{app}\Tabcel\_internal"

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\';
  OldSozcukId = '{6E1C0A9C-2E5B-4C9E-9C4B-5F2E0B9A7C11}_is1';
  OldTabcelId = '{B3F1C2D4-5A6E-4F70-8B19-2C7D9E0A4F33}_is1';

function OldUninstaller(const Id: String): String;
var
  Value: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, UninstallKey + Id, 'UninstallString', Value) or
     RegQueryStringValue(HKCU, UninstallKey + Id, 'UninstallString', Value) then
    Result := RemoveQuotes(Value);
end;

procedure RemoveOldStandalone(const Id, DisplayName: String);
var
  Path: String;
  ResultCode: Integer;
begin
  Path := OldUninstaller(Id);
  if (Path = '') or (not FileExists(Path)) then
    Exit;
  if MsgBox('Bilgisayarda ayrı kurulmuş bir ' + DisplayName + ' bulundu.' + #13#10#13#10 +
            'Aynı uygulamanın iki kopyası olmaması için önce o kurulum kaldırılsın mı?' + #13#10 +
            'Belgeleriniz ve ayarlarınız silinmez.', mbConfirmation, MB_YESNO) = IDYES then
    Exec(Path, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectComponents then
    if (not WizardIsComponentSelected('sozcuk')) and (not WizardIsComponentSelected('tabcel')) then
    begin
      MsgBox('Kurmak için en az bir uygulama seçmelisiniz (Sözcük ya da Tabcel). ' +
             'Vazgeçtiyseniz İptal''e basabilirsiniz.', mbInformation, MB_OK);
      Result := False;
    end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if WizardIsComponentSelected('sozcuk') then
    RemoveOldStandalone(OldSozcukId, 'Sözcük');
  if WizardIsComponentSelected('tabcel') then
    RemoveOldStandalone(OldTabcelId, 'Tabcel');
end;
