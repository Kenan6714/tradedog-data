# TradeDog Data Repository

Bu repo, TradeDog uygulaması için BIST100 hisse senetleri ve yatırım fonları verilerini içerir.

## 📁 Dosyalar

### `bist100.json`
- BIST100 endeksindeki 100 hisse senedinin listesi
- Sektörel sınıflandırma
- Her hisse için: Sembol, İsim, Sektör

**Güncelleme Sıklığı:** Haftalık (gerektiğinde)

### `funds.json` (yakında)
- Yatırım fonları listesi
- Fon kategorileri
- ISIN kodları

## 🔄 Nasıl Güncellenir?

1. JSON dosyasını düzenle
2. GitHub'a commit et
3. TradeDog otomatik olarak her gün saat 10:10'da güncel veriyi çeker

## 📊 Veri Formatı

### bist100.json
```json
{
  "last_updated": "2025-01-21",
  "bist100": [
    {
      "symbol": "THYAO",
      "name": "Türk Hava Yolları",
      "sector": "Ulaştırma",
      "sector_code": "transportation"
    }
  ],
  "sectors": {
    "transportation": {
      "name": "Ulaştırma",
      "stocks": ["THYAO", "PGSUS"]
    }
  }
}
```

## ⚡ Özellikler

- ✅ Gerçek zamanlı fiyatlar (Yahoo Finance)
- ✅ Otomatik güncelleme (her gün saat 10:10)
- ✅ Offline cache
- ✅ Sektörel analiz
- ✅ Tamamen ücretsiz

## 📝 Lisans

Bu veri seti TradeDog uygulaması için hazırlanmıştır.

---

**Son Güncelleme:** 2025-01-21
