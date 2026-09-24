<!--
Sözcük uygulama içi yardım içeriği (F1 → "Yardım ve Nasıl Kullanılır").

Yazım kuralları:
- Her konu "<!- - konu: kimlik | Başlık | ikon - ->" satırıyla başlar (tireler bitişik yazılır); ikon, icons.py'deki addır.
- Konu gövdesi Markdown'dır. Kısayollar `Ctrl+B` biçiminde yazılır.
- Yeni bir özellik eklendiğinde: ilgili konuyu güncelleyin, "Yenilikler"e tarihli madde ekleyin,
  yeni kısayol varsa "Klavye Kısayolları" tablosuna ekleyin (test, tablodaki kısayolların uygulamada tanımlı olduğunu denetler).
-->

<!-- konu: baslarken | Başlarken | new -->
# Sözcük'e Hoş Geldiniz

Sözcük, Word belgeleriyle (.docx) çalışan, sade ve tamamen **bilgisayarınızda çalışan** bir kelime işlemcidir. Yazdıklarınız, sesiniz ve belgeleriniz hiçbir sunucuya gönderilmez.

## Ekranın bölümleri

- **Başlık şeridi (mavi):** solda **Dosya** menüsü, Kaydet, Geri Al ve Yinele; ortada belgenin adı ve kayıt durumu; sağda **Otomatik Kaydet** anahtarı ve **Yardım** düğmesi.
- **Menü şeridi:** Dosya, Düzen, Biçim, Ekle, Sayfa Düzeni, Görünüm ve Yardım menüleri (bkz. [Menüler](konu:menuler)).
- **Komut çubuğu:** yazı tipi, biçimlendirme, paragraf, liste, tablo, resim, simge, sayfa düzeni ve sesle yazma düğmeleri; sığmazsa iki satıra yayılır. Düğmelerin üzerinde fareyi bekletince adı ve kısayolu görünür.
- **Cetveller:** sayfanın üstünde ve solunda; paragraf girintileri ve üst/alt kenar boşlukları buradan sürüklenerek ayarlanır.
- **Sayfa:** gerçek kâğıt boyutunda (varsayılan A4) sayfalar halinde yazarsınız.
- **Durum çubuğu (alt):** sayfa numarası, sözcük sayısı, dil, kayıt durumu, cetvel düğmesi, yakınlaştırma ve yazım denetimi durumu.

## İlk adımlar

1. Yazmaya hemen başlayabilirsiniz; yeni belge A4, Calibri 11 punto ve 2,5 cm kenar boşluklarıyla açılır.
2. Kaydetmek için `Ctrl+S` tuşlarına basın. Belge Word belgesi (.docx) olarak kaydedilir ve Word'de aynen açılır.
3. Bir konuda yardım gerektiğinde `F1` tuşuna basın; bu pencerenin üstündeki arama kutusuna aradığınızı yazabilirsiniz.

<!-- konu: yenilikler | Yenilikler | info -->
# Yenilikler

Sözcük'e eklenen özellikler, en yenisi en üstte.

## 24 Eylül 2026 — Sürüm 1.2

- **Sesli okuma:** Sözcük artık yazdığınız Türkçe metni sesli okuyor. Seçin ya da imleci bir cümleye koyun, **Sesli Oku** düğmesine tıklayın veya `Ctrl+Alt+Space`'e basın; okunan cümle sayfada maviyle işaretlenir. Sayılar, tarihler, saatler ve kısaltmalar Türkçe okunur. Okuma tamamen bilgisayarınızda yapılır, internet gerekmez. Uygulamayla **Ata**'nın (erkek) sesi gelir. Bkz. [Sesli Okuma](konu:sesli).

## 21 Eylül 2026 — Sürüm 1.1

- **Çok daha küçük kurulum:** kurulum paketi 1,3 GB'tan yaklaşık 300 MB'a, kurulu hali 2 GB'tan yaklaşık 500 MB'a indi. Çeviri motoru sadeleştirildi; ilk çeviri de artık saniyeler içinde hazır.
- **Dilleri kurulumda seçin:** uygulamayla yalnızca Türkçe ⇄ İngilizce gelir. Kurulumda **Özel kurulum**'u seçip Almanca, İtalyanca, İspanyolca, Fransızca, Rusça, Çince, Japonca, Hintçe, Korece, Arapça ve Portekizce'den istediklerinizi işaretleyebilirsiniz; kurulum onları indirir. Sonradan **Gözden Geçir → Dil Paketleri…** ile de eklenebilir. Bkz. [Çeviri](konu:ceviri).
- İspanyolca ve Fransızca çevirilerde görülen bozuk çıktılar düzeltildi.

## 19 Eylül 2026

- **Çeviri ve dil paketleri:** `Ctrl+Shift+T` ile seçili metni ya da belgenin tamamını çevirin; **Gözden Geçir → Dil Paketleri…** ile başka dilleri indirin. Türkçe ⇄ İngilizce uygulamayla birlikte gelir. Çeviri bilgisayarınızda yapılır; internet yalnızca dil paketini bir kez indirmek için gerekir. Bkz. [Çeviri](konu:ceviri).
- **Bağlantı (köprü):** `Ctrl+K` ile web adresi ya da belgede bir yer (ör. "2. sayfa, 5. satır") bağlantısı; `Ctrl` ile tıklayarak açılır. Bkz. [Bağlantılar](konu:baglanti).
- **Sayfa numarası:** Sayfa Düzeni menüsünden açılır; konum (alt/üst — sol, orta, sağ), biçim ("1", "Sayfa 1", "1 / 12") ve başlangıç numarası seçilebilir. Ekranda, yazdırmada, PDF'te ve .docx'te görünür. Bkz. [Sayfa Düzeni](konu:sayfa).
- **Bul ve Değiştir:** `Ctrl+F` ile arama, `Ctrl+H` ile değiştirme; tüm eşleşmeler sayfada sarıyla işaretlenir, Türkçe harf kuralları gözetilir. Bkz. [Bul ve Değiştir](konu:bul).

## 17 Eylül 2026

- **Menü şeridi:** Word'deki gibi konu başlıklarına göre menüler — Dosya, Düzen, Biçim, Ekle, Sayfa Düzeni, Görünüm, Yardım. Bkz. [Menüler](konu:menuler).
- **İki satırlı komut çubuğu ve sürükleyerek sıralama:** düğmeler sığmazsa ikinci satıra geçer; düğmeler sürüklenerek istediğiniz sıraya dizilebilir. Bkz. [Komut Çubuğunu Özelleştirme](konu:cubuk).
- **Word'ün açtığı diğer biçimler:** eski Word belgeleri (.doc, .dot), .docm, .dotx, .dotm, .rtf, .odt (LibreOffice), .txt, web sayfaları (.htm, .html, .mht), Word 2003 XML, Works (.wps) ve WordPerfect (.wpd) açılabilir; Farklı Kaydet'e .doc, .rtf, .odt, .txt ve .html eklendi. Bkz. [Dosya Biçimleri](konu:bicimler).
- **Google Drive ve OneDrive ile canlı çalışma:** Drive'daki Word belgelerini açıp düzenleyin; yazmaya kısa ara verdiğinizde belge kendiliğinden Drive'a kaydedilir. Belge başka yerde değişirse Sözcük fark eder. Bkz. [Google Drive ve OneDrive](konu:bulut).
- **Yardım ve Nasıl Kullanılır:** bu pencere. `F1`, başlıktaki **?** düğmesi ya da **Dosya → Yardım ve Nasıl Kullanılır** ile açılır; konular aranabilir.
- **Sayfa Düzeni:** kenar boşluğu hazır ayarları, dikey/yatay yönlendirme, kâğıt boyutları (A4, A5, A3, B5, Letter, Legal, Executive) ve önizlemeli **Sayfa Yapısı** penceresi. Bkz. [Sayfa Düzeni](konu:sayfa).
- **Komut çubuğunu özelleştirme:** düğmeleri gösterip gizleyin; pencere darsa sığmayan düğmeler **»** menüsünde. Bkz. [Komut Çubuğunu Özelleştirme](konu:cubuk).
- **Resimler:** dosyadan, panodan ya da sürükle-bırakla resim ekleme; tutamaklarla boyutlandırma, kırpma, 90° ve fareyle döndürme. Bkz. [Resimler](konu:resim).
- **Simgeler:** son kullanılan simgeler ve kategorili, aranabilir simge penceresi (₺, oklar, matematik, ASCII, kutu çizgileri, emoji…). Bkz. [Simgeler](konu:simge).
- **Dikey cetvel:** üst ve alt kenar boşlukları cetvelden sürüklenerek ayarlanabilir.
- **Türkçe yazım denetimi bileşeni:** Windows'ta yüklü değilse Sözcük içinden eklenebilir.

## Daha önce eklenenler

- Windows'un Türkçe yazım denetimiyle canlı denetim (kırmızı dalgalı çizgi, öneriler, `F7`).
- Sesle yazma (dikte): internet gerektirmeden Türkçe konuşmayı metne çevirir; susunca otomatik durur, ses seviyesi göstergesi; dikte sözlüğü ve öğrenen düzeltmeler.
- Tablolar; Excel'den ve web sayfalarından tablo yapıştırma.
- Yakınlaştırma, sayfa genişliğine/tam sayfaya sığdırma, yatay cetvel.
- Word (.docx) açma/kaydetme, PDF'i düzenlenebilir metin olarak açma, PDF olarak dışa aktarma, yazdırma.
- Otomatik kaydetme ve beklenmedik kapanmada belge kurtarma.

<!-- konu: menuler | Menüler | more -->
# Menüler

Başlığın altındaki menü şeridinde komutlar konularına göre toplanmıştır. Komut çubuğundaki düğmelerle aynı işi yaparlar; bir düğmeyi çubuktan gizleseniz bile komut menüde durur.

| Menü | İçindekiler |
|---|---|
| **Dosya** | Yeni, Aç, Google Drive'dan Aç, Kaydet, Farklı Kaydet, PDF Olarak Dışa Aktar, Yazdır, Yardım, Tanılama Günlüğü, Kapat |
| **Düzen** | Geri Al, Yinele, Kes, Kopyala, Yapıştır, Yalnızca Metni Koru, Tümünü Seç, Bul, Değiştir, Sonraki/Önceki Bul, Sonraki Yazım Hatası |
| **Biçim** | Stiller, Kalın/İtalik/Altı Çizili/Üstü Çizili, Yazı Tipi Boyutu, Yazı Tipi Rengi, Metin Vurgu Rengi, Hizalama, Satır Aralığı, Listeler ve Girinti, Biçimlendirmeyi Temizle, Yazı Tipi Ekle |
| **Ekle** | Tablo, Resim, Simge, Bağlantı, Sesle Yaz |
| **Sayfa Düzeni** | Kenar Boşlukları, Yönlendirme (Dikey/Yatay), Boyut (A4, A5, A3, B5, Letter, Legal, Executive), Sayfa Numarası, Sayfa Yapısı… |
| **Görünüm** | Cetvel, Yakınlaştır/Uzaklaştır, %100, Sayfa Genişliği, Tam Sayfa, Komut Çubuğunu Özelleştir, Düğme Sırasını Sıfırla |
| **Gözden Geçir** | Yazarken Yazım Denetimi, Sonraki Yazım Hatası, Dikte Sözlüğü, Çeviri, Dil Paketleri, Sesli Oku |
| **Yardım** | Yardım ve Nasıl Kullanılır (F1), Klavye Kısayolları, Tanılama Günlüğü Klasörünü Aç |

Menülerde komutların kısayolları da yazar.

<!-- konu: dosya | Dosya İşlemleri | open -->
# Dosya İşlemleri

Dosya işlemleri başlık şeridinin solundaki **Dosya** menüsündedir.

| İşlem | Kısayol | Açıklama |
|---|---|---|
| Yeni | `Ctrl+N` | Boş bir belge açar (açık belge kaydedilmemişse önce sorar). |
| Aç… | `Ctrl+O` | Word belgelerini (.docx, .doc…), .rtf, .odt, .txt, web sayfaları ve PDF açar (bkz. [Dosya Biçimleri](konu:bicimler)). |
| Google Drive'dan Aç… / OneDrive'dan Aç… | | Drive klasörünüzden belge açar (bkz. [Google Drive ve OneDrive](konu:bulut)). |
| Kaydet | `Ctrl+S` | Belgeyi .docx olarak kaydeder. |
| Farklı Kaydet… | `F12` | Yeni bir ad, konum ya da biçimle (.docx, .doc, .rtf, .odt, .txt, .html) kaydeder. |
| Google Drive'a Kaydet… / OneDrive'a Kaydet… | | Belgeyi Drive klasörünüze kaydeder; bundan sonra canlı kaydedilir. |
| PDF Olarak Dışa Aktar… | | Belgeyi kâğıt boyutu ve kenar boşluklarıyla PDF'e çevirir. |
| Yazdır… | `Ctrl+P` | Yazıcı seçme penceresini açar. |

## Word belgeleri

Sözcük .docx dosyalarını açar ve kaydeder: yazı tipleri, renkler, başlıklar, listeler, tablolar, resimler, sayfa boyutu ve kenar boşlukları korunur. Sözcük'ün desteklemediği öğeler (üst/alt bilgi, dipnot, yorum, metin kutusu, şekil) içeren bir belge açılırsa sayfanın üstünde bir uyarı görünür; belgeyi kaydederseniz bu öğeler dosyadan çıkarılır. Özgün dosyayı korumak isterseniz **Farklı Kaydet** kullanın.

## PDF açma

PDF dosyaları düzenlenebilir metne dönüştürülerek açılır: paragraflar, başlıklar ve listeler algılanır. Sayfa düzeni, tablolar ve resimler birebir korunmayabilir. Kaydettiğinizde belge .docx olarak kaydedilir; PDF'in kendisi değişmez. Taranmış (fotoğraf halindeki) PDF'lerde seçilebilir metin olmadığı için açılamaz.

## Otomatik kaydetme ve kurtarma

- Başlıktaki **Otomatik Kaydet** açıksa, daha önce kaydedilmiş bir belge yazmaya ara verdiğinizde kendiliğinden kaydedilir.
- Henüz hiç kaydedilmemiş belgeler için birkaç dakikada bir **kurtarma kopyası** tutulur. Sözcük ya da bilgisayar beklenmedik şekilde kapanırsa, bir sonraki açılışta sayfanın üstünde **Geri Yükle** seçeneği çıkar.

<!-- konu: bicimler | Dosya Biçimleri | open -->
# Dosya Biçimleri

Sözcük, Word'ün açabildiği belge biçimlerini açar. Asıl biçimi **Word Belgesi (.docx)**'tir: tüm özellikler bu biçimde eksiksiz kaydedilir.

## Açılabilen biçimler

| Biçim | Uzantı | Nasıl açılır |
|---|---|---|
| Word Belgesi | .docx | Doğrudan |
| Makro İçerebilen Word Belgesi | .docm | Doğrudan; makrolar çalıştırılmaz |
| Word Şablonu | .dotx, .dotm | Doğrudan; Word gibi yeni, adsız belge olarak açılır (şablon değişmez) |
| Word 97-2003 Belgesi / Şablonu | .doc, .dot | Microsoft Word ya da LibreOffice ile (aşağıya bakın) |
| Zengin Metin Biçimi | .rtf | Doğrudan |
| OpenDocument Metni (LibreOffice) | .odt | Doğrudan |
| Düz Metin | .txt | Doğrudan; Türkçe karakter kodlaması kendiliğinden algılanır |
| Web Sayfası | .htm, .html, .mht, .mhtml | Doğrudan; yerel resimler belgeye alınır, internetteki resimler alınmaz |
| Word 2003 XML Belgesi | .xml | Microsoft Word ya da LibreOffice ile |
| Works / WordPerfect | .wps, .wpd | Microsoft Word ya da LibreOffice ile |
| PDF | .pdf | Düzenlenebilir metne dönüştürülür (bkz. [Dosya İşlemleri](konu:dosya)) |

**Aç** penceresinde "Tüm Desteklenen Belgeler" ve "Tüm Word Belgeleri" seçenekleri vardır. Uzantısı yanlış olan dosyalar (ör. adı .doc ama içeriği RTF) içeriğine bakılarak doğru biçimde açılır.

## Eski biçimler ve Microsoft Word / LibreOffice

Word 97-2003 (.doc), Works, WordPerfect ve Word 2003 XML gibi eski biçimleri biçimlendirmesiyle okumak için Sözcük, bilgisayarınızda kurulu **Microsoft Word**'ü (yoksa ücretsiz **LibreOffice**'i) arka planda, görünmeden kullanır:

- Belge bilgisayarınızdan çıkmaz, internet kullanılmaz.
- Word penceresi açılmaz; belgedeki makrolar çalıştırılmaz; açık Word belgelerinize dokunulmaz.
- İlk açılış birkaç saniye sürer (Word'ün başlaması); bu sırada durum çubuğunda bilgi görünür.
- Parola korumalı belgeler açılamaz.

Bilgisayarda ne Word ne LibreOffice varsa: .doc dosyalarının **yalnızca metni** açılır (biçimlendirme, tablo ve resimler alınamaz, sayfanın üstünde bildirilir); diğer eski biçimler için LibreOffice'i indirme bağlantısı gösterilir.

## Uyumluluk Modu

.docx dışındaki bir biçimde açılan belgede başlık şeridinde **Uyumluluk Modu (.doc)** gibi bir yazı görünür:

- **Otomatik kayıt** bu belgelerde dosyanın kendisine yazmaz (yalnızca kurtarma kopyası tutulur); dosya siz **Kaydet** dediğinizde yazılır.
- **Kaydet** dediğinizde Sözcük **Word Belgesi (.docx) olarak kaydetmeyi** önerir; isterseniz özgün biçimde de kaydedebilirsiniz (o biçimde kaybolabilecekler belirtilir).
- .docx olarak kaydettiğiniz andan itibaren Uyumluluk Modu kalkar ve otomatik kayıt normal çalışır.

## Farklı Kaydet biçimleri

| Biçim | Not |
|---|---|
| Word Belgesi (.docx) | Önerilen; her şey korunur |
| Word 97-2003 Belgesi (.doc) | Microsoft Word ya da LibreOffice gerekir; bazı yeni biçimlendirmeler tam korunmayabilir |
| Zengin Metin Biçimi (.rtf) | Microsoft Word ya da LibreOffice gerekir |
| OpenDocument Metni (.odt) | Sayfa yapısı ve başlık stilleri dosyaya yazılmaz |
| Düz Metin (.txt) | Yalnızca metin (UTF-8); biçimlendirme, tablo ve resimler kaybolur |
| Web Sayfası (.html) | Resimler yanındaki "_dosyalar" klasörüne kaydedilir; sayfa yapısı yazılmaz |

Word ya da LibreOffice yoksa .doc ve .rtf seçenekleri listede görünmez.

<!-- konu: bulut | Google Drive ve OneDrive | cloud -->
# Google Drive ve OneDrive

Sözcük bilgisayarınızda çalışır; belgelerinizi Google Drive'da (ya da OneDrive'da) tutup düzenlerken yaptığınız değişiklikler **canlı olarak** Drive'a kaydedilir.

## Nasıl çalışır?

Bilgisayarınızdaki **Google Drive** uygulaması, Drive'ınızı Dosya Gezgini'nde ayrı bir sürücü olarak gösterir (ör. `G:\Drive'ım`); OneDrive ise kullanıcı klasörünüzde bir klasördür. Google hesabınızın oturumu bu uygulamada açıktır. Sözcük belgeyi bu klasöre kaydeder, Google Drive uygulaması da değişiklikleri buluta gönderir.

- Sözcük Google hesabınıza, şifrenize ya da Google'ın sunucularına **hiç bağlanmaz**; ayrıca bir giriş ya da ayar gerekmez.
- **Google Drive masaüstü uygulaması** kurulu ve oturumu açık olmalıdır (google.com/drive/download). OneDrive Windows'ta hazır gelir.
- İnternet yokken de yazmaya devam edebilirsiniz; değişiklikler bağlantı gelince Drive'a gönderilir.

## Drive'daki bir belgeyi açma ve kaydetme

- **Dosya → Google Drive'dan Aç…** doğrudan Drive'ınızı açar. **Aç…** penceresinden Drive sürücüsüne giderek de açabilirsiniz.
- Yeni ya da bilgisayardaki bir belgeyi Drive'a taşımak için **Dosya → Google Drive'a Kaydet…**
- Bu seçenekler yalnızca bilgisayarda Google Drive ya da OneDrive bulunduğunda menüde görünür.

## Canlı kaydetme

Drive'daki bir belgede **Otomatik Kaydet** açıkken, yazmaya **2 saniye** ara verdiğinizde belge kendiliğinden kaydedilir. Başlık şeridinde durum görünür:

| Durum | Anlamı |
|---|---|
| Değiştirildi | Kaydedilmemiş değişiklik var; kısa süre içinde kaydedilecek. |
| Google Drive'a kaydediliyor… | Kaydediliyor. |
| Google Drive'a kaydedildi | Belge Drive klasörüne kaydedildi; Google Drive uygulaması buluta gönderiyor. |
| Google Drive'a kaydedilemedi | Drive klasörüne yazılamadı (ör. Google Drive uygulaması kapalı). Sözcük kısa aralıklarla yeniden dener ve bu arada kurtarma kopyası tutar. |
| Başka yerde değiştirildi — otomatik kayıt bekliyor | Aşağıya bakın. |

Durum çubuğunda son kaydetme saati saniyesiyle görünür.

## Belge başka yerde değişirse

Aynı belge Drive'ın web sayfasında ya da başka bir bilgisayarda değiştirilip bu bilgisayara eşitlenirse Sözcük birkaç saniye içinde fark eder:

- **Sizin kaydedilmemiş değişikliğiniz yoksa** yeni sürüm kendiliğinden yüklenir ve durum çubuğunda bildirilir.
- **Sizin de kaydedilmemiş değişikliğiniz varsa** otomatik kayıt diğer sürümün üzerine yazmaz ve sayfanın üstünde seçenekler çıkar:
  - **Onların Sürümünü Yükle:** diğer sürümü açar (sizin kaydedilmemiş değişiklikleriniz atılır).
  - **Benimkini Kaydet:** sizin sürümünüzü dosyaya kaydeder (diğer değişiklikler dosyadan çıkar).
  - **Benimkini Ayrı Kaydet:** sizin sürümünüzü farklı adla kaydeder; iki sürüm de korunur.

Aynı belgeyi aynı anda iki yerde düzenlemek yerine, bir yerde kapatıp diğerinde açmanız önerilir: Sözcük değişiklikleri güvenle yakalar ama iki sürümü satır satır birleştirmez.

## Google Dokümanlar belgeleri (.gdoc)

Google Dokümanlar'da oluşturulan belgeler Drive'da `.gdoc` dosyası olarak görünür, ama bunlar gerçek belge değil, yalnızca **bağlantıdır**: belgenin içeriği bilgisayarda hiç bulunmaz, Google'ın sunucusunda durur. Google Drive uygulaması bu dosyanın içini okumaya bile izin vermez; bu yüzden Sözcük (ve Word gibi diğer programlar) açamaz. Bilgisayara kopyalanan bir `.gdoc` da yalnızca bağlantı kopyasıdır.

Sözcük'te açmaya çalışırsanız **Tarayıcıda Aç** düğmesi belgeyi Google Dokümanlar'da açar. Sözcük'te düzenlemek için:

1. Belgede **Dosya → İndir → Microsoft Word (.docx)** seçin.
2. İnen .docx dosyasını Drive klasörünüze taşıyın (ya da Sözcük'te açıp **Google Drive'a Kaydet…** kullanın).
3. Artık belge gerçek bir Word belgesidir; Sözcük'te düzenlenir ve canlı kaydedilir.

Çok sayıda belge için: drive.google.com'da belgeleri seçip **İndir** derseniz hepsi .docx olarak tek bir zip dosyasında iner.

Yeni belgelerin Google Dokümanlar biçimine çevrilmemesi için drive.google.com → **Ayarlar** → "Yüklemeleri dönüştür" seçeneğini kapalı tutun.

## Sınırlar

- Başka kişilerle **aynı anda ortak düzenleme**, paylaşım ve yorumlar Google'ın web hizmetlerine özgüdür; Sözcük'te yoktur.
- Belgenin buluta gerçekten ulaşıp ulaşmadığını Google Drive uygulaması izler; eşitleme durumunu görev çubuğundaki Google Drive simgesinden görebilirsiniz.

<!-- konu: bicim | Metin Biçimlendirme | bold -->
# Metin Biçimlendirme

Biçimlendirmek istediğiniz metni seçin (ya da yazmadan önce biçimi seçin) ve komut çubuğundaki düğmeleri kullanın.

## Yazı tipi

- **Stiller:** Normal, Başlık 1, Başlık 2. Başlık satırının sonunda `Enter`'a basınca sonraki paragraf Normal stille devam eder.
- **Yazı tipi ve boyut:** listeden seçin ya da boyut kutusuna değer yazıp `Enter`'a basın (ör. 10,5).
- **Yazı tipini büyüt/küçült:** `Ctrl+]` ve `Ctrl+[`.
- **Yazı Tipi Ekle…:** bilgisayarınızdaki .ttf ya da .otf yazı tipi dosyasını Sözcük'e ekler; eklenen yazı tipi sonraki açılışlarda da listede olur.

## Karakter biçimleri

| Biçim | Kısayol |
|---|---|
| Kalın | `Ctrl+B` |
| İtalik | `Ctrl+I` |
| Altı Çizili | `Ctrl+U` |
| Üstü Çizili | (düğme) |
| Tüm Biçimlendirmeyi Temizle | `Ctrl+Space` |

- **Metin Vurgu Rengi** ve **Yazı Tipi Rengi** düğmelerinin kendisine tıklamak son kullanılan rengi uygular; yanındaki oka tıklayınca renk paleti açılır ("Renk yok" / "Otomatik" ile kaldırılır).

<!-- konu: paragraf | Paragraflar ve Listeler | align_left -->
# Paragraflar ve Listeler

## Hizalama ve satır aralığı

| İşlem | Kısayol |
|---|---|
| Sola Hizala | `Ctrl+L` |
| Ortala | `Ctrl+E` |
| Sağa Hizala | `Ctrl+R` |
| İki Yana Yasla | `Ctrl+J` |

**Satır ve Paragraf Aralığı** düğmesinden 1 ile 3 arasında satır aralığı seçilir (Word varsayılanı 1,08).

## Madde işaretleri ve numaralandırma

- **Madde İşaretleri** `Ctrl+Shift+L`, **Numaralandırma** `Ctrl+Shift+N`.
- Liste maddesinin başında `Tab` bir alt seviyeye indirir, `Shift+Tab` bir üst seviyeye çıkarır. **Girintiyi Artır/Azalt** düğmeleri de aynı işi yapar.
- Boş bir madde üzerinde `Enter` önce seviyeyi düşürür, en üst seviyedeyse listeden çıkar (Word gibi).
- Paragraf içinde yeni paragraf açmadan alt satıra geçmek için `Shift+Enter`.

## Girintiler

Paragraf girintilerini yatay cetveldeki işaretçileri sürükleyerek ayarlayabilirsiniz. Bkz. [Cetveller](konu:cetvel).

<!-- konu: cetvel | Cetveller | ruler -->
# Cetveller

Cetveller durum çubuğundaki **cetvel** düğmesiyle gösterilip gizlenir.

## Yatay cetvel: paragraf girintileri

İmlecin bulunduğu (ya da seçili) paragrafların girintilerini gösterir. Beyaz alan yazı alanı, gri alanlar kenar boşluklarıdır.

- **Üstteki üçgen:** ilk satır girintisi.
- **Alttaki üçgen:** asılı girinti (ilk satır hariç diğer satırlar).
- **Alttaki kare:** sol girinti (ilk satır ve diğer satırlar birlikte kayar).
- **Sağdaki üçgen:** sağ girinti.

İşaretçiyi sürüklerken sayfada kesik çizgili bir kılavuz görünür. Değerler 0,25 cm'ye yapışır; serbest ayar için sürüklerken `Alt` tuşunu basılı tutun.

## Dikey cetvel: üst ve alt kenar boşlukları

Dikey cetveldeki gri/beyaz sınırın üzerine gelince imleç ↕ şeklini alır; sürükleyerek belgenin üst ya da alt kenar boşluğunu değiştirirsiniz. Sürüklerken değer (ör. "Üst kenar boşluğu: 3,25 cm") görünür. Sol ve sağ kenar boşlukları **Sayfa Düzeni** menüsünden ayarlanır.

<!-- konu: sayfa | Sayfa Düzeni | page_layout -->
# Sayfa Düzeni

Komut çubuğundaki **Sayfa Düzeni** düğmesi (ya da menü şeridindeki **Sayfa Düzeni** menüsü) belgenin kâğıt boyutunu, yönlendirmesini ve kenar boşluklarını ayarlar. Ayarlar tüm belgeye uygulanır, .docx dosyasına kaydedilir, yazdırma ve PDF'e de yansır.

## Kenar Boşlukları

| Hazır ayar | Üst | Alt | Sol | Sağ |
|---|---|---|---|---|
| Normal | 2,5 cm | 2,5 cm | 2,5 cm | 2,5 cm |
| Dar | 1,27 cm | 1,27 cm | 1,27 cm | 1,27 cm |
| Orta | 2,54 cm | 2,54 cm | 1,91 cm | 1,91 cm |
| Geniş | 2,54 cm | 2,54 cm | 5,08 cm | 5,08 cm |

Farklı değerler için **Özel Kenar Boşlukları…** seçeneğini kullanın. Üst ve alt boşluklar dikey cetvelden sürüklenerek de değiştirilebilir.

## Yönlendirme

**Dikey** ya da **Yatay**. Yönlendirme değişince kenar boşlukları da sayfayla birlikte döner (Word'deki gibi).

## Boyut

A4, A5, A3, B5 (JIS), Letter, Legal ve Executive. Listede olmayan bir boyut için **Diğer Kâğıt Boyutları…** ile genişlik ve yükseklik girin.

## Sayfa Numarası

**Sayfa Düzeni → Sayfa Numarası** menüsünden **Sayfa Numarası Ekle** işaretlenince belgenin her sayfasına numara konur.

- **Konum:** Alt Orta (varsayılan), Alt Sağ, Alt Sol, Üst Sağ, Üst Sol, Üst Orta.
- **Biçim:** yalnızca numara ("1"), "Sayfa 1" ya da "1 / 12" (toplam sayfa sayısıyla birlikte).
- **Başlangıç Numarası…:** belge başka bir dosyadan devam ediyorsa numaralandırmayı istediğiniz sayıdan başlatır.

Numara sayfanın kenar boşluğuna yazılır; belgenin metnine karışmaz, üzerine tıklayıp yazamazsınız — bu bir sayfa ayarıdır. Ekranda gördüğünüz gibi **yazdırmada ve PDF'te** de çıkar. Belgeyi .docx olarak kaydederseniz numara Word'ün kendi sayfa numarası alanı olarak yazılır: dosyayı Word'de açıp sayfa eklerseniz numaralar kendiliğinden güncellenir. Word'de hazırlanmış bir belgedeki sayfa numarası da açılırken tanınır.

Sözcük'te tam bir üst bilgi / alt bilgi düzeni yoktur; sayfa numarası dışındaki üst/alt bilgi içerikleri desteklenmez.

## Sayfa Yapısı penceresi

Dört kenar boşluğunu, yönlendirmeyi ve kâğıt boyutunu tek yerde, canlı önizlemeyle ayarlar. Sayfaya sığmayacak kadar büyük kenar boşlukları girerseniz uyarı görünür; sayfada en az 3 cm yazı alanı bırakılır.

<!-- konu: tablo | Tablolar | table -->
# Tablolar

## Tablo ekleme

**Tablo** düğmesine tıklayın ve açılan ızgarada fareyle istediğiniz satır × sütun sayısını seçin. Daha büyük tablolar için **Tablo Ekle…** ile sayıları yazın.

## Tabloda gezinme

- `Tab` sonraki hücreye, `Shift+Tab` önceki hücreye geçer ve hücrenin içeriğini seçer.
- Son hücrede `Tab` tabloya yeni bir satır ekler.

## Satır, sütun ve hücreler

İmleç tablodayken **Tablo** menüsünden ya da sağ tık menüsünden:

- **Ekle:** üste/alta satır, sola/sağa sütun.
- **Sil:** satırları, sütunları ya da tüm tabloyu sil.
- **Hücreleri Birleştir:** birden çok hücre seçiliyken.
- **Hücreyi Böl:** birleştirilmiş bir hücreyi eski haline getirir.

## Excel'den ve web'den tablo yapıştırma

Excel, Google E-Tablolar ya da bir web sayfasından kopyaladığınız hücreleri `Ctrl+V` ile yapıştırınca kenarlıklı bir tablo oluşur. İmleç zaten bir tablodaysa kopyalanan değerler o hücrelerden başlayarak doldurulur.

<!-- konu: resim | Resimler | image -->
# Resimler

## Resim ekleme

- **Dosyadan:** **Resim → Dosyadan Resim Ekle…** (birden çok dosya seçilebilir). PNG, JPEG, BMP, GIF, WEBP ve TIFF desteklenir.
- **Panodan:** ekran görüntüsü ya da kopyalanan bir resim için `Ctrl+V` veya **Resim → Panodaki Resmi Ekle**. Dosya Gezgini'nde kopyalanan resim dosyaları da yapıştırılabilir.
- **Sürükle-bırak:** Dosya Gezgini'nden ya da tarayıcıdan resmi sayfada istediğiniz yere bırakın.

Çok büyük fotoğraflar belge dosyası şişmesin diye makul boyuta küçültülür. Eklenen resim sayfaya sığacak boyutta yerleşir ve seçili gelir.

## Seçme ve boyutlandırma

- Resme tıklayınca mavi çerçeve ve 8 tutamak çıkar.
- **Köşe tutamakları** en-boy oranını koruyarak büyütür/küçültür; oranı bozmak için `Shift` basılı tutun.
- **Kenar tutamakları** yalnızca genişliği ya da yüksekliği değiştirir.
- **Özgün Boyut** resmi kendi boyutuna (sayfaya sığacak kadar) döndürür.
- Seçili resim `Delete` ile silinir, `Ctrl+X`/`Ctrl+C` ile kesilir/kopyalanır; `Esc` seçimi bırakır.

## Kırpma

1. Resmi seçin ve **Kırp**'a tıklayın (Resim menüsü ya da sağ tık).
2. Kalın siyah kırpma tutamaklarını sürükleyin; atılacak kısım soluk görünür.
3. `Enter` ya da resmin dışına tıklama kırpmayı uygular; `Esc` vazgeçer.

**Kırpmayı Sıfırla** resmin tamamını geri getirir; kırpma resmi kalıcı olarak bozmaz.

## Döndürme

- **Sağa 90° Döndür** ve **Sola 90° Döndür** (Resim menüsü ya da sağ tık).
- **Fareyle:** seçili resmin üstündeki yuvarlak ok tutamağını sürükleyin; bırakana kadar önizleme görünür. 15°'lik adımlarla döndürmek için `Shift` basılı tutun.
- **Döndürmeyi Sıfırla** resmi ilk haline getirir.

Tüm resim işlemleri `Ctrl+Z` ile tek adımda geri alınır. Resimler metnin içinde bir karakter gibi durur (metin resmin etrafından akmaz).

<!-- konu: simge | Simgeler | symbol -->
# Simgeler

**Simge** (Ω) düğmesi, klavyede olmayan karakterleri eklemenizi sağlar.

- Düğmeye tıklayınca **son kullandığınız 20 simge** görünür; birine tıklamak imlecin olduğu yere ekler.
- **Diğer Simgeler…** penceresinde simgeler kategorilere ayrılmıştır: Sık Kullanılanlar, Noktalama ve Tipografi, Para Birimleri (₺ dahil), Matematik, Oklar, Yunan Harfleri, Şekiller, İşaretler ve Semboller, Kutu Çizgileri, ASCII Karakterleri, Latin Harfleri, Emoji.
- **Arama:** Türkçe ("tl", "derece", "yıldız", "ok"), İngilizce Unicode adıyla ya da kodla ("U+20BA") arayabilirsiniz.
- Bir simgeye tıklayınca büyük önizlemesi, adı ve kodu görünür. **Ekle**, çift tıklama ya da `Enter` ekler. Pencere açık kalır; art arda simge ekleyebilirsiniz.

Simgeler imlecin yazı biçimiyle sıradan karakter olarak eklenir.

<!-- konu: baglanti | Bağlantılar | link -->
# Bağlantılar

Metne köprü eklemek için `Ctrl+K` tuşlarına basın; aynı komut **Ekle** menüsünde ve komut çubuğundaki zincir düğmesindedir.

## Bağlantı ekleme

1. Bağlantı yapılacak metni seçin (seçmezseniz yazdığınız metin eklenir) ve `Ctrl+K`'ye basın.
2. **Görüntülenecek metin** kutusuna metni yazın.
3. Hedefi seçin:
   - **Web adresi ya da e-posta:** `https://ornek.com`, `www.ornek.com` ya da `ad@ornek.com`. Başına `https://` ya da `mailto:` gerekiyorsa Sözcük kendisi ekler.
   - **Bu belgede bir yer:** **Sayfa** numarasını seçin; isterseniz **Satır** kutusunu işaretleyip satır numarası da verin (ör. 2. sayfanın 5. satırı).

## Bağlantıyı açma

Bağlantının üzerine **`Ctrl` ile tıklayın**: web adresleri tarayıcıda açılır, belge içi bağlantılar imleci o sayfaya (ve satıra) götürür. Fareyi üzerine getirince hedefi ipucu olarak görürsünüz. Sağ tık menüsünde **Bağlantıyı Aç**, **Bağlantıyı Düzenle…** ve **Bağlantıyı Kaldır** vardır.

Bağlantılar Word'deki gibi mavi ve altı çizili görünür. Bağlantının hemen ardına yazdığınız metin bağlantıya katılmaz.

## Yazarken kendiliğinden bağlantı

Bir adres yazıp boşluk ya da `Enter` tuşuna basarsanız (ör. `www.ornek.com` veya `ad@ornek.com`) Sözcük onu kendiliğinden bağlantıya çevirir. İstemezseniz `Ctrl+Z` ile geri alabilirsiniz.

## Word ile uyum

Belgeyi .docx olarak kaydettiğinizde bağlantılar Word'ün kendi köprüleri olarak yazılır: web adresleri doğrudan, belge içi bağlantılar ise hedef sayfaya konan bir yer imiyle. Word'de hazırlanmış belgelerdeki köprüler de açılırken okunur; Word'ün yer imlerine giden bağlantılar Sözcük'te de o yere gider.

<!-- konu: bul | Bul ve Değiştir | find -->
# Bul ve Değiştir

Belgede metin aramak için `Ctrl+F`, bulduğunu değiştirmek için `Ctrl+H` tuşlarına basın. Aynı komutlar **Düzen** menüsünde ve komut çubuğundaki büyüteç ve değiştirme düğmelerindedir.

## Arama

- Aranan sözcüğü yazdıkça bulunanların **tümü sayfada sarıyla** işaretlenir; o anda üzerinde olduğunuz eşleşme turuncu görünür.
- Şeritte **kaçıncı eşleşmede** olduğunuz yazar (ör. "3 / 12").
- `Enter` ya da `F3` sonraki, `Shift+Enter` ya da `Shift+F3` önceki eşleşmeye gider. Son eşleşmeden sonra başa döner.
- Metinde seçili bir sözcük varken `Ctrl+F`'ye basarsanız o sözcük arama kutusuna yazılır.
- `Esc` şeridi kapatır ve işaretleri kaldırır.

**Türkçe harfler:** Arama büyük/küçük harf ayrımı yapmaz ve bunu Türkçe kurallarıyla yapar — "istanbul" araması "İstanbul" ve "İSTANBUL" sonuçlarını da bulur, "ılık" araması "Ilık" ile eşleşir.

| Seçenek | Ne yapar |
|---|---|
| **Aa** | Büyük/küçük harf duyarlı arar ("Ev" ile "ev" farklı sayılır). |
| **Tam sözcük** | Yalnızca sözcüğün tamamı eşleşir ("kar" araması "karınca" içinde bulunmaz). |

Arama tablo hücrelerindeki metni de kapsar.

## Değiştirme

1. `Ctrl+H` ile şeridi açın; **Bul** ve **Değiştir** kutularını doldurun.
2. **Değiştir** o anki eşleşmeyi değiştirip sonrakine geçer.
3. **Tümünü Değiştir** belgedeki bütün eşleşmeleri tek seferde değiştirir ve kaç değişiklik yapıldığını durum çubuğunda bildirir.

- Tümünü Değiştir tek bir işlem sayılır: `Ctrl+Z` hepsini birden geri alır.
- Değiştirilen metin, değiştirilen yerin biçimini (kalın, renk, yazı tipi) korur.

<!-- konu: yapistir | Kopyalama ve Yapıştırma | paste -->
# Kopyalama ve Yapıştırma

| İşlem | Kısayol |
|---|---|
| Kes | `Ctrl+X` |
| Kopyala | `Ctrl+C` |
| Yapıştır | `Ctrl+V` |
| Yalnızca Metni Koru | `Ctrl+Shift+V` |
| Geri Al | `Ctrl+Z` |
| Yinele | `Ctrl+Y` |

- **Yapıştır** kopyalanan metnin biçimini (kalın, renk, başlık, tablo) korur.
- **Yalnızca Metni Koru** biçimi atar; metin imlecin bulunduğu yerin biçimini alır.
- Excel'den kopyalanan hücreler tablo, ekran görüntüleri resim olarak yapıştırılır.

Sağ tık menüsünde de Kes, Kopyala, Yapıştır ve Yalnızca Metni Koru bulunur.

<!-- konu: ceviri | Çeviri | translate -->
# Çeviri

Metni başka bir dile çevirmek için `Ctrl+Shift+T` tuşlarına basın; aynı komut **Gözden Geçir** menüsünde ve komut çubuğundaki küre düğmesindedir.

## Kullanım

1. Çevirmek istediğiniz metni seçin. Seçim yapmazsanız belgenin tamamı alınır; pencerede metni düzenleyebilirsiniz.
2. **Kaynak dil** "Otomatik algıla" bırakılabilir; **Hedef dil**'i seçin. Ortadaki ⇄ düğmesi dilleri değiştirir.
3. **Çevir**'e basın. Sonuç sağ bölümde görünür.
4. **Seçimin Yerine Koy** çeviriyi belgedeki seçili metnin yerine yazar (`Ctrl+Z` ile geri alınır), **Panoya Kopyala** ise panoya alır.

Paragraf ve satır yapısı korunur. Pencere açık kalabilir; belgede başka bir yeri seçip yeniden açtığınızda yeni seçim alınır.

## Diller ve dil paketleri

Her dil için bir **dil paketi** gerekir. **Türkçe ⇄ İngilizce** uygulamayla birlikte gelir: indirme gerekmez, internet olmadan da çalışır.

Diğer dilleri iki yoldan ekleyebilirsiniz:

- **Kurulum sırasında:** kurulumda **Özel kurulum**'u seçip istediğiniz dilleri işaretleyin; kurulum onları internetten indirir.
- **Sonradan:** **Gözden Geçir → Dil Paketleri…** (ya da çeviri penceresindeki **Dil Paketleri…** düğmesi). Listede her dilin hazır olup olmadığı ve indirilecekse kaç MB yer kaplayacağı yazar. İstediklerinizi işaretleyip **Seçilenleri İndir** deyin; indirme arka planda yapılır, sonrasında o diller çevrimdışı çalışır.

| Dil | İndirme boyutu (Türkçe ⇄) |
|---|---|
| İngilizce | uygulamayla gelir |
| Almanca | ≈301 MB |
| İtalyanca | ≈175 MB |
| İspanyolca | ≈373 MB |
| Fransızca | ≈132 MB |
| Çince | ≈145 MB |
| Hintçe | ≈209 MB |
| Japonca | ≈238 MB |
| Korece | ≈240 MB |
| Rusça | ≈352 MB |
| Arapça | ≈170 MB |
| Portekizce | ≈136 MB |

Türkçe ile diğer diller arasındaki çeviri İngilizce üzerinden yapılır; bu yüzden bir dili eklediğinizde hem o dile hem o dilden çeviri yapabilirsiniz.

## İlk kullanım ve gizlilik

- Çeviri **bilgisayarınızda** yapılır: metniniz hiçbir sunucuya gönderilmez.
- İnternet yalnızca yeni bir dil paketi indirirken gerekir.
- İlk çeviri model yüklendiği için birkaç saniye sürer; sonrakiler hızlıdır.

## Neden Microsoft'un çevirisi kullanılmıyor?

Word'ün **Çevir** komutu ve Bing Çeviri birer bulut hizmetidir: metni Microsoft'un sunucularına gönderirler ve uygulamadan kullanmak için abonelik anahtarı gerekir. Windows'un cihaz üzerinde çalışan çeviri özelliği ise yalnızca Copilot+ bilgisayarlarda vardır. Bu yüzden Sözcük, sesle yazmada olduğu gibi, açık kaynaklı ve ücretsiz bir çeviri modeli kullanır (Argos Translate / OPUS-MT). Böylece belgeleriniz bilgisayarınızdan çıkmaz.

<!-- konu: yazim | Yazım Denetimi | spell_check -->
# Yazım Denetimi

Sözcük, Windows'un yerleşik **Türkçe yazım denetimini** kullanır (Microsoft Office'in kullandığı denetimle aynı sonuçlar). Denetim bilgisayarınızda çalışır; metniniz hiçbir yere gönderilmez.

## Kullanım

- Yazarken hatalı kelimelerin altı **kırmızı dalgalı çizgiyle** işaretlenir.
- Kelimeye **sağ tıklayın:** öneriler menünün en üstünde kalın yazılır; birine tıklamak düzeltir.
- **Tümünü Yoksay:** bu kelimeyi Sözcük açık kaldığı sürece hata saymaz.
- **Sözlüğe Ekle:** kelimeyi kişisel sözlüğünüze kalıcı olarak ekler (özel adlar, kurum adları için).
- Arka arkaya tekrarlanan kelimeler ("ve ve") için **Tekrarlanan Kelimeyi Sil** önerilir.
- `F7` bir sonraki yazım hatasına gider.

## Durum çubuğundaki yazım düğmesi

Sağ alttaki düğme hata sayısını gösterir. Menüsünden **Yazarken Yazım Denetimi** açılıp kapatılır, **Sonraki Yazım Hatası** bulunur ve **Yoksayılan Kelimeleri Sıfırla** yapılır.

## Türkçe yazım bileşeni yüklü değilse

Bazı Windows kurulumlarında Türkçe yazım bileşeni yoktur; durum çubuğunda "Türkçe yazım denetimi yüklü değil" yazar. Düğmenin menüsünden:

- **Türkçe Yazım Denetimini Windows'a Ekle…:** Microsoft'un resmî "Türkçe temel yazma" bileşenini ekler. Ekran dilinizi ve klavyenizi değiştirmez. Windows yönetici onayı (UAC) ister ve internet gerektirir; birkaç dakika sürebilir. Bileşen isterseniz Windows Ayarları'ndan kaldırılabilir.
- **Windows Dil Ayarlarını Aç:** bileşeni kendiniz eklemek isterseniz.
- **Yeniden Dene:** bileşeni başka yoldan eklediyseniz.

<!-- konu: dikte | Sesle Yazma (Dikte) | mic -->
# Sesle Yazma (Dikte)

Konuşarak yazmanızı sağlar. Tanıma **tamamen bilgisayarınızda** yapılır: ses kaydı ve metin hiçbir sunucuya gönderilmez.

## Kullanım

1. İmleci metnin ekleneceği yere koyun.
2. Mikrofon düğmesine tıklayın ya da `Ctrl+Shift+M` tuşlarına basın. Düğme kırmızılaşır, durum çubuğunda "Dinleniyor…" ve süre görünür.
3. Konuşun. Bitirince düğmeye yeniden tıklayın ya da `Ctrl+Shift+M`'ye basın. **Susunca Otomatik Durdur** açıksa 2,5 saniye sessizlikte kendiliğinden durur.
4. "Ses metne dönüştürülüyor…" yazısından sonra metin imlecin olduğu yere eklenir.

Dikte edilen metni `Ctrl+Z` ile tek adımda geri alabilirsiniz.

## İlk kullanım

İlk dikte sırasında konuşma tanıma modeli **bir kez** indirilir (yaklaşık 480 MB, internet gerekir). Sonraki kullanımlarda internet gerekmez.

## Mikrofon düğmesinin menüsü (yanındaki ok)

- **Susunca Otomatik Durdur (2,5 sn)**
- **Ses Seviyesi Göstergesi:** konuşurken sesinizin mikrofona ulaştığını gösterir.
- **Dikte Sözlüğü…:** bkz. [Dikte Sözlüğü](konu:sozluk).

## İpuçları

- Net ve normal hızda konuşun; noktalama işaretleri çoğunlukla kendiliğinden konur.
- "Mikrofon bulunamadı" uyarısında Windows ses ayarlarından mikrofonun bağlı ve izinli olduğunu denetleyin.

<!-- konu: sesli | Sesli Okuma | read_aloud -->
# Sesli Okuma

Sözcük, yazdığınız Türkçe metni doğal bir sesle okur. Okuma **tamamen bilgisayarınızda** yapılır: metniniz hiçbir sunucuya gönderilmez, internet gerekmez.

## Kullanım

1. Okunmasını istediğiniz yeri seçin. Seçim yapmazsanız okuma, imlecin bulunduğu cümleden başlayıp belgenin sonuna kadar sürer.
2. Komut çubuğundaki **Sesli Oku** düğmesine tıklayın ya da `Ctrl+Alt+Space` tuşlarına basın. Okunan cümle sayfada açık maviyle işaretlenir ve görünür kalır.
3. Durdurmak için düğmeye yeniden tıklayın ya da `Ctrl+Alt+Space`'e basın.

Okuma sürerken belgeyi değiştirirseniz okuma durur (işaretlenen yerler kaymasın diye).

## Düğmenin menüsü (yanındaki ok)

- **Duraklat / Devam Et**
- **Okumayı Durdur**
- **Ses:** kurulu seslerden birini seçin (kadın / erkek).
- **Hız:** Yavaş, Normal, Hızlı, Çok hızlı.

## Nasıl okur?

Sayılar, tarihler, saatler, yüzdeler ve kısaltmalar Türkçe okunur: "21.09.2026" → *yirmi bir eylül iki bin yirmi altı*, "10:30'da" → *on otuzda*, "%15" → *yüzde on beş*, "Dr." → *doktor*, "3. sayfa" → *üçüncü sayfa*, "THY" → *te he ye*. Türkçenin söyleyiş kuralları (vurgu, ince ve kalın ünsüzler, "ğ", düzeltme işaretli "kâr / hâlâ") gözetilir.

İlk okumada ses modeli yüklendiği için birkaç saniye beklenir; sonrası akıcıdır.

<!-- konu: sozluk | Dikte Sözlüğü | spell_check -->
# Dikte Sözlüğü

Dikte sözlüğü, sık kullandığınız özel adları doğru tanımayı ve tekrarlayan tanıma hatalarını otomatik düzeltmeyi sağlar. Yazım denetiminin **Sözlüğe Ekle** kelimeleri de buraya kaydedilir.

## Kelimeler

Kişi, kurum ve ürün adlarını (ör. "Ataberk", "PySide") kelime olarak ekleyin; konuşma tanıma bu kelimelere öncelik verir ve yazım denetimi bunları hata saymaz.

- Metinde kelimeyi seçip sağ tıklayın → **Dikte Sözlüğü → Kelime Olarak Ekle**.
- Ya da **Dikte Sözlüğü…** penceresinin **Kelimeler** sekmesinden ekleyin.

## Düzeltmeler

Tanıma bir kelimeyi sürekli yanlış yazıyorsa (ör. "diktek" yerine "tiktik") bir düzeltme kaydedin; sonraki diktelerde otomatik düzeltilir.

- Yanlış yazılan kelimeyi seçip sağ tıklayın → **Dikte Sözlüğü → Dikte Düzeltmesi Olarak Kaydet…**, doğru halini yazın.
- **Öğrenme:** dikte ettiğiniz metinde bir kelimeyi elle düzeltirseniz Sözcük bunu fark eder. Aynı düzeltme tekrarlanınca sayfanın üstünde öğrenmek isteyip istemediğinizi sorar (**Evet, Doğrula** / **Hayır, Öğrenme**).
- Pencerede öğrenilmiş kayıtlar **Doğrula** ile onaylanır, **Sil** ile kaldırılır.

<!-- konu: gorunum | Görünüm ve Yakınlaştırma | zoom_in -->
# Görünüm ve Yakınlaştırma

- Durum çubuğunun sağındaki **kaydırıcı**, **−** ve **+** düğmeleriyle %10 ile %500 arasında yakınlaştırın.
- `Ctrl` basılıyken **fare tekerleği** de yakınlaştırır.
- Yüzde değerine tıklayınca hazır düzeyler ile **Sayfa Genişliği** ve **Tam Sayfa** seçenekleri açılır.
- Yakınlaştırma yalnızca görünümü değiştirir; yazdırmayı ve belgeyi etkilemez. Son kullanılan düzey hatırlanır.
- **Cetvel** düğmesi cetvelleri gösterir/gizler.
- Durum çubuğunun solunda bulunduğunuz **sayfa** ve belgenin **sözcük sayısı** görünür.

<!-- konu: cubuk | Komut Çubuğunu Özelleştirme | customize -->
# Komut Çubuğunu Özelleştirme

Komut çubuğunu kendinize göre düzenleyebilirsiniz: düğmeleri gizleyebilir, sıralarını değiştirebilirsiniz.

## İki satır

Düğmeler pencereye sığmazsa çubuk kendiliğinden **ikinci satıra** yayılır; pencereyi genişletirseniz yeniden tek satıra iner. İki satıra da sığmayanlar çubuğun sağındaki **»** menüsüne düşer.

## Düğmelerin sırasını değiştirme

- Bir düğmeyi **tutup sürükleyin**; bırakacağınız yeri mavi çizgi gösterir.
- Tablo, Resim, Renk gibi **menüsü olan düğmeleri** sürüklemek için `Alt` tuşunu basılı tutarak sürükleyin (basit tıklama menüyü açar).
- Düğmeler gruplar hâlinde durur; taşıdığınız düğme bırakıldığı yerdeki gruba katılır ve ayırıcı çizgiler kendiliğinden düzenlenir.
- Sıra sonraki açılışlarda korunur. **Görünüm → Düğme Sırasını Sıfırla** (ya da özelleştirme menüsündeki aynı komut) varsayılan sıraya döner.

## Düğmeleri gösterme ve gizleme

- Çubuğun **en sağındaki özelleştir düğmesine** tıklayın ya da çubuğa **sağ tıklayın**.
- Menüde düğmeler gruplar halindedir (Yazı Tipi, Karakter Biçimi, Paragraf, Listeler ve Girinti, Ekle ve Sayfa, Sesle Yazma, Yazı Tipleri). İşaretli olanlar çubukta görünür; bir gruba **Tümünü Göster** / **Tümünü Gizle** uygulanabilir.
- **Komut Çubuğunu Özelleştir…** tüm düğmeleri ikonlarıyla, işaret kutulu bir listede gösterir.
- **Gizlenenleri Geri Getir** tüm düğmeleri yeniden gösterir.

Gizlediğiniz düğmelerin **klavye kısayolları çalışmaya devam eder** (ör. Kalın düğmesi gizliyken `Ctrl+B`). Seçiminiz sonraki açılışlarda hatırlanır.

## Pencere dar olduğunda

Sığmayan düğmeler çubuğun sağındaki **»** düğmesinin menüsüne taşınır; tablo, resim, renk gibi menülü düğmeler orada alt menü olarak açılır.

<!-- konu: kisayollar | Klavye Kısayolları | keyboard -->
# Klavye Kısayolları

## Dosya

| İşlem | Kısayol |
|---|---|
| Yeni belge | `Ctrl+N` |
| Aç | `Ctrl+O` |
| Kaydet | `Ctrl+S` |
| Farklı Kaydet | `F12` |
| Yazdır | `Ctrl+P` |
| Yardım | `F1` |

## Düzenleme

| İşlem | Kısayol |
|---|---|
| Geri Al | `Ctrl+Z` |
| Yinele | `Ctrl+Y` |
| Kes | `Ctrl+X` |
| Kopyala | `Ctrl+C` |
| Yapıştır | `Ctrl+V` |
| Yalnızca Metni Koru | `Ctrl+Shift+V` |
| Bul | `Ctrl+F` |
| Değiştir | `Ctrl+H` |
| Sonraki eşleşme | `F3` |
| Önceki eşleşme | `Shift+F3` |
| Bağlantı ekle / düzenle | `Ctrl+K` |
| Bağlantıyı aç | `Ctrl` + tıklama |
| Çeviri | `Ctrl+Shift+T` |
| Sonraki yazım hatası | `F7` |

## Biçim

| İşlem | Kısayol |
|---|---|
| Kalın | `Ctrl+B` |
| İtalik | `Ctrl+I` |
| Altı Çizili | `Ctrl+U` |
| Yazı tipini büyüt | `Ctrl+]` |
| Yazı tipini küçült | `Ctrl+[` |
| Biçimlendirmeyi temizle | `Ctrl+Space` |
| Sola hizala | `Ctrl+L` |
| Ortala | `Ctrl+E` |
| Sağa hizala | `Ctrl+R` |
| İki yana yasla | `Ctrl+J` |
| Madde işaretleri | `Ctrl+Shift+L` |
| Numaralandırma | `Ctrl+Shift+N` |

## Diğer

| İşlem | Kısayol |
|---|---|
| Sesle yaz (başlat/durdur) | `Ctrl+Shift+M` |
| Sesli oku (başlat/durdur) | `Ctrl+Alt+Space` |
| Tabloda sonraki / önceki hücre | `Tab` / `Shift+Tab` |
| Liste seviyesi indir / çıkar | `Tab` / `Shift+Tab` (madde başında) |
| Aynı paragrafta alt satır | `Shift+Enter` |
| Resim kırpmayı uygula / vazgeç | `Enter` / `Esc` |
| Yakınlaştır / uzaklaştır | `Ctrl` + fare tekerleği |

<!-- konu: gizlilik | Gizlilik ve Sorun Giderme | info -->
# Gizlilik ve Sorun Giderme

## Gizlilik

- Sözcük'ün tüm özellikleri bilgisayarınızda çalışır. Belgeleriniz, sesiniz ve dikte edilen metin hiçbir sunucuya gönderilmez.
- İnternet yalnızca şu durumlarda kullanılır: sesle yazmanın ilk kullanımında konuşma tanıma modelinin indirilmesi, çevirinin ilk kullanımında dil paketinin indirilmesi ve isterseniz Windows'a Türkçe yazım bileşeninin eklenmesi.
- Google Drive / OneDrive'daki belgeleri buluta Sözcük değil, bilgisayarınızdaki Google Drive / OneDrive uygulaması gönderir; Sözcük hesabınıza bağlanmaz.

## Tanılama günlüğü

Sözcük, sorunları bulmaya yardımcı olmak için işlem kayıtları tutar (ör. "belge açıldı", "hata oluştu"). Bu kayıtlarda **belge içeriği, dikte edilen metin ya da dosya adları yer almaz**. Klasörü **Dosya → Tanılama Günlüğü Klasörünü Aç** ile açabilir, bir sorun bildirirken bu dosyaları paylaşabilirsiniz.

## Sık karşılaşılan durumlar

- **Yazım denetimi çalışmıyor:** durum çubuğundaki yazım düğmesinin menüsüne bakın; bkz. [Yazım Denetimi](konu:yazim).
- **Mikrofon bulunamadı:** Windows Ayarları → Gizlilik → Mikrofon'dan masaüstü uygulamalarının mikrofona erişimine izin verin.
- **Sesle yazma ilk seferde uzun sürüyor:** model indiriliyor ya da yükleniyor; sonraki kullanımlar hızlıdır.
- **PDF açılamıyor:** taranmış PDF'lerde seçilebilir metin yoktur.
- **Eski Word belgesi (.doc) yalnızca metin olarak açıldı:** bilgisayarda Microsoft Word ya da LibreOffice yok; birini kurunca biçimlendirmesiyle açılır. Bkz. [Dosya Biçimleri](konu:bicimler).
- **Açılan Word belgesinde uyarı çıktı:** belgede Sözcük'ün desteklemediği öğeler var; özgün dosyayı korumak için **Farklı Kaydet** kullanın.
- **Başlıkta "Google Drive'a kaydedilemedi" yazıyor:** görev çubuğundaki Google Drive uygulamasının çalıştığını ve oturumun açık olduğunu denetleyin; Sözcük kendiliğinden yeniden dener.
- **Program beklenmedik şekilde kapandı:** yeniden açınca kaydedilmemiş belgeniz için **Geri Yükle** seçeneği çıkar.
