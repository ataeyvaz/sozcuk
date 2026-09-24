# Sözcük — Süreç Günlüğü

Bu dosya, `plan.md`'deki fazlarda tamamlanan işleri, yapılan değişiklikleri ve alınan kararları tarih sırasıyla kaydeder. Her oturumdan sonra buraya kısa bir not eklenir.

Format:
```
## [Tarih] — Faz X: Başlık
- Ne yapıldı
- Ne değişti / neden değişti
- Bilinen sorunlar / sonraki adım
```

---

## [2026-09-16] — Faz 1: Temel yazı editörü başlatıldı
- Proje iskeleti oluşturuldu (Claude Code ile)
- PySide6 + QTextEdit tabanlı ana pencere, araç çubuğu ve metin editörü talebi verildi
- Durum: uygulanıyor, sonuç henüz test edilmedi

## [2026-09-16] — Plan güncellemesi: PDF açma ve özel font ekleme
- Faz 1'e "özel font ekleme" özelliği eklendi (kullanıcı .ttf/.otf yükleyebilecek)
- Faz 2'ye "PDF açma" özelliği eklendi (PDF'i düzenlenebilir metne dönüştürme)
- Not: PDF açma, PDF kaydetmeden teknik olarak daha zor — biçimlendirme kaybı olabileceği kullanıcıya belirtilecek
- Henüz kod tarafında uygulanmadı, sadece plana eklendi

## [2026-09-16] — Faz 1: Temel yazı editörü uygulandı
- Yapı: `main.py` (giriş), `sozcuk/window.py` (pencere, araç çubuğu, durum çubuğu), `sozcuk/editor.py` (QTextEdit, başlık/liste mantığı, sayfa görünümü), `sozcuk/fonts.py` (özel yazı tipleri), `sozcuk/icons.py` (kodla çizilen ikonlar), `requirements.txt`
- Tek satır araç çubuğu: geri al/yinele, paragraf stili (Normal/Başlık 1/Başlık 2), yazı tipi + boyut, yazı tipi ekle, kalın/italik/altı çizili, 4 hizalama, madde/numaralı liste
- Kısayollar: Ctrl+B/I/U, Ctrl+Z/Y, Ctrl+L/E/R/J (hizalama), Ctrl+Shift+L / Ctrl+Shift+N (listeler)
- Sayfa görünümü: gri zemin üzerinde ortalanmış 816px beyaz sayfa, 72px kenar boşluğu, varsayılan Calibri 11
- Durum çubuğunda canlı kelime/karakter sayacı; pencere başlığında kaydedilmemiş değişiklik işareti (●)
- Özel font ekleme: "A+" butonu ile bir veya birden fazla .ttf/.otf seçilir; dosya `%APPDATA%\Sözcük\fonts` klasörüne kopyalanır, her açılışta otomatik yüklenir. Geçersiz dosyada uyarı verilir, kopya silinir
- Karar: başlığın sonunda Enter'a basınca yeni satır otomatik Normal stile döner (Word davranışı)
- Karar: QTextEdit.undoAvailable sinyali geri al sırasında yanlış durum bildirdiği için geri al/yinele buton durumu doğrudan belgeden okunuyor
- Karar: sayfaya gölge efekti eklenmedi (QTextEdit'te çizim performansını düşürüyor), ince kenarlık kullanıldı
- Test: ekransız otomatik testler geçti (başlık, Enter sonrası Normal, listeler aç/kapa/değiştir, hizalama, biçim, sayaç, geri al, geçerli/geçersiz font yükleme)
- Bilinen sorunlar: tek uzun sayfa (sayfa sonu/sayfalama yok); eklenen fontu kaldırma arayüzü yok (klasörden elle silinebilir); elle kullanım testi yapılmalı
- Sonraki adım: Faz 2 — .docx aç/kaydet

## [2026-09-16] — Arayüz yenilemesi: Word kalitesinde sade tasarım
- Neden: kullanıcı, planlamada kararlaştırıldığı gibi arayüzün Office Word kalitesinde olmasını istedi (ribbon yok kararı korunarak)
- Word mavisi (#185ABD) başlık şeridi; Windows 11 yerel başlık çubuğu da aynı renge boyanıyor (DWM API)
- Başlık şeridinde: Dosya menüsü, hızlı erişim (Kaydet / Geri Al / Yinele), ortada belge adı + kayıt durumu, sağda "Otomatik Kaydet" anahtarı
- Tek satır komut çubuğu beyaz, yuvarlak köşeli kart içinde (Word'ün "basitleştirilmiş şerit" görünümü)
- İkonlar SVG olarak yeniden çizildi (her DPI'da keskin, pasif hali otomatik gri); uygulama ikonu eklendi
- **Gerçek sayfalama:** belge ayrı A4 sayfalar halinde (21×29,7 cm, 2,5 cm kenar boşluğu), sayfalar arası gri boşluk ve hafif gölge. Metin sayfa sınırında bir sonraki sayfaya geçer
- Word varsayılanları: Normal paragraf sonrası 8 nk, satır aralığı 1,08; başlıklarda önce/sonra boşluk
- Yeni biçim özellikleri: üstü çizili, yazı tipi rengi (Word tema paleti + standart renkler + "Diğer Renkler"), metin vurgu rengi (Word'ün 15 rengi), tüm biçimlendirmeyi temizle (Ctrl+Boşluk), yazı tipini büyüt/küçült (Ctrl+] / Ctrl+[), satır aralığı menüsü, girinti artır/azalt
- Liste davranışları Word gibi: Tab / Shift+Tab ile seviye değiştirme (alt seviyeler a., i. / ◦, ▪), boş maddede Enter önce seviye düşürür sonra listeden çıkar, numaralandırma alt maddelerden sonra kaldığı yerden devam eder
- Durum çubuğu: "Sayfa X / Y", sözcük sayısı (karakter sayısı ipucunda), dil, son kaydetme saati
- Yapı: `styles.py` (belge biçim sabitleri), `theme.py` (renkler, stil sayfası), `widgets.py` (renk seçici, anahtar, bilgi çubuğu), `builder.py` (içe aktarıcılar için ortak belge oluşturucu)
- Karar: Faz 1'deki "gölge yok" kararı değişti — gölge artık Qt efektiyle değil, sayfa arka planı çizilirken elle çiziliyor (performans sorunu yok)

## [2026-09-16] — Faz 2: Dosya işlemleri uygulandı
- **.docx aç/kaydet** (`docx_io.py`, python-docx): paragraflar, Başlık/Title stilleri, kalın/italik/altı/üstü çizili, yazı tipi/boyut, yazı ve vurgu rengi, üst/alt simge, hizalama, satır aralığı, paragraf boşlukları, girinti, iç içe madde/numaralı listeler, sayfa sonları, tablolar (birleştirilmiş hücreler dahil), satır içi görseller. Stil zinciri, belge varsayılanları ve tema fontları (ör. Calibri/Aptos) çözülüyor
- Açılışta desteklenmeyen öğeler (üst/alt bilgi, dipnot, yorum, metin kutusu, şekiller) bilgi çubuğunda bildiriliyor: "Kaydederseniz bu öğeler dosyadan çıkarılır"
- Kaydetme önce geçici dosyaya yazıp sonra yerine koyuyor — yarıda kalan kayıt dosyayı bozmaz. Dosya Word'de açıksa anlaşılır hata mesajı
- **PDF olarak dışa aktar** ve **Yazdır**: ekrandaki sayfa boşlukları olmadan gerçek A4 ölçüsünde
- **PDF açma** (`pdf_io.py`, pdfminer.six — MIT lisansı; PyMuPDF AGPL olduğu için .exe dağıtımına uygun değil): arka plan iş parçacığında dönüştürülür, arayüz donmaz. Yazı tipi/boyut/kalın/italik korunur; başlıklar, madde/numaralı listeler, ortalanmış satırlar, satır sonu tirelemeleri tahmin edilir; sayfa numaraları atlanır. Açılınca kullanıcıya düzenin birebir korunmamış olabileceği bilgi çubuğunda söylenir; kaydedince .docx olur. Taranmış (metinsiz) PDF'lerde açık hata mesajı
- **Otomatik kaydetme:** "Otomatik Kaydet" açık ve dosya kayıtlıysa yazmaya 4 sn ara verilince kaydedilir (Word gibi). Kaydedilmemiş belgeler için 2 dakikada bir kurtarma kopyası (`%APPDATA%\Sözcük\recovery`); uygulama çökerse bir sonraki açılışta "Geri Yükle / Sil" önerilir. Anahtar durumu hatırlanır
- Dosya menüsü: Yeni (Ctrl+N), Aç (Ctrl+O), Kaydet (Ctrl+S), Farklı Kaydet (F12), PDF Olarak Dışa Aktar, Yazdır (Ctrl+P), Kapat. Kapatırken/yeni belgede Word tarzı "Kaydedilsin mi?" sorusu
- Komut satırından dosya açma: `python main.py belge.docx` (ileride "Birlikte aç" için)
- Test: gerçek pencerede ekran görüntüleri incelendi; docx kaydet→aç gidiş-dönüşünde metin, başlık, biçimler, vurgu/renk, iç içe liste numaraları birebir; Word tarzı stil tabanlı listeler, tablo, görsel, sayfa sonu, üst bilgi uyarısı doğrulandı; PDF dışa aktarma A4 (595×842 pt) ve görüntüsü kontrol edildi; bilgisayardaki gerçek PDF'ler içe aktarıldı (46 sayfalık PDF ≈ 9 sn dönüştürme); kurtarma kopyası yaz/öner/sil test edildi
- Testte bulunup düzeltilen hatalar: iç içe listeden çıkınca girintinin birikmesi; kaydetmede numaralandırmanın her maddede 1'den başlaması; tablo hücrelerinin bir kısmının boş gelmesi; tablodan önceki satırın liste biçimini miras alması
- Bilinen sınırlar: Word'ün kendisiyle açma testi yapılamadı (bu bilgisayarda Word/.docx yok) — elle doğrulanmalı; üst/alt bilgi, dipnot, yorum, şekil desteklenmiyor; yakınlaştırma (zoom) yok; çok sütunlu PDF'lerde sütunlar tek akışa birleşir; büyük belgelerde otomatik kaydetme ana iş parçacığında çalışır (normal belgelerde fark edilmez)
- Sonraki adım: Faz 3 — AI destekli yazım

## [2026-09-16] — Arayüz ve düzenleme iyileştirmeleri (kullanıcı talebi, Faz 3 öncesi)
- **Keskin ikonlar:** bulanıklığın sebebi 20 px ikonların 18 px'e küçültülmesi ve çizgilerin piksel ızgarasına oturmamasıydı (ekran ölçeği %100). Tüm ikonlar 20 px ızgarada 1 px çizgiyle yeniden çizildi; özel ikon motoru her boyutta doğrudan çiziyor; harfler (B, I, U, A) ipuçlamalı gerçek yazı tipiyle çiziliyor; araç çubuğu ve menülerde ikonlar tam 20 px
- **Yakınlaştırma:** durum çubuğunda Word tarzı [−] kaydırıcı [+] ve yüzde menüsü (%50–%300, Sayfa Genişliği, Tam Sayfa); Ctrl+fare tekerleği imleç konumuna göre yakınlaştırır; %10–%500; son düzey hatırlanır
- Karar: editör QTextEdit'ten QGraphicsView + QGraphicsTextItem'a taşındı. QTextEdit yakınlaştırma desteklemiyor; grafik sahnesi gerçek vektörel ölçekleme yapıyor (metin yerleşimi değişmiyor, fare/imleç eşlemesi Qt tarafından yapılıyor)
- **Cetvel:** yatay cetvel (cm, kenar boşlukları gri) imlecin olduğu paragrafın ilk satır / asılı / sol / sağ girintilerini gösterir; işaretçiler sürüklenince sayfada kılavuz çizgi çıkar, bırakınca seçili paragraflara uygulanır (0,25 cm'ye yapışır, Alt ile serbest). Dikey cetvel imlecin olduğu sayfanın üst/alt kenar boşluklarını gösterir. Durum çubuğundan açılıp kapatılabilir. Girintiler .docx'e birebir yazılıp okunuyor
- **Tablolar:** komut çubuğunda Tablo düğmesi — Word'deki ızgaradan fareyle boyut seçme, "Tablo Ekle…" penceresi, üste/alta satır, sola/sağa sütun ekleme, satır/sütun/tablo silme, hücre birleştirme/bölme. Tabloda sağ tık menüsü aynı işlemleri içerir. Tab sonraki hücreye geçer, son hücrede yeni satır ekler
- **Panodan yapıştırma:** Excel / Word / web tabloları (HTML) tablo olarak yapıştırılır, kenarlıksız gelenlere kenarlık verilir; sekmeli metin (Excel, Google E-Tablolar) tabloya çevrilir; imleç tablodayken tablo verisi hücrelerin üzerine yazılır, gerekirse satır/sütun eklenir; panodaki görseller eklenir; Ctrl+Shift+V yalnızca metni yapıştırır
- Sağ tık menüsü: Kes, Kopyala, Yapıştır, Yalnızca Metni Koru (+ tablo işlemleri)
- Testte bulunup düzeltilen hatalar: QGraphicsTextItem Tab tuşunu kendi yakaladığı için tabloda/listede Tab sekme karakteri ekliyordu; yapıştırılan HTML tablolarına kenarlık uygulanmıyordu (Qt yeni tablo çerçevelerini düzenleme bloğu kapanınca oluşturuyor); metin öğesinin çevresinde Qt'nin kesik çizgili odak çerçevesi görünüyordu
- Test: yazma, liste Tab/Enter davranışları, tablo ekleme/Tab gezinme/satır-sütun/birleştir-böl/silme, TSV ve HTML tablo yapıştırma, cetvel girintileri ve docx gidiş-dönüşü, %150'de fareyle tıklama konumu, Tam Sayfa yakınlaştırma otomatik testlerle doğrulandı; ekran görüntüleri incelendi
- Bilinen sınırlar: cetvelde sekme durakları ve tablo sütun işaretçileri yok; tablo sütun genişlikleri sürüklenerek değiştirilemiyor; gerçek Excel/Word panosuyla elle test yapılmalı
- Sonraki adım: Faz 3 — AI destekli yazım

## [2026-09-16] — Faz 3: AI destekli yazım uygulandı
- **Model:** Claude Opus 5 (`claude-opus-5`), Anthropic Python SDK 1.6 ile. Tüm istekler akışlı (arayüz donmaz, yanıt canlı akar). Güvenlik sınıflandırıcısı bir isteği reddederse sunucu tarafında Anthropic'in önerdiği modelle otomatik yeniden denenir (`fallbacks: "default"`); yine reddedilirse kullanıcıya Türkçe açıklama gösterilir
- **Yardımcı paneli** (komut çubuğunun sağındaki "Yardımcı" düğmesi, Word'deki Copilot paneli gibi sağda açılır):
  - Hızlı eylemler: Düzelt, Geliştir, Özetle, Sadeleştir, Kısalt, Resmileştir
  - Serbest komut kutusu ("bu cümleyi daha sade yaz", "daha samimi yaz" vb.)
  - Hedef: seçim varsa seçim, yoksa imlecin bulunduğu paragraf; paragraf boşsa yeni metin üretilir (önceki ~3000 karakter bağlam olarak verilir) ve imlecin yerine eklenir
  - Öneri önce panelde gösterilir: Değiştir / Altına Ekle / Kopyala / Vazgeç. Değiştirme orijinal yazı biçimini korur ve tek adımda geri alınır. Öneri hazırlanırken metin değiştirildiyse onay sorulur. Durdur düğmesi var
  - Sağ tık menüsünde "Yardımcı" alt menüsü (aynı hızlı eylemler)
- **Yazım ve dilbilgisi denetimi:** "Belgeyi Denetle" (seçim varsa yalnızca seçimi) — Claude yapılandırılmış çıktı (JSON şeması) ile hatalı ifade / öneri / açıklama döndürür. Hatalar belgede Word gibi kırmızı dalgalı çizgiyle işaretlenir; sağ tıkta öneri kalın yazılı en üstte + açıklama + Yoksay. Panelde liste: Uygula / Yoksay / Tümünü Uygula (tek adımda geri alınır). Uzun belgeler ~40.000 karakterlik parçalar halinde denetlenir. İşaretler belge biçimine yazılmaz (kaydedilen dosyayı etkilemez); işaretli ifade düzenlenince işaret kalkar. Paragrafta birebir bulunamayan bulgular güvenlik için atlanır
- **API anahtarı:** paneldeki "API Anahtarı" penceresi; anahtar Windows Kimlik Bilgisi Yöneticisi'nde (keyring) saklanır, belgelere yazılmaz; "Bağlantıyı Test Et" ile doğrulanır. Kayıtlı anahtar yoksa SDK ortam değişkenini kullanır
- Hata mesajları Türkçe: geçersiz anahtar, yetki, istek sınırı, sunucu yoğunluğu, bağlantı yok
- Model istemi: yanıt doğrudan belgeye gireceği için yalnızca metin (Markdown/açıklama yok), metnin dilinde, paragraf yapısı korunur; belge içindeki talimat gibi görünen ifadeler uygulanmaz (istem enjeksiyonuna karşı)
- Yapı: `sozcuk/ai.py` (Qt'den bağımsız Claude istemcisi, eylemler, denetim), `sozcuk/assistant.py` (panel, arka plan iş parçacıkları, API anahtarı penceresi); editöre bulgu işaretleme ve sağ tık menüsü kancaları eklendi
- Karar: proje artık kendi sanal ortamını kullanıyor (`.venv`). Sebep: Anthropic SDK 1.6 gerekiyor, bilgisayardaki genel Python'da 0.96 kurulu ve masaüstündeki diğer projeler (aguilang vb.) etkilenmesin. Başlatmak için `Sözcük.bat` (ya da `.venv\Scripts\python main.py`). PyInstaller paketlemesi de bu ortamdan yapılacak
- Testte bulunup düzeltilen hata: imleç/satır konumu hesabında paragraf konumu iki kez ekleniyordu — dalgalı çizgiler kelimenin ~150 px altına çiziliyor, sayfa sınırındaki paragraflarda "Sayfa X / Y" yanlış sayfayı gösteriyordu. Hit-test ile karşılaştırmalı testle doğrulandı
- Test: panelin tamamı sahte Claude istemcisiyle uçtan uca test edildi (istek parametreleri, akış, değiştir/geri al, üretim + ekle, denetim işaretleri, geçersizleşme, tümünü uygula, hata yolu); ekran görüntüleri incelendi. Önceki özelliklerin testleri yeniden geçti
- **Bilinen durum:** bu bilgisayardaki `ANTHROPIC_API_KEY` ortam değişkeni API tarafından geçersiz bulundu, bu yüzden gerçek Claude ile canlı test yapılamadı. Kullanıcı geçerli bir anahtarı "API Anahtarı" penceresinden girip elle denemeli
- Sonraki adım: Faz 4 — cilalama ve PyInstaller ile tek dosyalık .exe

## [2026-09-17] — Faz 3 değişikliği: Claude yerine Google Gemini
- Neden: kullanıcı talebi — Google AI Studio ücretsiz katmanı (kredi kartı istemiyor; gerekçe plan.md'de)
- `sozcuk/ai.py` Google'ın resmî `google-genai` SDK'sı (2.24) ile yeniden yazıldı; panel, yazım denetimi, sağ tık menüsü ve işaretleme aynen korundu. SDK kullanımı kurulu paketin kendisinden doğrulandı (imzalar, hata sınıfları, zaman aşımı birimi)
- Modeller: varsayılan `gemini-3.5-flash`; seçenekler `gemini-3.1-flash-lite` (en hızlı, daha yüksek ücretsiz kota) ve `gemini-3.1-pro-preview` (en güçlü, ücretsiz katmanda olmayabilir). Model, "API Anahtarı" penceresinden seçilir ve hatırlanır; listede olmayan bir model adı da yazılabilir. Seçili model panelin altında görünür
- Gemini 3 modellerinde düşünme düzeyi "düşük" (yazım işlerinde daha hızlı yanıt)
- Metin dönüştürme akışlı (`generate_content_stream`); yazım denetimi JSON şemalı yapılandırılmış çıktıyla (`response_json_schema`)
- API anahtarı penceresi: Google AI Studio bağlantısı, model seçimi, ücretsiz katmanda metinlerin Google tarafından kullanılabileceği ve istek sınırları hakkında not. "Bağlantıyı Test Et" model bilgisini sorgular — hem anahtarı hem model adını doğrular, kota harcamaz. Anahtar yine Windows Kimlik Bilgisi Yöneticisi'nde; kayıtlı değilse GEMINI_API_KEY / GOOGLE_API_KEY ortam değişkeni kullanılır
- Türkçe hata mesajları: geçersiz anahtar, ücretsiz katman istek sınırı (429), model bulunamadı, bölge desteklenmiyor, sunucu yoğun, zaman aşımı, bağlantı yok, güvenlik engeli, yarıda kesilme
- Anthropic SDK sanal ortamdan kaldırıldı; requirements.txt güncellendi (`google-genai`)
- Testte bulunup düzeltilen hatalar: yanıtın tamamı Türkçe tırnak (“…”) içinde gelince tırnaklar temizlenmiyordu; SDK'nın otomatik fonksiyon çağırma uyarısı her istekte basılıyordu (özellik kapatıldı)
- Test: geçersiz anahtarla gerçek Google isteği (ücretsiz) → doğru Türkçe hata; anahtarsız durum; SDK'nın gerçek yanıt nesneleriyle akış, güvenlik engeli, yarıda kesilme, durdurma, JSON denetimi ve bozuk JSON; panel uçtan uca (model seçimi isteğe yansıyor, değiştir, denetim işaretleri); API anahtarı penceresinin görüntüsü incelendi
- Bilinen durum: bu bilgisayarda Gemini anahtarı yok, gerçek Gemini ile canlı test yapılamadı. Kullanıcı AI Studio anahtarını girip "Bağlantıyı Test Et" ile doğrulamalı. Model adları SDK'nın model listesinden alındı; hesabınızda farklıysa pencereden değiştirilebilir

## [2026-09-17] — Sesle yazma (dikte) eklendi
- Ne yapıldı: komut çubuğunda kendi grubunda (ince ayraçlarla) mikrofon düğmesi. Tıkla → dinlemeye başlar; tekrar tıkla → kayıt durur, ses metne dönüştürülür ve imlecin olduğu yere yazılmış gibi eklenir. Kısayol: Ctrl+Shift+M
- **Gizlilik:** tamamen yerel ve çevrimdışı — ses de, çıkan metin de hiçbir sunucuya gönderilmez; API anahtarı ya da hesap gerekmez. İnternet yalnızca ilk kullanımda modeli bir kez indirmek için gerekir (Hugging Face önbelleği, ~480 MB). Kayıt yalnızca bellekte tutulur, diske yazılmaz
- Teknik: `sozcuk/dictation.py` — kayıt `sounddevice` (PortAudio; PySide6 ile en temiz entegrasyon, ek derleme gerektirmiyor), tanıma `faster-whisper` "small" modeli, dil açıkça Türkçe (`language="tr"`). Arka plan iş parçacığında çalışır (PDF içe aktarma ile aynı QThread düzeni), arayüz donmaz. `window.py` yalnızca düğmeyi oluşturup denetleyiciye bağlar
- Kararlar:
  - CPU + int8: her bilgisayarda çalışır, GPU sürücüsü gerektirmez
  - Ses etkinliği filtresi (VAD) açık: sessizlikleri atar, Whisper'ın sessizlikte uydurma metin üretmesini önler; uzun kayıtlarda tekrar döngüsüne girmemesi için önceki metne koşullama kapalı
  - Kayıt 16 kHz mono; mikrofon bu hızı desteklemezse kendi hızında kaydedilip dönüştürülür
  - Model, mikrofona basıldığı anda arka planda yüklenmeye başlar — yükleme süresi kullanıcı konuşurken harcanır
  - Dikte edilen metin tek bir geri alma adımıdır (Ctrl+Z önceden yazılanı silmez); imlecin önünde boşluk yoksa otomatik boşluk eklenir; seçim varsa yazıyormuş gibi yerine geçer
  - Tek kayıt en fazla 10 dakika (sonra kendiliğinden durur ve dönüştürür)
  - `sounddevice` açılışta değil kayıt başlarken içe aktarılır: ses kütüphanesi yüklenemezse uygulama çökmez, yalnızca dikte kullanılamaz
- Arayüz: kayıt sırasında mikrofon ikonu kırmızıya döner, kayıt noktası çıkar ve yarım saniyede bir yanıp söner; düğme zemini açık kırmızı. Durum çubuğu: "Dinleniyor… 0:07 — durdurmak için…", dönüştürürken "Ses metne dönüştürülüyor… (4 sn)" (sayaç, takılmadığını gösterir), ilk kullanımda "model indiriliyor" notu, bitince "Dikte edilen metin eklendi." Dönüştürme sürerken düğme pasif
- Hatalar durum çubuğunda: "Mikrofon bulunamadı.", "Mikrofon açılamadı. Başka bir uygulama kullanıyor ya da mikrofon izni kapalı olabilir.", "Konuşma algılanmadı.", "Kayıt çok kısa…", model indirilemedi (internet gerekli)
- İkonlar: `mic` ve `mic_recording` 20 px ızgaraya hizalı; ikon motoruna dolu şekil desteği eklendi
- requirements.txt: `faster-whisper`, `sounddevice` eklendi
- Test: Windows'un Türkçe "Tolga" sesiyle sentezlenen cümle gerçek modelle tanındı — birebir doğru ("Yarın sabah saat 9'da toplantı odasında buluşalım. Rapor hazır olursa birlikte inceleriz."); gerçek mikrofondan kayıt (16 kHz açıldı); çok kısa kayıt ve sessizlik; arayüz akışı Ctrl+Shift+M ile (kayıt görünümü, dönüştürürken tekrar basmanın yok sayılması, sayaç, imlece ekleme, boşluk bağlama, ayrı geri alma adımı); mikrofon yokken hata mesajı; ekran görüntüsü incelendi
- Testte bulunup düzeltilen hatalar: Ctrl+Z dikte edilen metinle birlikte önceden yazılanı da siliyordu (ayrı düzenleme bloğu); dönüştürme sayacı hata mesajının üzerine yazabilirdi
- Bilinen sınır: bu bilgisayarın işlemcisinde (4 çekirdek) small model yaklaşık gerçek zamanın 1,5 katı sürede çalışıyor (6 sn konuşma ≈ 10 sn). Beam genişliği ve iş parçacığı sayısı denendi, anlamlı fark yok; darboğaz modelin kendisi. Daha hızlı dikte gerekirse ileride "base" model seçeneği eklenebilir (daha düşük Türkçe doğruluk)
- Not: plan.md'de "Görsel Kalite Standardı" başlıklı bir bölüm bulunamadı; projede uygulanan standart (20 px ızgaraya hizalı ikonlar, hover/pressed durumları, ayraçlı gruplar) izlendi
- Sonraki adım: Faz 4 — cilalama ve PyInstaller ile tek dosyalık .exe (faster-whisper modeli .exe'ye gömülmeyecek; ilk kullanımda indirilecek)

## [2026-09-17] — İnceleme: Diktek projesiyle karşılaştırma (kod değişikliği yok)
- Ne yapıldı: `Desktop\diktek` (C#/.NET 10, whisper.cpp, WinForms tepsi uygulaması) incelendi; hangi yönlerinin Sözcük'e alınmaya değer olduğu aynı bilgisayarda ölçülerek değerlendirildi. Diktek klasörüne yazılmadı (testte Diktek günlüğü `DIKTEK_LOG=0` ile kapalıydı)
- Ölçümler (aynı 6,4 sn'lik Türkçe cümle, i5-4210U):
  - Diktek whisper.cpp small-q5_0: 31,7 sn, doğru. Sözcük faster-whisper small int8: ~10 sn, doğru → Sözcük'ün motoru ~3 kat hızlı, motor değişikliği yapılmayacak
  - Kısık ses (tepe 0,09 + oda gürültüsü): iki motor da doğru. Diktek'in `AudioNormalizer` yaklaşımı faster-whisper'da denendi — çıktı birebir aynı, etkisiz → eklenmeyecek
  - Konuşmasız oda gürültüsü: Sözcük (VAD açık) boş sonuç, anında. VAD kapatılınca "Altyazı M.K.", "abone olmayı unutmayın" uyduruyor — Diktek'in "(Müzik)" sorununun Sözcük'teki karşılığı VAD ile zaten çözülmüş
- Alınmaya değer bulunanlar (henüz uygulanmadı, kullanıcı kararı bekliyor): sessizlikte otomatik durdurma, durum çubuğunda canlı seviye göstergesi, kişisel sözlük (faster-whisper `initial_prompt`/`hotwords`), yerel teşhis günlüğü, modeli internetsiz klasörden yükleme seçeneği
- Uygun bulunmayanlar: whisper.cpp motoru, ses normalizasyonu, sondaki sessizliği kırpma (VAD yapıyor), global kısayol / SendInput / pano enjeksiyonu / tepsi (Sözcük metni kendi belgesine yazıyor), `check-offline.ps1` (Sözcük Gemini ve model indirme için ağa çıkıyor)

## [2026-09-17] — Dikte iyileştirmeleri: otomatik durdurma, seviye göstergesi, dikte sözlüğü, teşhis günlüğü
- Neden: Diktek karşılaştırmasında önerilen sırayla, kullanıcı onayıyla (1+2, sonra 3+4). Kullanıcı ek olarak sözlüğe yeni ve öğrenilmiş kelimelerin eklenebilmesini istedi
- Mikrofon düğmesi artık ok menülü: "Susunca Otomatik Durdur (2,5 sn)", "Ses Seviyesi Göstergesi" (ikisi de açılıp kapanır, hatırlanır), "Dikte Sözlüğü…"
- **1) Sessizlikte otomatik durdurma** (`SilenceDetector`, dictation.py): konuşma başladıktan sonra 2,5 sn kesintisiz sessizlikte kayıt kendiliğinden durur ve dönüştürülür. Konuşma algılanmadan sayaç işlemez. Eşik: mutlak taban, konuşma tepesinin %10'u ve **kaydın gürültü tabanının 2,5 katı** — sonuncusu Diktek'in yöntemine eklendi, çünkü bu bilgisayarın ortam sesi ölçümde Diktek eşiğinin üstüne çıkabiliyordu. Durdurma ses iş parçacığında değil arayüz zamanlayıcısında yapılır. Durum çubuğu: "konuşmaya başlayın" → "susunca kendiliğinden durur" → "susarsanız 1,8 sn sonra biter"
- **2) Canlı seviye göstergesi** (`LevelMeter`, widgets.py): kayıt sırasında durum çubuğunda 20 bölmeli çubuk; desibel ölçeği (kısık mikrofon da okunur), konuşma algılanmadan soluk mavi, sonra yeşil, yüksekte sarı, kırpılma bölgesinde kırmızı; tepe tutucu çizgi
- **3) Dikte sözlüğü** (`vocabulary.py`, `vocabulary_dialog.py`; `%APPDATA%\Sözcük\dikte-sozlugu.json`, yalnızca yerel):
  - Kelimeler (özel adlar, terimler) Whisper'a ipucu (`hotwords`) olarak verilir. Ölçüldü: "PySide" ipucu yokken "Hüseyin de", ipucuyla doğru. Uzun/yapay listeler başa uydurma metin ekletebildiği için ipucu 120 token ile sınırlı; önce elle eklenenler, sonra en çok kullanılan öğrenilmişler
  - Düzeltmeler (yanlış → doğru) dikte edilen metne uygulanır; Türkçe büyük/küçük harf (I/ı, İ/i) doğru; büyük harf yalnızca cümle başında korunur; paragraf sınırını aşmaz
  - **Elle ekleme:** sözlük penceresinden kelime ya da düzeltme; ayrıca belgede kısa bir seçime sağ tıklayıp "Dikte Sözlüğüne Ekle"
  - **Öğrenme:** kullanıcı dikte edilen metinde bir kelimeyi düzeltip o bölümden çıkınca (ya da yeni dikte başlarken) Sözcük bunu öğrenir. Yalnızca yazımı düzeltilen kelimeler öğrenilir (benzerlik ≥ %60, en fazla 3 kelime, sayı içerenler hariç); anlamı değiştiren düzenlemeler öğrenilmez. Büyük harfle başlayan düzeltmeler (özel ad) kelime listesine de girer. Yanlış öğrenmeye karşı öğrenilen düzeltme 2 kez görülünce ya da kullanıcı pencereden "Onayla" deyince etkin olur. Pencerede kaynak (Elle eklendi / Öğrenildi), kullanım sayısı ve durum (Etkin / Öğreniliyor 1/2) görünür; silinebilir
- **4) Yerel teşhis günlüğü** (`logbook.py`; `%APPDATA%\Sözcük\Logs\sozcuk.log`, 1 MB × 4 dönen dosya): başlangıç sürümleri, yakalanmamış hatalar (iş parçacıkları dahil), Qt uyarıları; dikte (kayıt süresi, otomatik mi, tepe/konuşma RMS/gürültü tabanı, model yükleme, tanıma süresi, karakter sayısı, sözlük düzeltmesi/öğrenme sayısı); dosya açma/kaydetme (süre, paragraf/sayfa sayısı, hata türü); Gemini (eylem süresi, karakter sayıları, hata). **Gizlilik:** belge içeriği, dosya adları, dikte edilen metin ve yapay zekâya giden metin yazılmaz. Dosya menüsü → "Tanılama Günlüğü Klasörünü Aç". Kapatmak için `SOZCUK_LOG=0`
- Test:
  - Sessizlik algılayıcı: sessiz oda, orta gürültü ve kısık mikrofonda konuşma bitiminden 2,5 sn sonra durdu; konuşma yokken hiç durmadı
  - Sözlük birim testleri: ekleme/tekilleştirme, düzeltme uygulama, Türkçe harfler, öğrenme ve eşik, anlam değişikliğinin reddi, kalıcılık, bozuk dosyanın yedeklenmesi
  - Uçtan uca (kaydedilmiş ses gerçek zamanlı hızda sahte mikrofona beslendi, gerçek model): 3 diktenin üçünde kendiliğinden durdu, gösterge kayıtta göründü sonra gizlendi; "Ara yüzünü" iki kez "arayüzünü" diye düzeltilince öğrenildi ve 3. diktede otomatik uygulandı; sağ tıkla sözlüğe ekleme; günlükte dikte metni olmadığı doğrulandı; ekran görüntüleri incelendi
  - Önceki özelliklerin testleri (tablolar, yakınlaştırma, cetvel, docx, yardımcı paneli) yeniden geçti
- Testte bulunup düzeltilen hata: çok kelimeli bir düzeltme satır sonu üzerinden eşleşip iki paragrafı birleştirebiliyordu
- Bilinen sınırlar: ani yüksek seslerin olduğu ortamda (TV, arka planda konuşma) otomatik durdurma tetiklenmeyebilir — bu sesler yalnızca ses düzeyiyle konuşmadan ayırt edilemez; kayıt düğme/kısayolla her zaman durdurulabilir. 2,5 sn'den uzun düşünme molası kaydı bitirir (menüden kapatılabilir). Öğrenme, kullanıcı imleci dikte edilen bölümden çıkarana ya da yeni dikte başlayana kadar bekler. Canlı mikrofonla gerçek konuşma testi kullanıcıda
- Yeni bağımlılık yok (requirements.txt değişmedi)

## [2026-09-17] — Word yazım denetimi araştırması + doğrulanmış dikte düzeltmeleri
- Soru: Word'ün yazım/dilbilgisi teknolojisi hak ihlali olmadan entegre edilebilir mi? Değilse "tiktik" → "diktek" gibi yanlış/doğru çiftleri doğrulanmış kayıt olarak eklenebilsin
- **Düzeltme (önceki raporlara):** bu bilgisayarda Word 2016/365 KURULU (`WINWORD.EXE`, Word.Application.16). Daha önce "Word yok" denmişti; yalnızca .docx dosyası olmadığına bakılmıştı
- Ölçümler (geçici `comtypes` ile, sonra kaldırıldı):
  - Word COM otomasyonu çalışıyor; Türkçe yazım (MSSP7TR.LEX) ve dilbilgisi (MSGR8TR.LEX) sözlükleri kurulu. Ama Word'ün görünmez açılışı 52 sn sürdü ve Türkçe dilbilgisi denetimi "Herkez … gelecekler ama ben gelemiyeceğim cünkü" cümlesinde hiçbir dilbilgisi hatası bulamadı (yalnızca yazım: Herkez, gelemiyeceğim, cünkü)
  - Windows Yazım Denetimi API'si (ISpellCheckerFactory, Windows 8+ ile gelen resmî API): tr-TR destekleniyor; yazım hataları ve öneriler Word'ünkiyle BİREBİR aynı (aynı Microsoft Türkçe sözlüğü), anında, çevrimdışı, Word gerektirmiyor
  - "tiktik" Word'e göre DOĞRU bir kelime → dikte bir kelimeyi başka geçerli bir kelimeye çevirdiğinde hiçbir yazım denetimi yakalayamaz; bunu yalnızca yanlış → doğru kaydı çözer
- Hukuki değerlendirme: Word'ün sözlük dosyalarını (.LEX) kopyalayıp uygulamaya koymak lisans ihlali olur. Kullanıcının kendi lisanslı Word'ünü masaüstünde otomasyonla çağırmak ihlal değildir ama uygulamayı Word'e bağımlı ve çok yavaş yapar. Windows'un yazım denetimi API'si her uygulamanın kullanması için sunulmuştur — önerilen yol
- **Uygulandı — doğrulanmış dikte düzeltmeleri:**
  - Belgede bir kelimeye sağ tık → "Dikte Sözlüğü" alt menüsü → "Dikte Düzeltmesi Olarak Kaydet…" (seçim yoksa tıklanan kelime). Pencere akıllı dolar: kelime dikte edildiği gibi duruyorsa "yanlış" alanına ("tiktik"), metinde zaten düzeltildiyse Whisper'ın orijinalde tanıdığı hal "yanlış", seçili kelime "doğru" olarak ("Sözçük" → "Sözcük"); elle yazılmış metinde seçili kelime "doğru" alanına. Kaydedilince belgedeki yanlış kelime de düzeltilir
  - Doğrulanmış kayıt hemen etkin olur (iki kez görülmeyi beklemez) ve doğru hali ("diktek") tanımaya ipucu olarak da verilir — model kelimeyi zamanla ilk seferde doğru duysun diye
  - Kullanıcı dikte edilen metinde düzeltme yapınca bilgi çubuğunda soru çıkar: "Sözcük dikte düzeltmenizi öğrendi: “Yıldırm” → “Yıldırım”. Sonraki diktelerde hemen otomatik düzeltilsin mi?" — "Evet, Doğrula" / "Hayır, Öğrenme" (hayır: kayıt ve öğrenilen kelime silinir; cevapsız bırakılırsa 2. görülüşte etkinleşir)
  - Sözlük penceresinde kaynak "Doğrulandı" / "Öğrenildi", düğme "Doğrula"
- **Testte bulunup düzeltilen hata:** dikte edilen bölümü izleyen imleç, kullanıcı dikteden hemen sonra yazmaya devam edince büyüyordu (elle yazılan metin de "dikte edilmiş" sayılıyordu); ilk düzeltme denemesinde ise ilk/son kelime değiştirilince yeni hali bölüm dışında kalıyordu. `TrackedRange` sınıfı yazıldı (başlangıç eklemede yerinde kalır, bitiş son karakterle izlenir); 8 senaryonun 8'i doğru: arkaya yazma, hemen arkasına ekleme, ortadaki/ilk/son kelimeyi düzeltme, son kelimenin kısalması, arkada metin varken ve arkaya yazıp sonra düzeltme
- Test: sağ tıkla doğrulanmış kayıt + belgede düzeltme + sonraki diktede 2 düzeltmenin otomatik uygulanması; öğrenme sorusu ve "Evet" (hemen etkin) / "Hayır" (silindi) yolları; önce metinde düzeltip sonra sağ tık (orijinal otomatik bulundu, aynı düzeltme için ikinci kez soru sorulmadı); elle yazılmış metin; gerçek modelle dikte regresyon testi; ekran görüntüleri incelendi
- Öneri (kullanıcı kararı bekliyor): Windows Yazım Denetimi API'si ile yazarken canlı kırmızı dalgalı çizgi ve sağ tıkta öneriler (Word ile aynı Türkçe sonuçlar, çevrimdışı, ücretsiz). Dikte sözlüğündeki kelimeler yazım denetiminde hata sayılmaz, yazım denetiminden "Sözlüğe ekle" aynı sözlüğe yazar — tek kişisel sözlük. Dilbilgisi için Gemini denetimi kalır (Word'ün Türkçe dilbilgisi denetimi testte hata bulamadı)

## [2026-09-17] — Windows yazım denetimi eklendi, Gemini entegrasyonu kaldırıldı
- Neden: kullanıcı önerilen Windows yazım denetimini onayladı ve Gemini entegrasyonunun kaldırılmasını istedi
- **Gemini kaldırıldı:** `ai.py`, `assistant.py` (Yardımcı paneli, API anahtarı penceresi), komut çubuğundaki "Yardımcı" düğmesi, sağ tık "Yardımcı" alt menüsü, panelin stil kuralları ve ikonları silindi. `google-genai` ve `keyring` sanal ortamdan ve requirements.txt'ten çıkarıldı. Ayarlardaki `assistant` ve `gemini_model` kayıtları temizlendi; Windows Kimlik Bilgisi Yöneticisi'nde kayıtlı bir Gemini anahtarı yoktu. Artık uygulamada hiçbir metin buluta gönderilmiyor
  - Yan etki: Gemini ile yapılan dilbilgisi denetimi ve düzelt/geliştir/özetle özellikleri yok
- **Windows yazım denetimi eklendi:**
  - `spellengine.py`: Windows Yazım Denetimi API'si (ISpellCheckerFactory, `comtypes` ile); motor 0,14 sn'de hazır. Türkçe dil paketi yoksa ya da Windows dışında kibar biçimde devre dışı kalır, uygulama çalışmaya devam eder
  - `spellcheck.py`: yazarken canlı kırmızı dalgalı çizgi. Değişen paragraf yazmaya 350 ms ara verilince denetlenir; yazılmakta olan kelime, kelime bitene kadar işaretlenmez (Word gibi); başka paragrafa geçince hemen denetlenir
  - Sağ tık: öneriler kalın (Windows önerileri kelimenin büyük harfine uyarlıyor: "Herkez" → "Herkes"); tekrarlanan kelime için "Tekrarlanan Kelimeyi Sil" ("ve ve"); "Tümünü Yoksay" (oturum boyunca); "Sözlüğe Ekle". Öneriler yalnızca sağ tıklanınca hesaplanır (kelime başına ~60 ms)
  - Durum çubuğunda "5 yazım hatası" düğmesi: "Yazarken Yazım Denetimi" aç/kapa (hatırlanır), "Sonraki Yazım Hatası" (F7: hatayı seçer ve önerileri açar), "Yoksayılan Kelimeleri Sıfırla"
  - **Tek kişisel sözlük:** dikte sözlüğündeki kelimeler ve doğrulanmış düzeltmelerin doğru halleri yazım denetiminde hata sayılmaz; Türkçe ekli halleri de ("Ataberk'e"). Yazım denetiminden "Sözlüğe Ekle" aynı sözlüğe yazar ve kelime dikteye de ipucu olur. Sözlük değişince ilgili çizgiler anında kalkar. Sözlük artık pencere düzeyinde tek nesne; dikte ve yazım denetimi paylaşır
  - Belge açılınca tam tarama: önce ekranda görünen bölümden başlar, arayüzü dondurmamak için 25 ms'lik dilimlere bölünür
- Editör bulgu altyapısı yeniden düzenlendi (`Issue`): birden çok öneri, öneriler tembel hesaplanır, paragraf başına toplu güncelleme, sıralı listede ikili arama, yalnızca görünen bölümdeki çizgiler çizilir, düzenlemede yalnızca değişen yerdeki bulgular yoklanır
- **Testte bulunup düzeltilen hatalar (büyük belge, 1400 paragraf ≈ 200 sayfa):**
  - Belge yükleme 275 sn sürüyordu. Profil: sürenin %97'si sözcük/karakter sayacındaydı — her değişiklikte tüm belgenin karakterleri Python'da tek tek sayılıyordu (Faz 1'den beri var olan hata; yükleme sırasında 2.800 kez). Karakter sayımı C düzeyine taşındı, sayaç yazmaya ara verilince güncelleniyor → yükleme **3,8 sn**
  - Yükleme sırasında her paragraf ayrı değişiklik sayılıp sonra tek seferde (arayüzü dondurarak) denetleniyordu; `bulk_loading` bayrağı eklendi, yükleme sonrası tek zaman dilimli tarama yapılıyor. Çok paragraf birden değişirse (büyük yapıştırma, geri alma) de zaman dilimli taramaya aktarılıyor
  - Bulgu listesi her paragraf denetiminde baştan filtrelenip sıralanıyordu (karesel); yalnızca ilgili dilim değiştiriliyor
  - Kaynak dosyalarda görünmez Unicode karakterler (U+2028, U+2029, U+FFFC) dize sabitlerinin içine gerçek karakter olarak girmişti (dictation.py, docx_io.py, tables.py, editor.py); kaçış dizilerine çevrildi, sözdizimi ağacının değişmediği doğrulandı
- Ölçümler (200 sayfalık belge): tam tarama 16,6 sn arka planda; bu sırada olay döngüsü gecikmesi medyan 36 ms, en kötü 144 ms (yazma ve tıklama akıcı); tuş vuruşu 19–24 ms; 4.200 hatalı belgede ekran çizimi 63 ms
- Test: yazarken işaretleme ve yazılan kelimenin beklenmesi; öneri uygulama; tekrarlanan kelimeyi silme; Tümünü Yoksay; Sözlüğe Ekle (kişisel sözlüğe ve dikte ipucuna girdi); sözlükteki kelimenin ekli hali; F7; kapat/aç; büyük belge performansı; ekran görüntüleri incelendi. Önceki özelliklerin testleri (doğrulanmış dikte düzeltmeleri, tablolar, yakınlaştırma, cetvel, docx, gerçek modelle dikte) yeniden çalıştırıldı
- requirements.txt: `comtypes` eklendi; `google-genai`, `keyring` çıkarıldı
- Bilinen sınırlar: dilbilgisi denetimi yok; "Tümünü Yoksay" yalnızca açık oturum için (kalıcı olması için "Sözlüğe Ekle"); Windows'un Türkçe dil bileşeni olmayan bilgisayarlarda yazım denetimi devre dışı kalır (durum çubuğunda nedeni yazar)

## [2026-09-17] — Dikey cetvelle üst/alt kenar boşluğu + Türkçe yazım bileşenini uygulama içinden ekleme
- **Dikey cetvel sürüklenebilir oldu** (kullanıcı bildirimi: yatay cetvel çalışıyordu, dikey yalnızca gösterimdi):
  - İmlecin bulunduğu sayfanın gri/beyaz sınırları sürüklenerek belgenin üst ve alt kenar boşlukları ayarlanır (Word gibi). Sınırın üzerine gelince ↕ imleci ve değer ipucu; sürüklerken sayfa genişliğince yatay kılavuz çizgi ve "Üst kenar boşluğu: 3,25 cm"; 0,25 cm'ye yapışır, Alt ile serbest; sayfada en az 3 cm yazı alanı kalır. Bırakınca belge yeniden sayfalanır ve kaydedilmemiş sayılır
  - Kenar boşlukları artık sabit değil belgeye ait (`styles.page_margins` / `set_page_margins`, QTextDocument dinamik özelliği): .docx'e yazılır, .docx'ten okunur (Word'de ayarlanmış kenar boşlukları da gelir), PDF dışa aktarma ve yazdırmaya yansır. Yeni belge tam 2,5 cm (yuvarlanmış 94 px değil — yoksa .docx'e 2,49 cm yazılırdı)
  - Test (gerçek fare olaylarıyla): üst 4 cm, alt 1,5 cm; ilk satır sayfada aşağı kaydı; yapışma (3,13 → 3,25) ve Alt ile serbest (3,13); aşırı sürükleme sınırı; .docx gidiş-dönüşü 4,0/1,5 cm; PDF'te ilk satır 4,10 cm'de (4 cm + harf payı); ekran görüntüsü incelendi
  - Kapsam dışı: sol/sağ kenar boşlukları (yatay cetvel paragraf girintilerini ayarlıyor) ve her sayfaya ayrı kenar boşluğu (Word'de de bölüm düzeyindedir)
- **Türkçe yazım bileşenini uygulama içinden ekleme:**
  - Risk değerlendirmesi: uygulamanın kendi yazım denetimini açıp kapatmak zaten vardı ve risksiz. Windows'ta Türkçe bileşeni olmayan bilgisayarlarda bileşeni eklemek sistem değişikliğidir; ölçüldü: yönetici izni gerektiriyor (normal kullanıcıyla sorgu bile "yükseltme gerekiyor" veriyor). Eklenen Microsoft'un resmî "Türkçe temel yazma" isteğe bağlı özelliği (`Language.Basic~~~tr-TR~0.0.1.0`): ekran dilini ve klavye düzenini değiştirmez, Ayarlar'dan kaldırılabilir. Önlemlerle düşük riskli bulundu ve uygulandı
  - `winlang.py`: sabit, kullanıcı girdisi içermeyen tek PowerShell komutu (`Add-WindowsCapability`) Windows'un UAC onayıyla yükseltilmiş çalışır; Sözcük'ün kendisi yönetici olarak çalışmaz. Bekleme arka planda
  - Bileşen eksikse durum çubuğu "Türkçe yazım denetimi yüklü değil" der; menüde "Türkçe Yazım Denetimini Windows'a Ekle…" (önce riskleri açıklayan onay penceresi, sonra UAC), "Windows Dil Ayarlarını Aç", "Yeniden Dene". Kurulum sürerken "Türkçe yazım denetimi ekleniyor…"; başarıda yeniden başlatmadan etkinleşir ve belge denetlenir; UAC reddinde "hiçbir değişiklik yapılmadı"; indirme/politika hatasında açıklama + Dil Ayarları düğmesi; bileşen eklendi ama görünmüyorsa "Sözcük'ü yeniden başlatın"
  - Test: süreç başlatma/bekleme/çıkış kodu mekanizması yükseltmesiz zararsız komutlarla doğrulandı; kurulum komutunun sözdizimi PowerShell ayrıştırıcısıyla doğrulandı (çalıştırılmadı); tüm akış sahte kurucuyla test edildi (bileşen yok görünümü, Vazgeç'te hiçbir şey çalışmaması, UAC reddi, başarısız indirme, yeniden başlatma gereği, başarılı kurulum sonrası çizgilerin gelmesi, Yeniden Dene)
  - Bilinen durum: gerçek kurulum bu bilgisayarda denenmedi (Türkçe zaten yüklü ve UAC penceresi kullanıcının ekranında açılırdı)
- Önceki özelliklerin testleri yeniden geçti (yazım denetimi ve büyük belge, tablolar, yakınlaştırma, yatay cetvel, docx, doğrulanmış dikte düzeltmeleri)

## [2026-09-17] — Görseller (ekleme, boyutlandırma, kırpma, döndürme) ve Simge ekleme
- **Görsel ekleme** (`images.py`, komut çubuğunda "Resim" düğmesi): Dosyadan Resim Ekle… (çoklu seçim, son klasör hatırlanır), panodan yapıştırma (ekran görüntüsü, tarayıcıdan kopyalanan görsel, Gezgin'de kopyalanan görsel dosyaları), Gezgin'den ya da tarayıcıdan sürükle-bırak. Çok büyük fotoğraflar en uzun kenar 2400 px'e indirilir (belge şişmesin), görsel yazı alanına sığacak boyutta eklenir ve hemen seçilir. Açılamayan dosyalar adıyla bildirilir
- **Seçme ve boyutlandırma** (Word gibi): görsele tıklayınca mavi çerçeve ve 8 tutamak; köşeler en-boy oranını korur (Shift ile serbest), kenarlar tek yönde; yazı alanından büyüyemez. Esc seçimi bırakır; Sil/Kes/Kopyala/üzerine yazma normal çalışır (seçim, görselin metindeki karakteridir). Seçili görsel metin seçimi rengiyle boyanmaz
- **Kırpma**: "Kırp" ile Word'deki kalın siyah kırpma tutamakları çıkar, kırpılacak kısım soluk görünür; Enter ya da dışarı tıklama uygular, Esc vazgeçer. "Kırpmayı Sıfırla" özgün görseli geri getirir (kırpma kayıpsızdır)
- **Döndürme**: Sağa/Sola 90° (menü ve sağ tık) ve fareyle: görselin üstündeki dairesel ok tutamağı sürüklenir, sürüklerken yarı saydam önizleme; Shift ile 15° adımlar. 90'ın katları kayıpsız; diğer açılarda köşeler saydam kalır. "Döndürmeyi Sıfırla". Kırpılmış görsel döndürülebilir, döndürülmüş görsel kırpılabilir
- Tasarım: özgün görsel hiç bozulmaz; biçimde özgün görsel + açı + kırpma dikdörtgeni saklanır, görünen görsel bunlardan üretilir. Her işlem tek adımda Geri Al/Yinele ile geri alınır. .docx'e görünen (döndürülmüş/kırpılmış) hali PNG olarak yazılır — Word'de de aynı görünür
- **Simge ekleme** (`symbols.py`, "Ω Simge" düğmesi): Word gibi son kullanılan 20 simgelik ızgara + "Diğer Simgeler…" penceresi: 12 kategori (Sık Kullanılanlar, Noktalama ve Tipografi, Para Birimleri — ₺ dahil, Matematik, Oklar, Yunan Harfleri, Şekiller, İşaretler ve Semboller, Kutu Çizgileri, ASCII Karakterleri, Latin Harfleri, Emoji), Türkçe arama ("tl", "derece", "yıldız", "ok"), İngilizce Unicode adı ve U+20BA gibi kodla arama, büyük önizleme, ad ve kod; çift tık/Enter/Ekle ile ekler, pencere açık kalır. Simge imlecin yazı biçimiyle sıradan karakter olarak eklenir; son kullanılanlar hatırlanır
- Test: 33/33 (panodan/dosyadan/dosya yolundan ekleme, fareyle köşe ve kenar boyutlandırma, geri al, sağa/sola 90° piksel yönü, kırpma ve içerik doğrulaması, kırpılmış görseli döndürme, sıfırlamalar, fareyle 90° ve Shift'le 30° döndürme, tıklama/Esc/Delete, .docx gidiş-dönüşü, simge arama ve ekleme, ASCII kategorisi); ekran görüntüleri ve menüler incelendi; önceki testler (yazım denetimi, dikte aralığı) yeniden geçti
- Ölçüm notu: 200 sayfalık belgede tuş vuruşu bu ölçümde ~85 ms çıktı; görsel aracı kapatılınca da aynı — süre Qt'nin metin yerleşiminde, bu değişiklikten kaynaklanmıyor. İleride incelenebilir
- Bilinen sınırlar: görseller satır içidir (metin görselin etrafından akmaz, sayfada serbest konumlandırma yok); .docx'ten açılan görsellerde döndürme/kırpma bilgisi yoktur, görünen hali özgün sayılır

## [2026-09-17] — Sayfa Düzeni düğmesi ve özelleştirilebilir komut çubuğu
- **Sayfa Düzeni** (komut çubuğunda yeni düğme, `page_setup.py`): Word'ün Düzen sekmesindeki gibi
  - Kenar Boşlukları: Normal (2,5), Dar (1,27), Orta, Geniş hazır ayarları + "Özel Kenar Boşlukları…"
  - Yönlendirme: Dikey / Yatay (Word gibi kenar boşlukları da sayfayla birlikte döner)
  - Boyut: A4, A5, A3, B5 (JIS), Letter, Legal, Executive + "Diğer Kâğıt Boyutları…"
  - Sayfa Yapısı penceresi: dört kenar boşluğu, yönlendirme, kâğıt listesi ya da özel genişlik/yükseklik, canlı önizleme, sığmayan değerler için uyarı. Menüde belgenin geçerli ayarları işaretli görünür
- Altyapı değişikliği: sayfa boyutu ve sol/sağ kenar boşlukları artık sabit (A4, 2,5 cm) değil, üst/alt boşluklar gibi belgeye ait (`styles.page_size`, `all_margins`, `set_page_setup`). Editör sayfalaması, sayfa çizimi, cetveller (paragraf girintileri sol boşluktan ölçülür), görsel sığdırma, yakınlaştırma (Sayfa Genişliği/Tam Sayfa), yazdırma ve PDF (kâğıt boyutu ve yatay yönlendirme yazıcıya aktarılır), .docx yazma/okuma (kâğıt boyutu, yönlendirme, dört kenar boşluğu — Word'de ayarlanmış belgeler de doğru açılır) buna göre güncellendi. Yeni belge A4, dikey, 2,5 cm. En az 3 cm yazı alanı korunur
- **Komut çubuğunu özelleştirme**: çubuğun sağındaki özelleştir düğmesi ya da çubuğa sağ tık → gruplar (Yazı Tipi, Karakter Biçimi, Paragraf, Listeler ve Girinti, Ekle ve Sayfa, Sesle Yazma, Yazı Tipleri) ve her düğme için işaretli göster/gizle, grup başına Tümünü Göster/Gizle, "Komut Çubuğunu Özelleştir…" penceresi (ikonlu, gruplu işaret kutuları) ve "Varsayılana Sıfırla". Seçim hatırlanır (QSettings `commandbar/hidden`). Gizlenen düğmelerin klavye kısayolları çalışmaya devam eder (Ctrl+B testle doğrulandı); tümü gizlenen grubun ayırıcısı da gizlenir
- **Taşma**: pencere darsa sığmayan düğmeler sağdaki » menüsünde grup grup listelenir (tablo, resim, simge, sayfa düzeni, renkler ve satır aralığı alt menü olarak; Sesle Yaz ve seçenekleri). Qt'nin QToolBar taşma düğmesi bu yerleşimde açılmadığı (12 px'lik boş düğme) için komut çubuğu kendi yerleşimini yapan `CommandBar` bileşeniyle değiştirildi. Düğmeler tıklanınca odak metinde kalır
- Test: 27/27 (A4 varsayılanı, yatay çevirme ve metin genişliği, Geniş hazır ayarı, cetvel girintileri, A5, sığmayan boşluğun sıkıştırılması, .docx'e yatay Legal ve dört boşluk yazma ve geri okuma, PDF sayfa boyutu 35,56×21,59 cm, yeni belgenin varsayılana dönmesi, menü işaretleri, Sayfa Yapısı penceresi, düğme gizleme, gizli düğmenin kısayolu, ayırıcılar, yeniden açılışta hatırlama, sıfırlama, dar pencerede » ve içeriği, geniş pencerede » gizli); ekran görüntüleri incelendi (düzeltilen: yazı tipi boyutu kutusunun yanındaki düğmeyle çakışması, » düğmesindeki fazladan ok). Önceki testler yeniden geçti (görseller 33/33, yazım denetimi, Türkçe bileşen kurulum akışı, dikte sözlüğü)
- Bilinen sınırlar: sol/sağ kenar boşlukları cetvelden sürüklenemez (menü/pencereden ayarlanır; yatay cetvel paragraf girintileri içindir); tüm belge için tek sayfa yapısı (Word'deki bölüm başına farklı ayar yok); düğmelerin sırası değiştirilemez, yalnızca gösterilip gizlenebilir

## [2026-09-17] — Yardım ve Nasıl Kullanılır
- **Uygulama içi yardım** (`help.py`, içerik `sozcuk/yardim.md`): `F1`, başlık şeridinin sağındaki **?** düğmesi ya da **Dosya → Yardım ve Nasıl Kullanılır** ile açılan ayrı pencere. Solda ikonlu konu listesi, sağda biçimli içerik (başlıklar, kenarlıklı tablolar, kısayollar vurgulu), üstte arama
- 18 konu: Başlarken, Yenilikler, Dosya İşlemleri, Metin Biçimlendirme, Paragraflar ve Listeler, Cetveller, Sayfa Düzeni, Tablolar, Resimler, Simgeler, Kopyalama ve Yapıştırma, Yazım Denetimi, Sesle Yazma (Dikte), Dikte Sözlüğü, Görünüm ve Yakınlaştırma, Komut Çubuğunu Özelleştirme, Klavye Kısayolları, Gizlilik ve Sorun Giderme. İçerik kodla karşılaştırılarak yazıldı (menü adları, hazır ayar değerleri, kısayollar, uyarı metinleri)
- Arama Türkçe büyük/küçük harf kurallarıyla çalışır (İ/ı), sonuçlar ilgiye göre sıralanır (başlıkta geçen, sonra geçme sıklığı), eşleşmeler sarıyla vurgulanır ve ilkine kaydırılır; "Bkz." bağlantıları ilgili konuyu açar. Son açılan konu hatırlanır; pencere tek örnek, belgeyle yan yana açık kalabilir
- **Bakım kuralı:** her yeni özellikte `yardim.md`'de ilgili konu güncellenir, "Yenilikler"e tarihli madde eklenir, yeni kısayol "Klavye Kısayolları" tablosuna yazılır. Dosyanın başında yazım kuralları var; içerik Markdown olduğu için kod bilgisi gerekmeden düzenlenebilir
- Test: 13/13 (konuların yüklenmesi, ikonlar, tüm iç bağlantıların geçerliliği, **yardımda geçen her kısayolun uygulamada gerçekten tanımlı olması** — ileride yardım ile uygulama ayrışırsa test yakalar, F1, konu açma, arama ve vurgulama, Türkçe büyük harf araması, sonuç yok durumu, bağlantı, tablo kenarlıkları, tek pencere, son konunun hatırlanması); ekran görüntüleri incelendi (düzeltilen: aramada ilk eşleşmenin mavi seçim rengiyle görünmesi). Sayfa düzeni/komut çubuğu testleri yeniden geçti (27/27)

## [2026-09-17] — Plan: Google Drive / OneDrive ile eşitlenerek çalışma (değerlendirme)
- Kullanıcı isteği plan.md'ye **Faz 5** olarak eklendi; kod değişikliği yok
- Değerlendirme: bu bilgisayarda Google Drive masaüstü uygulaması ("Drive'ım" sürücüsü) ve OneDrive klasörü kurulu. En sağlam yol, bu eşitleme klasörleri üzerinden çalışmak (5A). Gereken işler: güvenli kaydetme (bugün dosyanın doğrudan üzerine yazılıyor), dosya başka yerde değişirse bunu fark etme, bulut göstergesi, çakışma kopyalarını bildirme. Doğrudan hesap bağlantısı (Graph / Drive API, 5B) mümkün ama geliştirici kaydı, OAuth ve gizlilik ilkesinde değişiklik gerektiriyor. Word Online / Google Dokümanlar tarzı aynı anda ortak canlı düzenleme gerçekçi değil
- Sonraki adım: kullanıcı onayıyla 5A

## [2026-09-17] — Faz 5A: Google Drive / OneDrive ile canlı kayıt
- Kullanıcı netleştirdi: Google Dokümanlar gerekmiyor; Sözcük yerelde çalışacak, istenen Drive'a erişim ve çalışırken canlı kayıt. API ve hesap bağlantısı olmadan, Google Drive masaüstü uygulamasının sürücüsü üzerinden uygulandı (bu bilgisayarda G:\Drive'ım, "Google Drive" etiketli birim; OneDrive: %OneDrive%)
- `cloud.py`: bulut klasörlerini bulma (birim etiketi "Google Drive" + Drive'ım/My Drive klasörü, eski yansıtma modu klasörleri, OneDrive ortam değişkenleri), dosyanın hangi bulutta olduğu, Google biçimli dosyalar (.gdoc/.gsheet/.gslides), `ChangeTracker` (boyut + değişiklik zamanı yoklaması; imza değişince içerik özeti karşılaştırılır — eşitleme uygulaması yalnızca tarihi değiştirirse çakışma sayılmaz)
- **Canlı kayıt:** bulut klasöründeki belgede otomatik kayıt yazmaya 2 sn ara verilince (yerel belgede 4 sn). Başlıkta "Google Drive'a kaydediliyor… / kaydedildi / kaydedilemedi", ipucunda eşitlemeyi Drive uygulamasının yaptığı açıklaması; durum çubuğunda saniyeli son kayıt saati
- **Güvenli kayıt:** geçici dosya adı `~$sozcuk-…` oldu (eşitleme uygulamaları "~$" dosyalarını buluta göndermez); yerine koyma, dosya eşitleme sırasında kilitliyse 8 kez / 0,25 sn aralıkla yeniden denenir; hata olursa geçici dosya silinir. Kayıt başarısızsa kurtarma kopyası yazılır ve 10 sn sonra kendiliğinden yeniden denenir
- **Başka yerde değişiklik** (3 sn'de bir yoklama): yerelde kaydedilmemiş değişiklik yoksa yeni sürüm sessizce yüklenir (imleç ve kaydırma korunur); varsa otomatik kayıt durur, başlıkta "Başka yerde değiştirildi — otomatik kayıt bekliyor", bildirim çubuğunda Onların Sürümünü Yükle / Benimkini Kaydet / Benimkini Ayrı Kaydet
- Dosya menüsü: "Google Drive'dan Aç…", "Google Drive'a Kaydet…" (ve OneDrive karşılıkları); yalnızca o bulut bilgisayarda varsa görünür. .gdoc açılmak istenirse içeriğin yalnızca Google sunucusunda olduğu açıklanır, "Tarayıcıda Bul" Drive'da adıyla arar ve .docx'e indirme yolu anlatılır
- Yardım: yeni "Google Drive ve OneDrive" konusu (durum tablosu, çakışma seçenekleri, .gdoc, sınırlar), Yenilikler, Dosya İşlemleri tablosu, Gizlilik ve Sorun Giderme güncellendi
- Test: 21/21 — gerçek algılama (G:\Drive'ım ve OneDrive bulundu; kullanıcının Drive'ına yazılmadı) + sahte Drive klasöründe: açma ve durum, 2 sn canlı kayıt, geçici dosya kalmaması, yalnızca tarihi değişen dosyanın çakışma sayılmaması, sessiz yeni sürüm yükleme, çakışma bildirimi ve bekleme durumu, çakışmada otomatik kaydın üzerine yazmaması, Benimkini Kaydet, Onların Sürümünü Yükle, kilitli dosyada yeniden deneme, yazılamayınca kurtarma kopyası ve 10 sn sonra kendiliğinden kayıt, .gdoc, menü, yerel dosyada eski davranış. Yardım 13/13, sayfa düzeni 27/27, görseller 33/33 yeniden geçti
- Bilinen sınırlar: gerçek Google Drive'a yazılarak denenmedi (kullanıcının bulutuna test dosyası göndermemek için); Drive'ın buluta gönderip göndermediği Sözcük'ten görülmez (Drive uygulaması simgesinden izlenir); eşitleme çakışma kopyaları ("Belge (1).docx") ayrıca bildirilmiyor; iki sürüm satır satır birleştirilmiyor

## [2026-09-17] — Drive canlı kayıt doğrulandı; .gdoc açıklaması ve "Tarayıcıda Aç"
- Kullanıcı gerçek Drive'da denedi: Sözcük'te Drive'dan açıp düzenlenen belge kaydediliyor, telefondan güncel hali görülüyor (Faz 5 elle doğrulandı)
- .gdoc incelemesi (bu bilgisayarda, içerik okunmadan): dosya 183 bayt görünüyor ama Google Drive uygulaması okumaya izin vermiyor ("Yanlış işlev"); belge kimliği bile okunamıyor. İçerik yalnızca Google sunucusunda; API olmadan Sözcük açamaz
- Windows'ta .gdoc, Google Drive uygulamasına ilişkilendirilmiş (`GoogleDriveFS.exe --open_gdoc`). "Tarayıcıda Bul" (adıyla arama) yerine **"Tarayıcıda Aç"**: dosya bu ilişkilendirmeyle açılır, belge doğrudan Google Dokümanlar'da açılır; olmazsa Drive araması. Bildirim metni ve yardımdaki .gdoc bölümü (neden açılamadığı, .docx'e indirme, toplu indirme, yüklemeleri dönüştürmeyi kapatma) güncellendi
- Test: bulut 22/22, yardım 13/13

## [2026-09-17] — Plan: Word'ün açtığı diğer biçimler (değerlendirme)
- Kullanıcı: yalnızca .docx ve .pdf açılıyor, eski Word biçimleri bile yok. plan.md'ye **Faz 6** eklendi; kod değişikliği yok
- Bu bilgisayarda Word 16 kurulu, LibreOffice yok. Word arka planda görünmeden çalıştırılarak ölçüldü: Word'ün açılışı 6,4 sn, .docx→.doc 1,4 sn, →.rtf 0,55 sn, →.odt 0,39 sn, .doc→.docx 0,2 sn, Türkçe içerik korundu; deneme bitince Word kapandı. Ek kütüphane gerekmiyor (`comtypes`)
- Qt yerleşik olarak HTML, ODF, Markdown ve düz metin yazabiliyor (.odt kaydetme hazır); .doc/.wps/.wpd için biçimlendirmeyi okuyan uygun lisanslı saf Python kütüphanesi yok → Word, yoksa LibreOffice ile dönüştürme, ikisi de yoksa .doc için yalnızca metin
- Sonraki adım: kullanıcı onayıyla önerilen sırayla başlamak

## [2026-09-17] — Faz 6: Word'ün açtığı diğer biçimler
- Kullanıcı önerilen sırayı onayladı; hepsi uygulandı
- **Ek program gerektirmeyenler:** .docm/.dotx/.dotm (paketin içerik türü bellekte .docx'e çevrilir; makrolar okunmaz/çalışmaz; şablonlar Word gibi yeni adsız belge olarak açılır), .txt (BOM, UTF-8, BOM'suz UTF-16, Windows-1254 algılama), .htm/.html (Qt HTML içe aktarımı; `<img>` yerel yolları ve data: adresleri çözülüp resimler belgeye gömülür, internet resimleri alınmaz; Word'ün "•+boşluk" liste maddeleri gerçek listeye çevrilir; tablolara kenarlık), .mht/.mhtml (MIME bölümleri, Content-Location/CID ile resimler)
- **Kendi okuyucularımız:** `odt_io.py` (stil zinciri, başlık düzeyleri, hizalama/girinti/aralık, karakter biçimleri, iç içe listeler, birleştirilmiş hücreli tablolar, Pictures/ resimleri, sayfa yapısı) ve `rtf_io.py` (kod sayfaları ve \\u Unicode ile Türkçe, yazı tipi/renk tabloları, stil adından başlık, listeler, tablolar, PNG/JPEG resimler, alan sonuçları, sayfa yapısı; üst/alt bilgi, dipnot, WMF/EMF bildirilir)
- **Eski biçimler** (.doc, .dot, .xml Word 2003, .wps, .wpd): `converters.py` — kurulu Microsoft Word COM ile (yoksa LibreOffice --headless, geçici profille) arka planda görünmeden .docx'e çevirip açma. Güvenlik: makrolar zorla kapalı (AutomationSecurity), salt okunur, son kullanılanlara eklenmez, uyarı yok, parola sorulmaz; kullanıcının açık Word'üne bağlanılırsa Word kapatılmaz. Dönüştürme ayrı iş parçacığında, arayüz donmaz. Ölçüm: .doc açma 4,3-4,9 sn, .xml 5,6 sn (Word'ün başlaması dahil)
- **Word/LibreOffice yoksa:** `doc_text.py` — [MS-DOC] FIB + parça tablosundan metin (olefile, BSD lisans; requirements.txt'e eklendi); alan kodları atılır, tablo hücreleri sekme/satır. Diğer eski biçimlerde LibreOffice indirme bağlantısı
- **İçerikten tür algılama:** adı .doc ama içeriği RTF/.docx olan dosyalar doğru okuyucuyla (Word'süz, anında) açılır; eski biçim uzantılı ama içeriği tutmayan dosyalar Word'e verilmez (Word her dosyayı düz metin sanıp açabiliyor — testte yakalandı)
- **Açma güvenliği:** dosya önce ayrıştırılır, hata verirse açık belgeye dokunulmaz; kendi okuyucumuz bir .rtf/.odt'yi açamazsa Word/LibreOffice ile denenir
- **Uyumluluk Modu:** .docx dışı belgede başlıkta "Uyumluluk Modu (.doc)" ve bildirim; otomatik kayıt dosyaya yazmaz (kurtarma kopyası); Kaydet'te Word Belgesi (.docx) önerilir, istenirse özgün biçimde (kaybolacaklar yazılır)
- **Farklı Kaydet:** .docx, .doc ve .rtf (Word/LibreOffice ile), .odt (Qt ODF yazıcısı), .txt (UTF-8), .html (resimler "_dosyalar" klasörüne); biçim kaybı uyarısı. Aç penceresi: "Tüm Desteklenen Belgeler", "Tüm Word Belgeleri" ve biçim başına filtreler
- Düzeltme: Word'ün eski belgelerden dönüştürdüğü .docx'lerdeki VML resimler (w:pict/v:imagedata) artık okunuyor (önce ad alanı hatası veriyordu)
- Yardım: yeni "Dosya Biçimleri" konusu (biçim tablosu, Word/LibreOffice ile açma ve güvenlik, Uyumluluk Modu, Farklı Kaydet biçimleri), Yenilikler, Dosya İşlemleri, Sorun Giderme
- Test: Word'e kendi kaydettirdiğimiz gerçek örnek dosyalarla (başlık, kalın/italik/renk, ortalı paragraf, liste, tablo, resim, Türkçe) 39/39 — 12 biçimi açma (metin, başlık, kalın, liste, tablo, resim; şablonların adsız açılması; Uyumluluk Modu), .odt/.txt/.html/.rtf/.doc olarak kaydedip geri açma, html resim klasörü, eski biçimde otomatik kaydın dosyaya yazmaması, Kaydet'te .docx önerisi ve özgün biçimde kaydetme, Word/LibreOffice yokken .doc metni ve .wps uyarısı ve kaydetme listesi, bozuk .rtf ve .doc'ta açık belgenin korunması, adı .doc olan RTF. Önceki testler yeniden geçti (yardım 13, bulut 22, sayfa düzeni 27, görseller 33). Testlerde başlatılan Word her seferinde kapandı
- Bilinen sınırlar: .odt kaydında başlık stilleri ve sayfa yapısı yazılmıyor; LibreOffice yolu bu bilgisayarda kurulu olmadığı için gerçek LibreOffice ile denenmedi; Word her dönüştürmede yeniden başlıyor (~4-5 sn); boş tablo hücresi olan .doc'ta metin yedeği satırı erken bölebilir

## [2026-09-17] — İki satırlı ve sürüklenebilir komut çubuğu + menü şeridi
- **Komut çubuğu iki satır:** `CommandBar` yerleşimi yeniden yazıldı; düğmeler sığmazsa ikinci satıra yayılır (MAX_ROWS=2), pencere genişleyince tek satıra döner, iki satıra da sığmayanlar » menüsünde kalır. Ayırıcılar artık ayrı öğeler değil, grup değişimine göre çizilir (sıralama değişince kendiliğinden doğru yere gelir)
- **Sürükleyerek sıralama:** düğmeler sürüklenip bırakılarak yeniden sıralanır; bırakma yeri mavi çizgiyle gösterilir. Menüsü olan düğmeler (tıklayınca menü açtığı için) `Alt` ile sürüklenir; menüsüz düğmeler doğrudan. Sıra QSettings `commandbar/order` içinde saklanır; "Düğme Sırasını Sıfırla" ile varsayılana döner
- **Menü şeridi:** başlığın altında Word tarzı menüler — Dosya (başlıktan buraya taşındı), Düzen (geri al/yinele, kes/kopyala/yapıştır, tümünü seç, sonraki yazım hatası; seçime göre etkinleşir), Biçim (stiller, karakter biçimleri, boyut, renkler, hizalama, satır aralığı, listeler, temizle, yazı tipi ekle), Ekle (tablo, resim, simge, sesle yaz), Sayfa Düzeni (kenar boşlukları, yönlendirme, boyut, Sayfa Yapısı…), Görünüm (cetvel, yakınlaştırma, çubuk özelleştirme), Yardım. Menüler komut çubuğundaki eylemleri paylaşır: düğme gizlense de komut menüde durur. `Tümünü Seç` (Ctrl+A) editöre eklendi
- Test: 22/22 — menü başlıkları ve içerikleri, Düzen menüsünün seçime göre etkinleşmesi, Biçim'den kalın ve punto, Sayfa Düzeni menüsünden yatay/A5/dar kenar boşluğu, Görünüm'den cetvel ve sayfa genişliği, Yardım'dan kısayollar konusu, dar pencerede iki satır ve geniş pencerede tek satır, sürükle-bırakla sıralama (kaydedilmesi, yeniden açılışta korunması, sıfırlanması), Alt ile menülü düğme sürükleme, gizlemenin iki satırda çalışması. Ekran görüntüleri incelendi
- Yardım: yeni "Menüler" konusu, "Komut Çubuğunu Özelleştirme" (iki satır, sürükleme) ve "Başlarken" güncellendi

## [2026-09-19] — Bul ve Değiştir
- Word'de olup bizde olmayan özellik eklendi (`find.py`): `Ctrl+F` arama şeridi, `Ctrl+H` değiştirme alanları, `F3`/`Shift+F3` sonraki/önceki, `Esc` kapatır; Düzen menüsünde ve komut çubuğunda (yeni "Bul ve Değiştir" grubu) düğmeleri
- Arama belge blokları üzerinde yapılır (tablo hücreleri dahil); büyük/küçük harf duyarsız aramada **Türkçe kuralları** kullanılır (İ↔i, I↔ı) — Qt'nin kendi find'ı bunu yanlış yapıyor. Seçenekler: Aa (harf duyarlı), Tam sözcük
- Tüm eşleşmeler sayfada sarıyla, geçerli eşleşme turuncuyla boyanır: `Editor.set_highlights` + `paint_highlights` (metnin altına, yalnızca görünen bölüm için satır satır dikdörtgen hesabı; `_range_rects` bulgular için de kullanılabiliyor). Şeritte "3 / 12" sayacı, sonuç yoksa kırmızı "Sonuç yok"
- Değiştir: geçerli eşleşmeyi değiştirip sonrakine geçer. Tümünü Değiştir: eşleşmeler **sondan başa** değiştirilir (konum kayması yok) ve tek `beginEditBlock` içinde yapılır → `Ctrl+Z` hepsini birden geri alır; biçim korunur; değiştirilen metin aranan metni içerse bile (serin → serinserin) sonsuz döngü olmaz
- Metinde seçili sözcük varsa `Ctrl+F` onu arama kutusuna yazar; belge değişince eşleşmeler kendiliğinden yenilenir
- Test: 23/23 — Türkçe harf duyarsızlığı (İstanbul/istanbul/İSTANBUL ve Ilık/ılık), harf duyarlı ve tam sözcük seçenekleri, tablo içindeki metin, şeridin açılması, sayaç, ileri/geri gezinme ve başa dönme, vurguların çizilmesi ve temizlenmesi, sonuç yok durumu, Değiştir/Tümünü Değiştir, tek adım geri alma, biçim koruma, kendini içeren değiştirme, Esc, seçili sözcükle açılma, menü ve düğmeler. Ekran görüntüsü incelendi
- Yardım: yeni "Bul ve Değiştir" konusu, Yenilikler, Klavye Kısayolları (Ctrl+F, Ctrl+H, F3, Shift+F3) ve Menüler güncellendi

## [2026-09-19] — Sayfa numarası
- Word'de olan, bizde olmayan sayfa numarası eklendi (`page_numbers.py`). Kapsam bilinçli olarak dar: tam üst bilgi/alt bilgi düzeni yok, yalnızca sayfa numarası
- **Ayar belgeye ait** (QTextDocument dinamik özellikleri, styles.page_size gibi): açık/kapalı, konum (alt/üst × sol/orta/sağ — 6 hazır konum), biçim ("1", "Sayfa 1", "1 / 12"), başlangıç numarası. Yeni belgede kapalı; `Editor.set_page_numbers` değişikliği belgeyi kaydedilmemiş sayar
- **Metnin parçası değil:** numara belgenin akışına eklenmez, sayfanın kenar boşluğuna çizilir; kullanıcı tıklayıp yazamaz. Ekranda `PageBackground` (sayfa ve gölge çizimiyle aynı yerde), yazdırma ve PDF'te `Editor.print_document` sayfaları tek tek basıp numarayı ekler (numara kapalıyken eski hızlı yol korunur). "1 / 12" biçimi durum çubuğundaki sayfa sayısını kullanır
- **.docx yazma:** Word'ün kendi alanı olarak — alt/üst bilgi parçasında `PAGE` ve gerektiğinde `NUMPAGES` alan kodları (fldChar begin/separate/end), hizalama `w:jc`, başlangıç numarası `w:pgNumType w:start`. Word'de açılınca canlı alan kalır, sayfa eklenince kendiliğinden güncellenir
- **.docx okuma:** üst/alt bilgideki PAGE alanı tanınır ve ayara çevrilir; hizalama sırasıyla `w:jc`, Word'ün sayfa numarası çerçevesi (`w:framePr w:xAlign`) ve alt bilgi stilindeki sekmelerden (1 sekme orta, 2 sekme sağ) anlaşılır — gerçek Word çıktısı incelenerek eklendi. Sayfa numarası içeren alt bilgi artık "desteklenmeyen öğe" uyarısı vermiyor
- Arayüz: **Sayfa Düzeni → Sayfa Numarası** alt menüsü (aç/kapat, Konum, Biçim, Başlangıç Numarası… penceresi); menü belgenin geçerli ayarını işaretli gösterir, kapalıyken konum/biçim menüleri sönük
- Test: 34/34 — varsayılanın kapalı olması, biçim ve başlangıç numarası metinleri, ekrana çizimin piksel doğrulaması (alt orta/alt sağ/üst sol hizalama, ikinci sayfada da çıkması, kapatınca kaybolması), metne eklenmediğinin doğrulanması, PDF'te her sayfada numara ve başlangıç numarası, .docx'e PAGE/NUMPAGES alanı ve pgNumType yazımı, kendi yazdığımız dosyanın geri okunması, **Word'ün kendisiyle oluşturulan** sayfa numaralı belgenin (çerçeveli, sağa hizalı, 4'ten başlayan) doğru okunması ve uyarı vermemesi, menü seçenekleri ve durum eşitlemesi. Ekran görüntüleri incelendi
- Yardım: "Sayfa Düzeni" konusuna "Sayfa Numarası" bölümü, Yenilikler ve Menüler güncellendi
- Not: plan.md'de "Görsel Kalite Standardı" başlığı yok; "Notlar / Kararlar" bölümündeki "arayüz kalitesi Office Word seviyesinde olmalı" ilkesi izlendi (20 px ızgara ikon, Word tarzı menü yapısı, sade pencere)

## [2026-09-19] — Bağlantılar (köprü)
- Yeni `links.py`: köprü biçimi (Word rengi #0563C1, altı çizili), adres çözümleme/normalleştirme, belge içi hedefler ve bağlantı penceresi
- **Hedef türleri:** web/e-posta (`https://`, `www.` ve `ad@yer` kendiliğinden tamamlanır, `mailto:`), **belge içi sayfa/satır** (`sozcuk:sayfa=2&satir=5` — "2. sayfanın 5. satırı"), Word belgelerinden gelen **yer imleri** (`sozcuk:yerimi=AD`)
- Sayfa/satır haritası belgenin yerleşiminden çıkarılır (`links.line_positions`): her satırın hangi sayfada kaçıncı satır olduğu; hedef yoksa en yakınına gidilir. Bağlantı penceresi imlecin bulunduğu sayfa/satırla açılır
- **Kullanım:** `Ctrl+K` (Ekle menüsü ve komut çubuğunda zincir düğmesi) bağlantı ekler ya da imleçteki bağlantıyı düzenler; pencerede "Bağlantıyı Kaldır" da var. **Ctrl + tıklama** açar (web tarayıcıda, belge içi hedef imleci oraya götürür), fare üzerindeyken hedefi ipucu gösterir, sağ tık menüsünde Aç / Düzenle / Kaldır
- **Yazarken kendiliğinden bağlantı:** adres yazıp boşluk ya da Enter'a basınca köprüye çevrilir (Word gibi); tek geri-al adımı
- Köprünün hemen başında/sonunda yazılan metin köprüye katılmaz (`Editor._drop_link_format`) — Qt biçimi kendiliğinden sürdürdüğü için eklendi
- **.docx yazma:** web adresleri ilişki (`r:id`, TargetMode="External") ile, belge içi hedefler ise hedef paragrafa konan `w:bookmarkStart` ve `w:hyperlink w:anchor` ile yazılır; yer imi adı sayfa/satırı taşır (`sozcuk_s3_r4`), böylece geri okunduğunda aynı hedef olur
- **.docx okuma:** `w:hyperlink` (dış adres ya da anchor) köprüye çevrilir; belgedeki `w:bookmarkStart` konumları eşlenir, böylece Word'ün yer imlerine giden bağlantılar Sözcük'te de çalışır
- Test: 29/29 — adres normalleştirme ve çözümleme, biçim (renk/alt çizgi), sayfa/satır haritası ve gezinme (3. sayfa 4. satıra gitme, görünür olması), yalnızca sayfa hedefi, Ctrl + tıklama (tarayıcı çağrısı yakalandı), sağ tık menüsü ve kaldırma, pencere çıktıları ve düğme durumları, yazarken kendiliğinden köprü, .docx'te ilişki/anchor/bookmark yazımı ve geri okunması, **gerçek Word**'ün kaydettiğimiz dosyadaki köprüleri tanıması (Hyperlinks koleksiyonu) ve Word'de yapılmış köprünün Sözcük'te okunması, menü/düğme. Ekran görüntüleri incelendi
- Yardım: yeni "Bağlantılar" konusu, Yenilikler, Klavye Kısayolları (Ctrl+K, Ctrl+tıklama) ve Menüler güncellendi

## [2026-09-19] — Çeviri (yerel)
- Kullanıcı isteği: API anahtarı olmadan çeviri, mümkünse Microsoft altyapısıyla. Araştırma sonucu: Word'ün Çevir komutu ve Bing Çeviri bulut hizmetidir (abonelik anahtarı ister, metni Microsoft sunucusuna gönderir); Windows'un cihaz üzerinde çeviri API'si yalnızca Copilot+ bilgisayarlarda ve 24H2'de var — bu bilgisayarda Windows 11 21H2 ve NPU'suz Intel i5-4210U. Microsoft Translator'ın çevrimdışı dil paketleri yalnızca kendi uygulamalarında. Bu yüzden, dikte modelinde olduğu gibi, yerel açık kaynak model seçildi
- `translate.py`: Argos Translate (MIT) + OPUS-MT/Argos modelleri (CC-BY-4.0; yardımda kaynak belirtildi). Ölçüm: en↔tr paketleri 125/121 MB, ilk çeviri (model yükleme dahil) 5-7 sn, sonraki paragraflar ~1 sn; ctranslate2 zaten faster-whisper ile kurulu
- Modül: kurulu/indirilebilir dil çiftleri, Türkçe dil adları, paket indirme+kurma, satır/paragraf yapısını koruyan çeviri, Türkçe dil sezgisi. Not: Python'da `re.IGNORECASE` "İ" ile "i"yi eşleştirdiği için sezgi yanlış çalışıyordu; harf ve kelime desenleri ayrıldı (testte yakalandı)
- Arayüz: **Çeviri penceresi** (Ctrl+Shift+T) — kaynak/hedef dil, ⇄ ile yer değiştirme, sol/sağ metin alanları, Çevir / Seçimin Yerine Koy / Panoya Kopyala; çeviri ve indirme arka planda (arayüz donmaz), durum satırında ilerleme ve "metin bilgisayarınızda çevrildi" bilgisi. Seçim varsa seçili metin, yoksa belgenin tamamı alınır; hedef dil hatırlanır
- Yeni **Gözden Geçir** menüsü (yazarken yazım denetimi, sonraki hata, dikte sözlüğü, çeviri) ve komut çubuğunda küre düğmesi
- requirements.txt: `argostranslate>=1.9`
- Test: 22/22 — bileşen ve kurulu çiftler, dil listesi ve Türkçe adlar, dil sezgisi, tr→en ve en→tr çeviri (paragraf yapısıyla), aynı dilde değişmeme, pencerenin açılması, seçim/tam belge alınması, pencereden çeviri, Seçimin Yerine Koy ve geri alma, dilleri değiştirme, hedef dilin hatırlanması, menü ve düğme. Ekran görüntüsü incelendi
- Yardım: yeni "Çeviri" konusu (kullanım, ilk indirme, gizlilik, Microsoft'un çevirisinin neden kullanılmadığı), Yenilikler, Menüler, Klavye Kısayolları ve Gizlilik bölümü güncellendi
- Bilinen sınırlar: çeviri düz metindir (kalın/renk gibi biçimler çeviri sonrası korunmaz, seçimin biçimi neyse o uygulanır); dil paketleri yalnızca İngilizce üzerinden (tr→de gibi doğrudan çiftler listede yoksa indirilemez); eski işlemcide uzun belgelerde çeviri yavaş olabilir

## [2026-09-19] — Çeviri dil paketleri: uygulamaya gömme ve toplu indirme
- Kullanıcı sorusu: dokuz dil (İngilizce, Almanca, Fransızca, İspanyolca, Rusça, Çince, Japonca, Hintçe, Korece) uygulamaya gömülsün mü? **Ölçüm:** çeviri yönlü olduğu için dil başına iki paket gerekiyor; indirme adreslerinden ölçülen boyutlar: tr↔en 246 MB, en↔de 302, en↔fr 132, en↔es 373, en↔ru 352, en↔zh 145, en↔ja 237, en↔hi 209, en↔ko 240 → **hepsi 2,23 GB**. Uygulamayı 2,3 GB yapmak yerine iki yol birden kuruldu
- **Gömülü paketler:** `sozcuk/diller/` klasörüne konan `.argosmodel` dosyaları ilk kullanımda kendiliğinden kurulur (kullanıcı indirmez, internet gerekmez); paketlenmiş .exe sürümde uygulamanın yanındaki `diller` klasörüne de bakılır. Şu an gömülü: Türkçe⇄İngilizce ve Türkçe⇄Fransızca (377 MB) — istenen diller `araclar/dil_paketleri_indir.py` ile tek komutla eklenebilir (`--hepsi` 2,23 GB)
- **Dil Paketleri penceresi** (Gözden Geçir menüsü ve çeviri penceresindeki düğme): her dil için hazır mı, değilse kaç MB; işaretle ve **Seçilenleri İndir** (arka planda, ilerleme bilgisiyle). Çeviri penceresindeki hedef dil listesinde de indirilecek boyut yazıyor
- **İngilizce üzerinden çeviri:** tr→de gibi doğrudan paketi olmayan çiftler için yalnızca eksik paket(ler) indirilir (`missing_packages`); tr→fr denemesi doğrulandı (8,5 sn ilk çeviri, sonrası hızlı)
- Test: 19/19 — gömülü klasörün bulunması ve paketlerin kurulması, paket adından dil çifti çıkarma, İngilizce üzerinden tr→fr çevirisi, eksik paket ve boyut hesapları, Dil Paketleri penceresinin listesi/durumu/seçimi, menü ve düğmeler. Ekran görüntüsü incelendi
- Düzeltme: çeviri penceresinde hedef dillerin tamamı "(indirilecek)" görünüyordu (kaynak dil "Otomatik" iken kurulu çiftler yanlış hesaplanıyordu); artık hazır diller sade, ötekiler boyutuyla yazılıyor
- Yardım: "Çeviri" konusuna dil paketleri bölümü ve boyut tablosu eklendi

## [2026-09-19] — Gömülü diller: Almanca, İtalyanca, İspanyolca
- Kullanıcı kararı: Fransızca gömülüden çıksın; **Almanca, İtalyanca ve İspanyolca** gömülü gelsin, diğerleri indirilebilir kalsın
- `sozcuk/diller/` içeriği güncellendi: Türkçe⇄İngilizce (pivot dil, zorunlu) + en⇄de, en⇄it, en⇄es — 8 paket, toplam **1,1 GB** (de 151+151, it 88+87, es 88+285, tr/en 121+125). Fransızca paketleri klasörden silindi (indirilebilir listede kaldı, ≈132 MB)
- Ölçülen boyut düzeltmesi: İtalyanca paketleri tahmin edilen 102 MB yerine 88/87 MB; `PACKAGE_SIZES` güncellendi. Arayüzdeki dil sırası gömülüler önce gelecek biçimde değiştirildi
- Doğrulandı: gömülü paketler kendiliğinden kurulduktan sonra tr→de, tr→it, tr→es çevirileri çalışıyor (İngilizce üzerinden; ilk çeviri 6-20 sn, sonrası hızlı)
- Yardım: dil tablosu ve "uygulamayla gelir" bilgisi güncellendi

## [2026-09-19] — Faz 4: Künye, ikon, .exe paketi, kurulum paketi ve GitHub
- **Künye:** `sozcuk/__init__.py` içinde sürüm (1.0) ve "Developed By Usta ve Ata"; Yardım → **Sözcük Hakkında** penceresi (sürüm, künye, gizlilik notu, kullanılan açık kaynak bileşenler ve lisansları)
- Düzeltme: künye önce `QApplication.setOrganizationName` ile de atanmıştı; bu, Windows'un kullanıcı verisi klasörünü `%APPDATA%\Developed By Usta ve Ata\Sözcük` yapıyor ve mevcut ayarları/kişisel sözlüğü öksüz bırakıyordu. Geri alındı, oluşan boş klasör silindi (paketlenmiş sürüm denemesinde yakalandı)
- **İkon:** `araclar/ikon_uret.py` — Word mavisi şeritli sayfa ve "S"; 16-256 px altı boyutlu gerçek ICO (PNG gömülü). İlk denemede QBuffer geçici QByteArray ile çöküyordu, düzeltildi
- **PyInstaller** (`sozcuk.spec`): klasör biçiminde paket, `dist/Sozcuk/` 2,0 GB. Yardım metni ve `sozcuk/diller/*.argosmodel` pakete gömülür; gereksiz Qt modülleri dışlanır. Paketlenmiş sürümde veri dosyalarının yolu için `sozcuk.resource_dir()` eklendi (PyInstaller `_MEIPASS`); `help.HELP_FILE` ve `translate.bundle_dirs()` bunu kullanıyor
- **Inno Setup** (`kurulum/sozcuk.iss`): `dist/Sozcuk-1.0-kurulum.exe` 1,31 GB. Türkçe sihirbaz, Başlat menüsü kısayolu, isteğe bağlı masaüstü kısayolu ve .docx ilişkilendirmesi, "Birlikte aç" listesine kayıt, kaldırma
- **Denemeler:** paketlenmiş .exe belge açarak sınandı (13 paragraf, yazım denetimi hazır, hata kaydı yok); paket içi yollar ayrı bir testle doğrulandı (yardım metni + 8 dil paketi bulunuyor, 24 yardım konusu okunuyor); kurulum paketi geçici klasöre sessizce kurulup çalıştırıldı (1,90 GB, pencere başlığı "ornek.docx - Sözcük"), sonra sessizce kaldırıldı ve kayıt defteri girdisinin kalmadığı doğrulandı
- **GitHub:** depo başlatıldı, `.gitignore` (venv, build/dist, *.argosmodel — GitHub 100 MB sınırı), `README.md` (özellikler, çalıştırma, paketleme, bileşen lisansları) eklendi ve https://github.com/ataeyvaz/sozcuk adresine `main` dalı olarak yüklendi. Commit kimliği gizlilik için GitHub noreply adresiyle
- Bilinen sınırlar: paket ve kurulum dosyası dil paketleri yüzünden büyük (2,0 GB / 1,31 GB); dilsiz bir sürüm için `sozcuk/diller` boşaltılıp yeniden derlemek yeterli. Kurulum paketi imzalanmadı: Windows SmartScreen ilk çalıştırmada uyarı gösterebilir

## [2026-09-21] — Sürüm 1.1: paketi küçültme, dilleri kurulumda seçme, temizlik
- Kullanıcı isteği: paket ve kurulu hal çok büyüktü (2,0 GB / kurulum 1,31 GB). Yalnızca Türkçe⇄İngilizce gömülü kalsın, diğer diller Inno Setup'ta seçilsin; kurulum test edilsin, sonra işe yaramayanlar temizlensin
- **Ölçüm (eski paket):** 1,1 GB gömülü dil paketi, 371 MB torch, ~120 MB spacy/thinc/blis, 66 MB PyAV. Ayrıca eski sürüm gömülü paketleri ilk açılışta `~\.local\share\argos-translate` içine açıp kopyalıyordu → kullanıcıda **~3 GB**
- **Çeviri motoru sadeleştirildi (`translate.py`):** Argos Translate kütüphanesi yerine doğrudan CTranslate2 + SentencePiece (BPE kullanan 1.9 paketleri için Moses + Argos'un `apply_bpe.py`'si → `sozcuk/apply_bpe.py`, MIT). Argos yalnızca cümle bölmek için torch/stanza/spacy getiriyordu; yerine kısaltma listeli basit bölücü. Aynı `.argosmodel` paketleri, **açılmış klasör** olarak okunur, hiçbir yere kopyalanmaz. Aranan yerler: `sozcuk/diller/` (gömülü), `Sozcuk.exe` yanındaki `diller/` (kurulumda seçilenler), `%LOCALAPPDATA%\Sözcük\diller` (sonradan indirilenler)
- Eski ve yeni motor aynı cümlelerde karşılaştırıldı: çıktılar birebir aynı; ilk çeviri 28 sn → 1,4 sn (stanza yüklemesi yok). Eskiden "Dr." kısaltması "Home" diye çevriliyordu, düzeldi
- **Hata düzeltmeleri (eskide de vardı):** (1) `compute_type="auto"` bu işlemcide int8'e çeviriyor, İspanyolca 1.9 paketi int8'de anlamsız çıktı veriyordu ("mainstre@@…") → `"default"`. (2) en→fr 1.9 paketinde "▁" metinde kalıyordu → temizleniyor. (3) İndirme sunucusu (argos-net.com) Python'un varsayılan kimliğine 403 veriyor → `User-Agent: Sozcuk`
- **Dikte:** faster-whisper açılışta PyAV'ı içe aktarıyor ama yalnızca dosyadan ses çözmek için kullanıyor; biz ham ses verdiğimiz için pakete konmuyor, yerine boş modül (`dictation._stub_av`)
- **`sozcuk.spec`:** yalnızca tr⇄en gömülü (stanza/ klasörü alınmaz); torch, stanza, spacy, argostranslate, av vb. dışlandı; kullanılmayan Qt parçaları süzüldü (yazılım OpenGL 20 MB, QML/Quick'i sürükleyen sanal klavye eklentisi, Qt PDF/Network, dil dosyaları)
- **`kurulum/sozcuk.iss` (Inno Setup 6.5+):** "Standart" ve "Özel" kurulum; Özel'de 11 dil (Almanca, İtalyanca, İspanyolca, Fransızca, Rusça, Çince, Japonca, Hintçe, Korece, Arapça, Portekizce). Seçilen diller `[Files]` `download extractarchive` ile Argos sunucusundan indirilip `{app}\diller`'e açılır (`ArchiveExtraction=full`; hedef ad `.zip` olmalı, arşiv türü uzantıdan tanınıyor — ilk denemede bu yüzden "Unknown ArchiveFileName extension" hatası). Yükseltmede eski `_internal` silinir, indirilmiş diller korunur; kaldırmada `diller` de silinir. Sürüm 1.1
- **Sonuç:** `dist/Sozcuk/` 2,0 GB → **498 MB** (257 MB'ı tr⇄en modelleri); kurulum 1,31 GB → **309 MB**
- **Denemeler:** paketlenmiş halde çeviri (tr→en, en→tr 1,1 sn) ve dikte (21 sn, doğru metin) ayrı bir deneme programıyla sınandı; kurulum geçici klasöre sessizce kuruldu (Fransızca seçili: 2 paket indirildi ve açıldı, 668 MB), kurulu uygulamanın Fransızcayı bulduğu ve fr→tr / tr→fr çevirdiği doğrulandı; aynı klasöre yükseltme (diller korundu), kurulu .exe'nin açılması ("Belge1 - Sözcük"), sessiz kaldırma (klasör ve kayıt defteri girdisi kalmadı). Uygulama içinden indirme (Dil Paketleri) de sınandı
- **Temizlik:** `.venv`'den çeviri/Gemini dönemi kalıntısı 58 paket kaldırıldı (torch, spacy, stanza, argostranslate, pydantic, google-auth…; 1,9 GB → 1,0 GB, `pip check` temiz); `sozcuk/diller/*.argosmodel` (1,1 GB), eski `Sozcuk-1.0-kurulum.exe` (1,3 GB) ve `build/` silindi. Proje klasörü 4,3 GB → 2,1 GB. `requirements.txt`, `README.md`, `araclar/dil_paketleri_indir.py` (artık yalnız tr⇄en'i açılmış olarak indirir), yardım (Yenilikler + Çeviri) güncellendi
- Eski sürümün `~\.local\share\argos-translate` klasörü (1,2 GB, artık kullanılmıyor) kullanıcı onayıyla silindi
- Açık kalan: kurulum indirmelerinde SHA-256 denetimi yok (HTTPS'e güveniliyor)

## [2026-09-21/22] — Faz 7: Sesli okuma (Türkçe telaffuz + Ata'nın sesiyle Piper modeli)

### Karar: neden kendi sesimizi eğitiyoruz
- Kullanıcı şartı: doğal, kaliteli Türkçe **kadın ve erkek** ses, **bulut API yok**. Bu bilgisayarda (i5-4210U, 2 çekirdek, 8 GB, 2014) ölçüldü: **Piper (VITS)** 8 sn sesi 2 sn'de üretiyor (kullanılabilir); **MOSS-TTS-Nano** 13 sn sesi 3 dk'da ve Türkçesi bozuk; **Chatterbox** yalnızca yüklenmesi 8,5 dk; **FreyaTTS** tek (kadın) ses, torch; **XTTS-v2 / OmniVoice** yavaş ve ticari kullanıma kapalı → hepsi elendi
- Hazır Türkçe Piper sesleri (dfki, fahrettin, fettah, 99eren99) kullanıcı tarafından "robotik ve aksanlı" bulundu — üçü de İngilizce lessac sesinden az Türkçe veriyle türetilmiş. Lisans: dfki CC BY-NC-SA, fettah/fahrettin CC0 veri
- Kullanıcının `Desktop\BabaKartalVoice` projesinde kendi sesiyle 273 kayıt (27 dk) ve XTTS ince ayarlı bir model var (oğlu Kartal'a miras amaçlı). XTTS doğal ama 7,2x yavaş ve 2 GB → **XTTS'i değil, kayıtları** kullanıp hızlı bir Piper modeli eğitmeye karar verildi

### Türkçe telaffuz (`sozcuk/pronunciation.py`)
- Piper metni espeak-ng ile ses birimine çeviriyor; espeak GPL (uygulamayı GPL yapardı) ve Türkçede yanlışları var ("Dr." → "dere", "konuşmaya"yı olumsuzluk sanıyor, "hâlâ"yı kalın l ile okuyor) → kendi kodumuz
- Kurallar tahminle değil ölçümle çıkarıldı: espeak'in 5.600 kelimelik Türkçe çıktısı üretildi, harfler ses birimleriyle hizalandı, bağlam istatistikleri çıkarıldı. Sonuç: kapalı hecede e→ɛ (l/m/n önünde æ), i→ɪ, o→ɔ, u→ʊ, ü→ø; l kalın ünlü yanında ɫ; r iki ünlü arasında ɾ; g ince ünlü yanında ɟ; ğ e/i'den sonra j, ı'dan sonra ɯ, diğer ünlüleri uzatır; çift patlamalı ünsüz Cː, çift sürekli CC
- Vurgu: kural son hece + vurgusuz ek listesi (-ma/-me olumsuzluğu, -yor, -dır, -ken, -(y)la, -sa, -ca, -sınız, ortaç -dığ/-acağ, gereklilik -malı) + kendi vurgusunu taşıyan sözcük sözlüğü (şimdi, Ankara…)
- Ölçüm: espeak ile ses birimi uyumu **%96**, vurgu uyumu **%78**. İncelenen farklarda çoğunlukla espeak yanlış ("almaz" → ALmaz, "arama" → araMA, "belge" ince g)
- Metin hazırlama: sayı (bin/milyon, ondalık, sıra sayısı), saat, tarih, yüzde, para/birim, kısaltma sözlüğü, büyük harfli kısaltmaların harf harf okunması (THY → te he ye; NATO sözcük gibi)
- Doğrulama: fettah modeliyle üretilen ses Whisper'a yazdırıldı, metin neredeyse birebir geri geldi

### Sözcük tarafı
- `read_aloud.py`: ses modeli klasörleri (uygulama içi / exe yanı / `%LOCALAPPDATA%\Sözcük\sesler`), onnxruntime ile sentez, `sounddevice` ile çalma, bir sonraki cümleyi arka planda hazırlama (kuyruk), duraklat/durdur, ses ve hız menüsü, ilk yüklemede "ses hazırlanıyor" bilgisi (model ilk açılışta ~12 sn yükleniyor)
- Okunan cümle açık maviyle vurgulanır (`editor.set_reading_range`), görünür tutulur; belge değişirse okuma durur
- Kısayol `Ctrl+Alt+Space`, komut çubuğunda hoparlör düğmesi, Gözden Geçir menüsünde. Yardım konusu eklendi

### Eğitim hattı (Kaggle)
- Colab yerine **Kaggle**: tarayıcı kapalıyken de çalışıyor, haftada 30 sa ücretsiz GPU (Colab kullanıcının 25 dk'lık eğitimini öldürmüştü). Giriş: `kaggle auth login` (OAuth; anahtar dosyası gerekmez)
- Veri seti (özel): `ataeyvaz/sozcuk-ata-ses-verisi` — `wav/` + `metadata.csv` (`utt|ses birimleri`, bizim dönüştürücümüzle) + `pronunciation.py`. Eğitim `--data.phoneme_type text` ile bu ses birimlerini kullanır: eğitim ve uygulama aynı dönüştürücü → eski Piper denemesini bozan fonem uyuşmazlığı imkânsız
- Kernel'ler: `sozcuk-ata-ses-egitimi` (pilot, 3 sa) ve `sozcuk-ata-ses-egitimi-2` (devam, 8 sa; `kernel_sources` ile öncekinin `last.ckpt`'ini girdi alır). Betik ve araçlar projede: `araclar/ses_egitimi/` (bkz. oradaki BENIOKU.md)
- Betikteki tuzak kapatmaları (BabaKartalVoice Colab notlarından + yenileri): `torch.load` gevşek kip, `val_mos` geri çağrımının kaldırılması, ONNX eski dışa aktarıcı, eski checkpoint ayarlarının süzülmesi, **devam ederken Timer durumunun silinmesi** (yoksa `max_time`ın bir kısmı harcanmış sayılır), indirilen arşivin `.zip` uzantısıyla kaydedilmesi (Inno gibi Kaggle da türü uzantıdan tanıyor)
- Önce 3 dakikalık deneme koşusu yapıldı (kurulum hatalarını 3 saatlik kotayı yakmadan görmek için)

### Sonuçlar
- Pilot (3 sa): kelime hatası **%21**. Devam (toplam 11 sa): **%13** (Whisper + Levenshtein ile ölçüldü)
- Kullanıcı dinledi: ses kendisine benziyor; **%25 yavaş** (`length_scale 1.25`) tercih edildi, ses json'una varsayılan olarak yazıldı. Model `%LOCALAPPDATA%\Sözcük\sesler\ata.onnx`'e kuruldu (pilot yedeği yanındaki klasörde)
- Kalan kusur: **"Kartal"** ince okunuyor (a'lar e'ye kaçıyor). Sebep: kelime 273 cümlenin hiçbirinde geçmiyor; dönüştürücü doğru veriyor (`kartˈaɫ`), model tahmin ediyor. noise_scale düşürme ve hitap vurgusu denendi, fark etmedi → **çözüm: kullanıcının o kelimeyi kendi sesiyle kaydetmesi**

### Kayıt uygulaması (BabaKartalVoice, kullanıcı onayıyla değiştirildi)
- `docs/prompts_tr.txt` sonuna 28 cümle eklendi: "Kartal" (16), "Beşiktaş" (5), kalın ünlüler (7) → 301 cümle. Yedek: `docs/prompts_tr.yedek-2026-09-22.txt`
- Gmail ve Drive APK'yı "virüs" diye engelledi. İnceleme: kod Ağustos'taki APK ile **birebir aynı** (896 dosyadan yalnızca cümle metni değişmiş), tek izin RECORD_AUDIO, internet izni yok → yanlış alarm. Muhtemel sebep: herkeste aynı olan **"Android Debug" imzası** + hata ayıklama işareti
- Çözüm: **yayın sürümü, kullanıcıya özel anahtarla** (`android-recorder/imza/babavoice-yayin.jks`, şifre `imza.properties`, ikisi de .gitignore'da — **YEDEKLENMELİ**, kaybolursa güncelleme kurulamaz). `allowBackup=false` + `dataExtractionRules` (kayıtlar Google yedeğine gitmesin), sürüm 0.2.0, `build_apk.ps1` artık `assembleRelease` yapıyor ve bellek darlığı için Gradle'ı 1 GB + tek süreçte çalıştırıyor. Değiştirilen dosyaların eski halleri: `yedek-2026-09-22/`
- Kurulum: Gmail yayın sürümünü de engelledi → **adb** ile kuruldu. Önce telefondaki 275 dosya bilgisayara çekilip MD5 ile doğrulandı (`telefon-yedek-2026-09-22/`), sonra eski uygulama kaldırılıp 0.2.0 kuruldu. Xiaomi'de ilk iki deneme `INSTALL_FAILED_USER_RESTRICTED` verdi: telefon ekranı açık olmalı ve çıkan onay penceresi onaylanmalı
- Google'ın "geliştirici doğrulaması" araştırıldı (Eylül 2026 Brezilya/Endonezya/Singapur/Tayland, 2027 dünya): hobi/öğrenci için **ücretsiz sınırlı dağıtım hesabı** (20 cihaz, kimlik istemiyor), tam hesap 25 dolar; **adb ile kurulum muaf**. Türkiye'de henüz zorunlu değil

### Buradan devam (kullanıcı 28 kaydı yaptıktan sonra)
1. Kayıtları çek (Git Bash'te `export MSYS_NO_PATHCONV=1`):
   `adb pull /sdcard/Android/data/com.kartal.babavoice/files <hedef>`
2. BabaKartalVoice veri setine ekle (mevcut kayıtlara dokunmadan): `scripts/prepare_dataset.py`
3. Kaggle veri klasörünü üret ve yükle: `araclar/ses_egitimi/veri_hazirla.py`, sonra `kaggle datasets version -p <klasör> -r zip -m "28 yeni kayıt"`
4. `araclar/ses_egitimi/egitim.py`'yi `TRAIN_HOURS=3` ve `kernel_sources = ["ataeyvaz/sozcuk-ata-ses-egitimi-2"]` ile yeni bir kernel'e gönder (`sozcuk-ata-ses-egitimi-3`)
5. Çıktıyı indir, Whisper ile ölç, "Kartal"ı dinle
6. Beğenilirse: ses `sozcuk/sesler/` altına, `sozcuk.spec`'e (+63 MB), yardım "Yenilikler"e; hepsi tek commit
7. Kadın sesi: aynı hat, rızası olan bir kadın aynı uygulamayla cümleleri okur

### Commit durumu
- 2026-09-23: kod, yardım ve eğitim araçları `43a8fde` ile commit edildi (`pronunciation.py`, `read_aloud.py`, `editor.py`, `icons.py`, `window.py`, `yardim.md`, `araclar/ses_egitimi/`). Geçici `va.png` silindi
- Ses modeli henüz pakete konmadı: yalnızca `%LOCALAPPDATA%\Sözcük\sesler` altında kurulu

## [2026-09-24] — Faz 7: yeni kayıtlarla 3. eğitim turu (14 saat)
- Kullanıcı 28 yeni cümlenin 27'sini kaydetti ("Maç başladı, kartal forma giydik…" dilbilgisi bozuk olduğu için bilerek atlandı). Kayıtlar `adb` yerine zip ile geldi (`babakartalvoice-kayitlar.zip`)
- BabaKartalVoice: kayıtlar `raw-recordings`'e eklendi (yedek: `transcript.yedek-2026-09-24.csv`, `dataset/metadata.yedek-2026-09-24.csv`); `prepare_dataset.py` → 300 kayıt, 29 dk 47 sn, hepsi denetimden geçti (medyan sinyal/gürültü 31 dB)
- `veri_hazirla.py` → `BabaKartalVoice\kaggle-veri`; Kaggle veri seti yeni sürümü yüklendi. Not: Kaggle CLI (2.2.4) Windows'ta `-p C:/...` yolunda hata veriyor, klasöre girip `-p .` kullanılmalı. CLI bu bilgisayarda kurulu değildi, geçici bir sanal ortama kuruldu
- Kernel `sozcuk-ata-ses-egitimi-3`: `kernel_sources` = `-2`, `TRAIN_HOURS = 3` (toplam 14 sa). 17:51'de bitti
- **Ölçüm** (yeni betik; 16 cümle, hiçbiri eğitimde yok, her model 3 tur — ses modeli her okumada biraz farklı ürettiği için): eski (11 sa) kelime hatası **%25,8**, yeni (14 sa) **%27,4** → fark ölçüm gürültüsü içinde, anlamlı iyileşme yok. "Kartal" kelimesi yenide 9 okumanın 9'unda "Kartal" duyuldu (eskide 6/9: "karta", "kartta"); "Kartal'a bal" ve "Galatasaray'la" yenide daha kötü. Önceki %13 farklı cümle/yöntemle ölçülmüştü, doğrudan karşılaştırılamaz
- **Kullanıcı dinledi: yeni ses eskisinden daha iyi → kuruldu** (`%LOCALAPPDATA%\Sözcük\sesler\ata.onnx`; uygulamanın `find_voices` yoluyla yüklendiği ve okuduğu doğrulandı, `length_scale 1.25` korundu). Whisper ölçümü farkı yakalamadı; "Kartal"daki ince a sorunu kulakla değerlendirildi
- Yeni model `%LOCALAPPDATA%\Sözcük\sesler\aday-14saat-2026-09-24\`, eski model yedeği `…\yedek-11saat-2026-09-24\`. Dinleme dosyaları: `BabaKartalVoice\ses-denemesi-2026-09-24\` (`eski/`, `yeni/` aynı 16 cümle, `cumleler.txt`, `kaggle-ornekleri/`)

---

*(Yeni girişler en alta eklenir.)*
