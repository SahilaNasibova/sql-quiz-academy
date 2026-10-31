# SQL Quiz Academy

Azərbaycan dilində Oracle SQL və PL/SQL test platforması. Streamlit interfeysi tünd yan menyu, bənövşəyi banner, real statistika və mövzu kartları ilə hazırlanıb.

## Lokal işə salmaq

Python 3.12 istifadə edin:

```bash
cd /workspace/sql-quiz-academy
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 0.0.0.0
```

Lokal sınaqda SQLite avtomatik yaradılır. İctimai tətbiqdə davamlı yaddaş üçün Supabase PostgreSQL istifadə edin. SQLite məlumatları Streamlit Cloud yenidən başladıqda itə bilər.

## Müəllim hesabı və gizli konfiqurasiya

Standart müəllim ünvanı `sahila.nasibova1@gmail.com`-dur. Bu ünvan açıq qeydiyyatda bloklanır. Hesab yalnız serverdə `TEACHER_PASSWORD` təyin olunanda yaradılır. Şifrə ən azı 10 simvol olmalıdır; tətbiqdə scrypt ilə heşlənir. Şifrə dəyişəni mövcud hesabın şifrəsini dəyişmir. İlkin yaradılmadan sonra onu konfiqurasiyadan silmək olar.

Streamlit Community Cloud → App settings → Secrets bölməsinə aşağıdakı açarları əlavə edin. Şifrələri GitHub-a və ya çata yazmayın. Lokal istifadə üçün eyni açarları `.streamlit/secrets.toml` faylında saxlamaq olar; fayl Git tərəfindən nəzərə alınmır.

```toml
TEACHER_EMAIL = "sahila.nasibova1@gmail.com"
# TEACHER_PASSWORD = burada öz güclü ilkin şifrənizi təyin edin
# DATABASE_URL = Supabase-dən alınan SQLAlchemy bağlantısı
```

`DATABASE_URL` formatı: `postgresql+psycopg://USER:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require`. Supabase → Connect → Session pooler bağlantısını istifadə edin (IPv4 dəstəyi). İstifadəçi adı adətən `postgres.PROJECT_REF` olur. Şifrədəki xüsusi simvollar URL kodlaşdırılmalıdır. Bağlantı məlumatlarını yalnız Secrets bölməsində saxlayın.

Tətbiq PostgreSQL-də `quiz_academy` adlı ayrıca schema yaradır; cədvəllər Supabase-in standart `public` schema-sına yazılmır. Bu schema-nı Supabase Data API-nin exposed schemas siyahısına əlavə etməyin və anon/authenticated rollarına giriş verməyin. İlkin bağlantı rolunun schema və cədvəl yaratmaq icazəsi olmalıdır. Tətbiq yalnız serverdəki PostgreSQL bağlantısından istifadə edir. Supabase bağlantısı bu mühitdə hələ yoxlanmayıb; yayımdan əvvəl öz layihənizdə sınaq tələb olunur.

## Funksiyalar

- Ad-soyad, e-poçt və şifrə ilə tələbə qeydiyyatı; müəllim rolu yalnız konfiqurasiya olunmuş hesaba verilir.
- Oracle SQL və PL/SQL nümunə sualları; müəllim panelində “Nümunə sualları əlavə et” düyməsi ilə yüklənir.
- A–D variantları, Markdown SQL kod blokları, əvvəlki/növbəti sual, hər saniyə yenilənən sayğac.
- Server vaxtına əsaslanan son tarix; cavablar serverdə yadda saxlanılır. Aktiv test girişdən sonra davam edir; sessiya bağlansa belə vaxt dayanmaz.
- Cavab açarı test zamanı brauzerə göstərilmir. Test bitdikdən sonra bal, faiz və izahlar görünür.
- Sual bankı, redaktə, silmə, mövzu və sual balı; ümumi test müddəti 1–180 dəqiqədir. Mövzu üzrə bütün aktiv suallar testə daxil olur.
- CSV/XLSX idxalı və CSV şablonu; tələbə nəticələri, çətin sual statistikası, Excel ixracı.
- Davam edən testlər sualların başlanğıc nüsxəsini saxlayır; sonrakı redaktə qiymətləndirməni dəyişmir.

## Streamlit Community Cloud-da yayımlamaq

1. Supabase pulsuz layihəsi yaradın; server bağlantısını və cədvəl giriş məhdudiyyətlərini hazırlayın.
2. Streamlit Community Cloud-da GitHub hesabınıza daxil olun, bu reponu, `main` branch və `app.py` faylını seçin. Python 3.12 seçin.
3. Advanced settings / Secrets bölməsində `DATABASE_URL`, `TEACHER_EMAIL`, ilkin `TEACHER_PASSWORD` təyin edin.
4. Deploy edin, müəllim hesabına daxil olun və nümunə sualları əlavə edin.
5. Tələbə kimi ayrıca hesab yaradaraq tam testi yoxlayın; telefon ekranında menyu, variantlar və nəticələri yoxlayın. Bundan sonra Streamlit-in verdiyi real `*.streamlit.app` ünvanını paylaşın.

Pulsuz planlarda tətbiq yatması, verilənlər bazasının dayandırılması, saxlanma və hesablama limitləri ola bilər. Streamlit və Supabase-in cari limitlərini hesab panellərindən yoxlayın. Bu layihə Oracle serverinə SQL icra etmir; SQL/PLSQL üzrə çoxvariantlı bilik yoxlamasıdır.

## Yoxlamalar

```bash
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

Avtomatik yoxlamalar giriş, müəllim səlahiyyəti, cavab açarının gizliliyi, server vaxt limiti, nəticələrin hesablanması, testin təkrar bitirilməsi və Streamlit giriş/test/panel axınlarını yoxlayır.

İlk versiyada e-poçt təsdiqi, şifrə bərpası, MFA, paylaşılmış giriş cəhd limiti və ayrıca adlandırılmış testlərin idarəsi yoxdur. Şəxsi istifadə və kiçik pilot üçün başlayın; geniş ictimai istifadə üçün bunları və verilənlər bazası ehtiyat nüsxələrini ayrıca hazırlayın.
