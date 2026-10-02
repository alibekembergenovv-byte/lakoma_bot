# «Lakoma» Katering Servisi ushın Telegram Bot

Qaraqalpaqstandaǵı emlewxanalar kúnlik awqat sanların kiritip barıwı hám «Lakoma» katering xızmeti ushın kúnlik/aylıq esabatlar hám Excel kestelerin generaciya qılıwshı sistema.

---

## 🚀 Tiykarǵı imkaniyatlar

1. **Bolnicalar dizimnen ótiwi:**
   - Qaraqalpaqstan rayonların saylaw (Nókis qalası, Xojeli, Qaraózek, Shımbay, Taxtakópir hám b.).
   - Rayonǵa tiyisli emlewxananı (RMO, TUb, Balalar emlewxanası hám b.) saylaw.
   - Xızmetker atı-familiyası hám telefon nomerin tastıyıqlaw (kontakt túymesi yamasa format boyınsha qol menen kiritish).

2. **Admin moderaciyası:**
   - Jańa dizimnen ótken bolnica xızmetkerleri «kútilip atırǵanlar» dizimine túsedi.
   - Lakoma administratorı xızmetkerdi bir basıw menen tastıyıqlaydı (`✅ Tastıyıqlaw`) yamasa biykarlaydı (`❌ Biykar etiw`).
   - Xızmetkerge tastıyıqlanǵanlıǵı haqqında xabar avtomatik jetkeriledi.

3. **Kúnlik awqat sanların kiritip barıw:**
   - Azanǵı awqat (Zavtrak), Túslik awqat (Obet) hám Keshki awqat (Ujin) sanların basqıshpa-basqısh kiritish.
   - Qosımsha izoh / eskertpe kiritish imkaniyatı.
   - Kiritilgen maǵlıwmatlardı qayta tekseriw hám tastıyıqlaw kartochkası.
   - Búgingi kiritilgen sanlardı qayta kóriw hám jańalaw imkaniyatı.

4. **Administrator paneli:**
   - 📈 **Búgingi ulıwma jıyıntıq:** Rayonlar hám bolnicalar kesiminde awqat sanları, jámi esap.
   - ⚠️ **Kiritpegenler dizimi:** San kiritpegen bolnicalar hám olardıń biriktirilgen xızmetkerleri haqqında tolıq maǵlıwmat.
   - 📢 **Esletpe jiberiw:** Bir túyme menen búgingi san kiritpegen barlıq xızmetkerlerge avtomat túrde esletpe xatı jiberiledi.
   - 📥 **Excel esabatlar:** Kúnlik hám aylıq qánigelesken kestelerdi avtomat jaratıw hám Telegram arqalı júklep beriw.

5. **Kórkem Excel (.xlsx) eksport:**
   - Professional Lakoma katering brending stilleri (kók heder, turaqlı fontlar, borderler, qosımsha eskertpeler, kúnlik/aylıq jıyıntıq formulaları).

---

## 🛠 Texnologiyalar

- **Python 3.12+**
- **Aiogram 3.x** — Asinxron Telegram Bot freymvorki (FSM, Routerler, Inline/Reply Keyboards)
- **aiosqlite** — Asinxron SQLite maǵlıwmatlar bazası
- **openpyxl** — Excel (.xlsx) formatındaǵı professional esabatlar generaciyası
- **pytest & pytest-asyncio** — 100% test qaplaması (birlik, integraciya hám E2E simulyaciya)

---

## 📁 Proekt strukturası

```
lakoma_catering_bot/
├── bot/
│   ├── config.py              # Konfiguraciya (.env júklew, admin ID-ler, kataloglar)
│   ├── database/
│   │   ├── db.py              # SQLite sxeması hám rayonlar/bolnicalar dáslepki maǵlıwmatları
│   │   └── queries.py         # Asinxron DB sorawları (users, daily_records, summaries)
│   ├── handlers/
│   │   ├── admin.py           # Admin paneli, moderaciya, esletpeler, Excel júklew
│   │   ├── registration.py    # Bolnica xızmetkerlerin dizimnen ótkeriw FSM
│   │   ├── report.py          # Kúnlik awqat sanların kiritip barıw FSM
│   │   └── start.py           # Start komandası hám tiykarǵı menyu
│   ├── keyboards/
│   │   ├── reply.py           # Reply menyu túymeleri (bolnica hám admin)
│   │   └── inline.py          # Inline túymeler (rayonlar, moderaciya, Excel parametrleri)
│   └── services/
│       └── excel_service.py   # Kúnlik hám aylıq qánigelesken Excel faylların generaciya qılıw
├── data/                      # SQLite maǵlıwmatlar bazası faylı (lakoma.db)
├── exports/                   # Generaciya qılınǵan Excel faylları saqlanatuǵın papka
├── tests/                     # Pytest testler kompleksi
│   ├── test_admin_handlers.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_e2e_simulation.py # Tolıq biznes-cikldi tekseriwshi E2E test
│   ├── test_excel_service.py
│   ├── test_keyboards.py
│   ├── test_registration_handlers.py
│   └── test_report_handlers.py
├── run.py                     # Botty iske qosıwshı tiykarǵı fayl
├── requirements.txt           # Kerekli Python paketleri
├── .env.example               # Úlgi sazlawlar faylı
└── README.md                  # Hújjetlestiriw
```

---

## ⚙️ Ornatıw hám iske qosıw

### 1. Repozitoriyanı klonlaw yamasa papkaǵa ótiw:
```bash
cd d:/Programms/Lakoma/lakoma_catering_bot
```

### 2. Virtual ortalıqtı jaratıw hám aktivlestiriw:
```bash
python -m venv venv
venv\Scripts\activate   # Windows ushın
# source venv/bin/activate  # Linux/macOS ushın
```

### 3. Kerekli kitapxanalardı ornatıw:
```bash
pip install -r requirements.txt
```

### 4. `.env` faylın sazlaw:
`.env.example` nusqasın kóshirip alıp `.env` jaratıń:
```bash
copy .env.example .env
```
`.env` faylın ashıp Telegram maǵlıwmatlarıńızdı kiritiń:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321
DB_PATH=data/lakoma.db
EXPORTS_DIR=exports
```

### 5. Botty iske qosıw:
```bash
python run.py
```

---

## 🧪 Testlerdi iske qosıw

Barlıq birlik, integraciya hám E2E simulyaciya testlerin iske qosıw ushın:

```bash
pytest -v
```

Jeke E2E simulyaciya testin iske qosıw:
```bash
pytest tests/test_e2e_simulation.py -v
```
