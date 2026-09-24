# Sözcük — Proje Planı

## Amaç
Microsoft Word'ün karmaşık, kalabalık arayüzü yerine — aynı temel yazma deneyimini sunan, sade ve kullanımı kolay bir masaüstü kelime işlemci uygulaması. Word'ün %10'luk gerçekten kullanılan özelliklerini alıp, gerisini atan bir yaklaşım.

## Teknik Altyapı
- **Dil:** Python 3.11+
- **Arayüz:** PySide6 (Qt)
- **Metin motoru:** QTextDocument (QGraphicsView üzerinde sayfalı, yakınlaştırılabilir görünüm)
- **Dosya uyumluluğu:** python-docx (.docx), kendi .rtf/.odt okuyucuları, Qt (HTML, ODF yazma), olefile (.doc metin yedeği), pdfminer.six (PDF); eski biçimler kurulu Word ya da LibreOffice ile dönüştürülür
- **Yazım denetimi:** Windows Yazım Denetimi API'si (`comtypes`; Word ile aynı Türkçe sonuçlar, çevrimdışı)
- **Sesle yazma:** faster-whisper (yerel, çevrimdışı) + sounddevice
- **Çeviri:** CTranslate2 + SentencePiece ile Argos Translate / OPUS-MT dil paketleri (yerel; tr⇄en gömülü, diğerleri kurulumda seçilir ya da bir kez indirilir)
- **Bulut yapay zekâ:** yok (Gemini entegrasyonu kullanıcı kararıyla kaldırıldı)
- **Bulut depolama:** Google Drive / OneDrive masaüstü eşitleme klasörleri üzerinden (API ve hesap bağlantısı yok)
- **Paketleme:** PyInstaller (klasör) + Inno Setup 6.5+ (ek dilleri kurulumda indirir)

## Klasör
`sozcuk/`

## Fazlar

### Faz 1 — Temel yazı editörü
**Durum:** Uygulandı, arayüz Word kalitesine yükseltildi (elle test bekliyor)
- Ana pencere, sade araç çubuğu (ribbon değil)
- Kalın / italik / altı çizili (ikon + Ctrl+B/I/U)
- Yazı tipi ailesi ve boyutu seçimi
- Hizalama: sol / orta / sağ / iki yana yasla
- Madde işaretli ve numaralı liste
- Başlık stilleri (Normal / Başlık 1 / Başlık 2)
- Kelime/karakter sayacı (durum çubuğunda, canlı güncellenir)
- Geri al / yinele (Ctrl+Z / Ctrl+Y)
- Sade, modern, bol boşluklu tasarım; sayfa görünümü (beyaz, ortalanmış, kenar boşluklu)
- **Özel font ekleme:** kullanıcının bilgisayarına .ttf/.otf font dosyası yükleyip yazı tipi listesine ekleyebilmesi

### Faz 2 — Dosya işlemleri
**Durum:** Uygulandı (elle test ve Word'de açma testi bekliyor)
- .docx aç / kaydet (Word ile uyumlu)
- PDF olarak dışa aktar
- **PDF açma:** mevcut bir PDF'i düzenlenebilir metin olarak içe aktarma (karmaşık düzenler tam korunmayabilir, bunu kullanıcıya belirtmemiz gerekir)
- Otomatik kaydetme (birkaç dakikada bir, arka planda)

### Faz 3 — Yazım yardımı (yerel)
**Durum:** Uygulandı (elle test bekliyor)
- ~~Yapay zekâ ile düzelt / geliştir / özetle, hızlı komutlar, dilbilgisi kontrolü~~ — önce Claude, sonra Google Gemini ile uygulandı; **2026-09-17'de kullanıcı kararıyla kaldırıldı**. Böylece uygulamada hiçbir metin buluta gönderilmiyor
- **Yazım denetimi:** Windows Yazım Denetimi API'si ile yazarken canlı kırmızı dalgalı çizgi, sağ tıkta öneriler, Tümünü Yoksay, Sözlüğe Ekle, tekrarlanan kelime, F7 ile sonraki hata. Word'ün Türkçe yazım sonuçlarıyla birebir aynı (ölçüldü), çevrimdışı, ücretsiz, lisans sorunu yok
- **Sesle yazma (dikte):** yerel faster-whisper; otomatik durdurma, seviye göstergesi, kişisel sözlük (ipucu kelimeleri, doğrulanmış/öğrenilmiş düzeltmeler)
- **Tek kişisel sözlük:** dikte ve yazım denetimi aynı sözlüğü kullanır
- Bilinen sınır: dilbilgisi denetimi yok (Word'ün Türkçe dilbilgisi denetimi de testte hata bulamadı)

### Faz 5 — Google Drive / OneDrive ile canlı kayıt
**Durum:** Uygulandı (2026-09-17; elle test bekliyor — gerçek Drive'a yazılarak denenmedi)

**Kullanıcı kararı (2026-09-17):** Google Dokümanlar kullanılmayacak. Sözcük yerelde çalışır; istenen, Drive'a erişim ve çalışırken canlı (online) kayıt. Google'dan API alınmayacak.

**Yol:** Google Drive masaüstü uygulamasının sürücüsü (bu bilgisayarda `G:\Drive'ım`) ve OneDrive klasörü. Oturum o uygulamalarda açıktır; Sözcük hesaba, şifreye ya da sunuculara bağlanmaz, dosyayı klasöre kaydeder, eşitleme uygulaması buluta gönderir.

Uygulananlar (`cloud.py`, `window.py`, `docx_io.py`):
- Dosya menüsünde "Google Drive'dan Aç… / Google Drive'a Kaydet…" (ve OneDrive), yalnızca bulut klasörü varsa
- Bulut klasöründeki belgede otomatik kayıt yazmaya 2 sn ara verilince; başlıkta "Google Drive'a kaydediliyor… / kaydedildi / kaydedilemedi"
- Güvenli kayıt: "~$" adlı geçici dosyaya yazıp tek adımda yerine koyma (eşitleme uygulamaları "~$" dosyalarını göndermez), dosya kilitliyse yeniden deneme; kayıt başarısızsa kurtarma kopyası ve 10 sn sonra kendiliğinden yeniden deneme
- Başka yerde değişikliği fark etme (3 sn yoklama + içerik özeti): yerel değişiklik yoksa yeni sürüm sessizce yüklenir; varsa otomatik kayıt durur, Onların Sürümünü Yükle / Benimkini Kaydet / Benimkini Ayrı Kaydet
- .gdoc (Google Dokümanlar) dosyaları: içerik yalnızca Google sunucusunda olduğu için açılamaz; açıklama + "Tarayıcıda Aç" (Drive uygulamasıyla doğrudan belge) + .docx'e indirme yolu

Açık kalanlar / fikirler:
- Eşitleme çakışma kopyalarını ("Belge (1).docx") bildirme
- Yalnızca bulutta duran (indirilmemiş) büyük dosyayı açarken "indiriliyor" göstergesi
- Drive'daki son belgeler listesi (Dosya menüsünde)

Yapılmayacaklar:
- Google Drive API / Microsoft Graph ile doğrudan hesap bağlantısı (gerek yok; geliştirici kaydı, OAuth ve gizlilik ilkesinden ödün gerektirir)
- Google Dokümanlar web oturumunu uygulamaya gömmek (Google gömülü tarayıcılarda girişi engeller; iç servisleri API'siz kullanmak kullanım koşullarına aykırı)
- Aynı anda ortak canlı düzenleme (Word Online / Google Dokümanlar'a özgü altyapı)

### Faz 6 — Word'ün açtığı diğer biçimler
**Durum:** Uygulandı (2026-09-17; elle test bekliyor). Kullanıcı önerilen sırayı onayladı; tüm adımlar yapıldı.
Modüller: `formats.py` (biçim listesi, içerikten tür algılama, .docm/.dotx/.dotm, .txt, .html/.mht okuma; .txt/.html/.odt yazma), `converters.py` (Word COM / LibreOffice), `odt_io.py`, `rtf_io.py`, `doc_text.py` (olefile ile .doc metin yedeği).
Açık kalanlar: .odt kaydında başlık stilleri ve sayfa yapısı yazılmıyor (Qt ODF yazıcısı); LibreOffice yolu bu bilgisayarda kurulu olmadığı için gerçek LibreOffice ile denenmedi; Word her dönüştürmede yeniden başlatılıyor (~4-5 sn).

Word'ün açabildikleri: .docx .docm .dotx .dotm, .doc .dot (Word 97-2003), .rtf, .txt, .htm/.html, .mht/.mhtml, .odt (OpenDocument), .xml (Word 2003 XML), .wps (Works), .wpd (WordPerfect), .pdf.

Ölçüm (bu bilgisayar): Word 16 kurulu, LibreOffice yok. Word'ü görünmeden arka planda çalıştırarak dönüştürme denendi: Word'ün açılışı 6,4 sn (oturumda bir kez), .docx→.doc 1,4 sn, .doc→.docx 0,2 sn, Türkçe karakterler korundu; ek kütüphane gerekmedi (yazım denetiminde kullanılan `comtypes` yeterli).

**6A — Ek program gerektirmeyenler (her bilgisayarda)**
- .docm / .dotx / .dotm: .docx ile aynı biçim (makrolar yok sayılır; şablon yeni belge olarak açılır) — kolay
- .txt: kodlama algılama (UTF-8, UTF-16, Windows-1254 Türkçe) — kolay
- .htm / .html / .mht: Qt'nin HTML içe aktarımı; yerel resimler — kolay/orta
- .odt: OpenDocument okuyucu (docx_io gibi); **kaydetme için Qt'nin yerleşik ODF yazıcısı** var — orta
- .rtf: kendi okuyucumuz (metin, kalın/italik, yazı tipi, renk, hizalama, listeler, basit tablolar) — orta/zor

**6B — Word 97-2003 (.doc/.dot), Works (.wps), WordPerfect (.wpd), Word 2003 XML**
Bu eski ikili biçimleri biçimlendirmesiyle okuyan güvenilir, lisansı uygun bir Python kütüphanesi yok. Sırayla:
1. **Word kuruluysa:** Word arka planda görünmeden .docx'e çevirir, Sözcük onu açar (en yüksek doğruluk; internet yok, belge bilgisayardan çıkmaz)
2. **LibreOffice kuruluysa:** aynı dönüştürme LibreOffice ile (ücretsiz; Word olmayan bilgisayarlar için)
3. **İkisi de yoksa (.doc için):** yalnızca metni çıkaran yedek okuyucu; "biçimlendirme alınamadı, Word ya da LibreOffice kurulursa tam açılır" uyarısı

**Kaydetme**
- Eski biçimde açılan belgede Kaydet: Word'deki "Uyumluluk Modu" gibi sor — **.docx olarak kaydet (önerilen)** ya da özgün biçimde bırak (.doc/.rtf için Word/LibreOffice ile geri çevirme)
- Farklı Kaydet listesine: .odt (Qt), .txt, .html; Word/LibreOffice varsa .doc ve .rtf
- Aç penceresinde Word gibi "Tüm Word Belgeleri" filtresi ve biçim başına filtreler

Önerilen sıra: 6A kolaylar (.docm/.dotx/.dotm, .txt, .html) → .doc/.rtf/.odt için Word ile dönüştürme (6B-1) → .odt okuyucu → LibreOffice desteği → .rtf okuyucu → .doc metin yedeği. Yardım (Dosya İşlemleri + Yenilikler) her adımda güncellenir.

### Faz 4 — Cilalama ve paketleme
**Durum:** Uygulandı (2026-09-19)
- Künye: **Developed By Usta ve Ata** — Yardım → Sözcük Hakkında penceresinde, sürüm ve kullanılan açık kaynak bileşenlerle birlikte
- Uygulama ikonu: `araclar/ikon_uret.py` ile üretilen çok boyutlu `sozcuk.ico`
- **PyInstaller** paketi (`sozcuk.spec`, klasör biçiminde): `dist/Sozcuk/` ≈ 2,0 GB (gömülü dil paketleri dahil); yardım metni ve diller pakete konur, konuşma tanıma modeli ilk kullanımda indirilir
- **Inno Setup** kurulum paketi (`kurulum/sozcuk.iss`): `dist/Sozcuk-1.0-kurulum.exe` ≈ 1,31 GB; Başlat menüsü ve isteğe bağlı masaüstü kısayolu, "Birlikte aç" listesine kayıt, isteğe bağlı .docx ilişkilendirmesi, kaldırma desteği
- Kaynak kodu GitHub'a yüklendi: https://github.com/ataeyvaz/sozcuk (dil paketleri ve dist/ depoya girmez)
- **Sürüm 1.1 (2026-09-21):** paket 498 MB, kurulum 309 MB (Argos/torch/spacy çıkarıldı, yalnız tr⇄en gömülü); "Özel kurulum"da 11 dil seçilip kurulum sırasında indirilir. Ayrıntı: `surec.md`
- **Sürüm 1.2 (2026-09-24):** sesli okuma ve Ata'nın sesi pakette; paket 559 MB, kurulum 367 MB

### Faz 7 — Sesli okuma (TTS)
**Durum:** Uygulama hazır ve commit edildi (43a8fde, 2026-09-23); 14 saatlik ses (Ata, erkek) Sürüm 1.2 ile pakete kondu (2026-09-24). Açık iş: kadın sesi.

**Kullanıcı şartı (kırmızı çizgi):** doğal, kaliteli Türkçe **kadın ve erkek** ses; **bulut API yok**, her şey bu bilgisayarda.

**Seçilen yol:** Piper (VITS) ses modeli + kendi Türkçe telaffuz kodumuz. Ölçüldü (2026-09-21, i5-4210U):
Piper gerçek zamanın ~4 katı hızlı ve anlaşılır; Chatterbox (yükleme 8,5 dk), MOSS-TTS-Nano (Türkçesi bozuk,
10x yavaş), FreyaTTS, XTTS-v2/OmniVoice (yavaş ya da ticari kullanıma kapalı) elendi. Hazır Türkçe Piper
seslerinin hepsi erkek ve "robotik, aksanlı" bulundu (İngilizce sesten türetilmişler) → kendi sesimizi eğitiyoruz.

**Uygulanan (Sözcük tarafı, commit edildi — 43a8fde):**
- `sozcuk/pronunciation.py` — Türkçe metin → ses birimi (IPA). Sayı/saat/tarih/yüzde/kısaltma okuma, vurgu
  kuralları, ince-kalın ünsüz, ğ, düzeltme işareti. espeak'in 5.600 kelimelik çıktısıyla ölçüldü: ses birimi
  uyumu %96, vurgu %78 (farkların çoğunda espeak yanlış, biz doğru). espeak-ng kullanılmıyor: GPL ve Türkçe
  hataları var (bkz. modül başlığı)
- `sozcuk/read_aloud.py` — ses modeli bulma/yükleme (onnxruntime), cümle cümle sentez + çalma (sounddevice),
  bir sonraki cümleyi arka planda hazırlama, duraklat/durdur, ses ve hız menüsü
- `sozcuk/editor.py` — okunan cümlenin açık mavi vurgusu (`set_reading_range`, `ensure_position_visible`)
- `sozcuk/window.py`, `icons.py` — "Sesli Oku" düğmesi (`Ctrl+Alt+Space`), Gözden Geçir menüsü, hoparlör ikonu
- `sozcuk/yardim.md` — "Sesli Okuma" konusu, kısayol tablosu, menü tablosu

**Ses modeli (Ata'nın sesi):**
- Veri: `Desktop\BabaKartalVoice` — 300 cümle / 30 dk (kullanıcının kendi kayıtları; 27'si 2026-09-24'te eklenen "Kartal", "Beşiktaş", kalın ünlü cümleleri)
- Eğitim: Kaggle GPU (ücretsiz, haftada 30 sa). Betik ve araçlar `araclar/ses_egitimi/`, veri seti
  `ataeyvaz/sozcuk-ata-ses-verisi` (özel), kernel'ler `sozcuk-ata-ses-egitimi` (pilot 3 sa) ve
  `-2` (devam, 8 sa), `-3` (yeni kayıtlarla devam, 3 sa). Temel model: Piper tr_TR dfki medium checkpoint
- Eğitim ve uygulama **aynı** telaffuz kodunu kullanır (`--data.phoneme_type text`): Piper'ın espeak'iyle
  uyuşmazlık olmaz (BabaKartalVoice'ta eski denemeyi bu uyuşmazlık bozmuştu)
- Sonuç (11 saat): kelime hatası %21 → **%13** (Whisper ile ölçüldü). Kullanıcı tercihi: **%25 yavaş**
  (`length_scale 1.25`, ses dosyasının json'unda varsayılan)
- Sonuç (14 saat, 2026-09-24): kullanıcı dinledi, **eskisinden daha iyi** bulundu ve kuruldu:
  `%LOCALAPPDATA%\Sözcük\sesler\ata.onnx`. Whisper ölçümünde fark çıkmadı (yeni betik, 16 cümle × 3 tur:
  %25,8 → %27,4, gürültü içinde); "Kartal" 9/9 doğru duyuldu (eskide 6/9). 11 saatlik yedek:
  `…\sesler\yedek-11saat-2026-09-24\`

**Açık iş — buradan devam:**
1. ~~Yeni kayıtlarla eğitim turu~~ — yapıldı (2026-09-24, ayrıntı `surec.md`)
2. ~~Sonucu dinleyip karar~~ — kullanıcı yeni sesi beğendi, kuruldu
3. ~~Paketleme~~ — Sürüm 1.2 (2026-09-24): ses `sozcuk/sesler/` altında, depoda da (kullanıcı kararı)
4. **Kadın sesi:** aynı hat. Rızası olan bir kadın aynı kayıt uygulamasıyla cümleleri okur
5. Lisans notu: dfki temel modeli CC BY-NC-SA → türetilen ses ticari kullanıma kapalı. Ticari gerekirse
   fettah/fahrettin (CC0 veri) temelinden ya da sıfırdan eğitmek gerekir

## Notlar / Kararlar
- Ribbon değil, tek satır sade araç çubuğu tercih edildi.
- Arayüz kalitesi Office Word seviyesinde olmalı: Word mavisi başlık şeridi, basitleştirilmiş şerit görünümünde tek satır komut çubuğu, gerçek A4 sayfa görünümü, Word ile aynı kısayollar ve davranışlar.
- PDF okuma için pdfminer.six (MIT) seçildi; PyMuPDF AGPL lisanslı olduğu için .exe dağıtımına uygun değil.
- Word'ün yazım teknolojisi: sözlük dosyalarını kopyalamak lisans ihlali; kurulu Word'ü otomasyonla çağırmak yavaş (açılış 52 sn) ve Word'e bağımlı. Windows'un yerleşik yazım denetimi API'si aynı Türkçe sonuçları verdiği için o seçildi.
- Bulut yapay zekâ kullanılmıyor: tüm yazım yardımı (yazım denetimi, dikte) bu bilgisayarda çalışır.
- Karmaşık Word özellikleri (mail merge, makrolar, gelişmiş stil şablonları vb.) bilinçli olarak dışarıda bırakılıyor.
- PDF açma teknik olarak PDF kaydetmeden daha zor: PDF'ler "düz metin" değil, sabit konumlu görsel öğeler içerir. `pdfplumber` veya `PyMuPDF` gibi kütüphanelerle metni çıkarmak mümkün ama orijinal biçimlendirme (yazı tipi, tam düzen) birebir korunamayabilir — bunu kullanıcıya net şekilde belirtmemiz gerekiyor.

---
*Faz durumları ve değişiklik geçmişi için `surec.md` dosyasına bakın.*
