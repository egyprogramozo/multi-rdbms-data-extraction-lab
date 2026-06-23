# Multi-RDBMS Data Extraction Lab

![Multi-RDBMS Data Extraction Lab](images/00_project_hero/multi_rdbms_data_extraction_lab_hero.png)

Ez a repó egy többforrásos adatkinyerési portfólióprojektet mutat be. A cél egy valószerű Data Engineering labor felépítése: több különböző forrásrendszerből `EFF_DAT` alapján rendelési adatok kinyerése, majd forrásonkénti CSV landing állományok előállítása biztonságos staging → landing logikával.

A projektben öt relációs adatbázis export nézeten keresztül adja át a rendelési adatokat, a hatodik forrás pedig egy manual / legacy CSV file-drop bemenet.

## Mit bizonyít ez a projekt?

A projekt nem csak azt mutatja meg, hogy több adatbázishoz lehet kapcsolódni, hanem egy kontrollált adatkinyerési folyamatot is bizonyít:

- több RDBMS forrás egységes kezelése;
- read-only export nézetek használata alaptáblák közvetlen olvasása helyett;
- `EFF_DAT` alapú, kézzel vezérelt feldolgozási nap;
- forrásonkénti CSV landing állományok;
- staging → landing safe replace logika;
- újrafuttathatóság ugyanarra az `EFF_DAT` értékre;
- hiba esetén az érintett landing fájl védelme;
- részleges hiba esetén a többi forrás további futása;
- dokumentált logok, képernyőképek és mintakimenetek.

A repo fókusza: **rendszertervezés, adatkinyerési logika, validáció, hibaágak és bizonyíték-alapú dokumentálás**.

## Projektállapot

Jelenlegi projektállapot: **v2.0.3 – publikálás előtti dokumentációs audit és end-to-end extraction checkpoint**.

A v2.0 állapot bizonyította a működő end-to-end kinyerési folyamatot. A v2.0.3 állapot a publikálás előtti tisztított, dokumentált és ellenőrzött változat: a működő Python / PowerShell logika változatlan, a dokumentáció és a repo-szerkezet pedig véglegesítésre került.

A projekt már nemcsak az adatforrások elérését bizonyítja, hanem a tényleges `EFF_DAT`-alapú kinyerési folyamatot is:

- manual CSV / file-drop forrás validálása és landing CSV előállítása;
- öt adatbázisos forrás connection + export view SELECT ellenőrzése;
- öt adatbázisból tényleges CSV kinyerés;
- többnapos, kontrollált tesztsorozat `2026-06-16` és `2026-06-20` között;
- ugyanarra az `EFF_DAT` értékre történő újrafuttatás;
- hibaszimuláció rossz MySQL porttal;
- hiba esetén meglévő landing fájl érintetlenül hagyása;
- a többi adatforrás futásának folytatása részleges hiba esetén;
- részletes futási logok és képi bizonyítékok.

A teljes lezáró tesztsorozat eredménye: **PASS**.

![Teljes többnapos kinyerési tesztsorozat PASS](images/11_full_extraction_test_series/01_full_extraction_test_series_pass.png)

A csomag működése külön kicsomagolt repómappából is igazolásra került: friss lokális `.env` beállítással, külön bemásolt Db2 JDBC driverrel, majd 5/5 DB connection, 5/5 DB extraction és teljes többnapos test series `PASS` eredménnyel. Ez azt igazolta, hogy a projekt nem csak a fejlesztői munkamappában, hanem tiszta kicsomagolás után is újraindítható.

## Forrásrendszerek

| Forrás                 | Kapcsolódási / feldolgozási mód                       | v2.0 állapot        |
| ---------------------- | ----------------------------------------------------- | ------------------- |
| MSSQL / SQL Server     | `pymssql`                                             | `SUCCESS_WITH_ROWS` |
| Oracle                 | `oracledb`                                            | `SUCCESS_WITH_ROWS` |
| IBM Db2                | JDBC, `JayDeBeApi` / `JPype1` / lokális `db2jcc4.jar` | `SUCCESS_WITH_ROWS` |
| MySQL                  | `mysql-connector-python`                              | `SUCCESS_WITH_ROWS` |
| PostgreSQL             | `psycopg2`                                            | `SUCCESS_WITH_ROWS` |
| Manual CSV / file-drop | lokális céloldali input mappa                         | `SUCCESS_WITH_ROWS` |

Az adatbázisos források read-only export nézeten keresztül érhetők el. A kinyerő oldali cél nem az alaptáblák közvetlen elérése, hanem egy kontrollált, stabil export interfész használata.

## Fő folyamat

A projektben az `EFF_DAT` kézzel állított feldolgozási nap.

```text
forrásrendszerek
        ↓
kontrollált export nézetek / file-drop CSV bemenet
        ↓
EFF_DAT szerinti szűrés
        ↓
staging CSV
        ↓
sikeres futás esetén landing CSV csere
        ↓
logolás és bizonyítékok
```

A staging → landing logika lényege, hogy egy forrás meglévő landing fájlja csak akkor cserélődik, ha az adott forrás új kinyerése sikeresen lefutott. Hibás futás esetén az adott forrás korábbi landing fájlja változatlan marad.

## Fő scriptek

Manual CSV / file-drop kinyerés:

```text
src/check_manual_csv_source.py
```

Adatbázis-kapcsolatok ellenőrzése:

```text
src/check_database_connections.py
```

Adatbázisos források kinyerése CSV landing állományokba:

```text
src/extract_database_sources.py
```

Manual CSV tesztsorozat:

```text
tools/run_manual_csv_test_series.ps1
```

Teljes, többnapos kinyerési tesztsorozat:

```text
tools/run_full_extraction_test_series.ps1
```

Windows PowerShell környezetben a teljes tesztsorozatot a gép execution policy beállítása blokkolhatja. A tesztkörnyezetben ezért kontrolláltan így futott:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_full_extraction_test_series.ps1
```

## Kimeneti mappaszerkezet

A futási kimenetek alapértelmezett helyei:

```text
data/staging/{EFF_DAT}/
data/landing/{EFF_DAT}/
```

Adatbázisos forrásoknál:

```text
data/staging/{EFF_DAT}/database_sources/
data/landing/{EFF_DAT}/database_sources/
```

Példa landing fájlok:

```text
data/landing/2026-06-16/manual_csv_orders_2026-06-16.csv
data/landing/2026-06-16/database_sources/mssql_orders_2026-06-16.csv
data/landing/2026-06-16/database_sources/oracle_orders_2026-06-16.csv
data/landing/2026-06-16/database_sources/db2_orders_2026-06-16.csv
data/landing/2026-06-16/database_sources/mysql_orders_2026-06-16.csv
data/landing/2026-06-16/database_sources/postgresql_orders_2026-06-16.csv
```

Az `EFF_DAT` a mappanévben és a fájlnévben is megjelenik. Ez azért fontos, mert így egy korábbi napra történő újrafuttatás nem írja felül egy másik nap landing eredményét.

A publikus repóban a runtime `data/landing/` és `data/staging/` mappák csak `.gitkeep` fájlokkal szerepelnek. A tesztelt mintakimenetek az `evidence/` mappában találhatók.

## Bizonyított működés

A v2.0 lezáró tesztsorozatban ezek az `EFF_DAT` értékek futottak:

```text
2026-06-16
2026-06-17
2026-06-18
2026-06-19
2026-06-20
```

Minden napon:

- manual CSV extraction: `SUCCESS_WITH_ROWS`;
- database extraction: exit code `0`;
- database landing files: `5/5`;
- eredmény: `PASS`.

A tesztsorozat külön ellenőrizte az újrafuttatást és a hibaágat is:

- `2026-06-16` újrafuttatás: `PASS`;
- MySQL hibaszimuláció rossz porttal: `FAILED_PORT_UNREACHABLE`;
- MySQL output action: `LEFT_EXISTING_FILE_UNCHANGED`;
- a MySQL landing fájl hash / timestamp alapján változatlan maradt;
- a többi DB forrás közben sikeresen lefutott;
- `config/.env` a teszt végén visszaállt.

## Fontos bizonyítékok

```text
evidence/manual-csv-test-series/
evidence/database-connection-tests/
evidence/database-extraction/
evidence/full-extraction-test-series/
```

Kiemelt logok:

```text
evidence/database-connection-tests/final-5db-success/database_connection_test_20260621_075511.log
evidence/database-extraction/logs/database_extraction_20260621_075557.log
evidence/full-extraction-test-series/logs/full_extraction_test_series_20260621_075529.log
```

Kiemelt képek:

```text
images/09_database_connection_tests/06_all_five_database_sources_success.png
images/10_database_extraction/01_database_extraction_5db_success.png
images/11_full_extraction_test_series/01_full_extraction_test_series_pass.png
```

## Dokumentáció

Részletes leírások:

```text
docs/01_project_overview.md
docs/02_source_export_views.md
docs/03_readonly_export_access.md
docs/04_manual_csv_source.md
docs/05_codex_workspace_started.md
docs/06_eff_dat_extraction_logic.md
docs/07_manual_csv_test_series.md
docs/08_file_transfer_boundary_and_codex_smb_diagnostics.md
docs/09_database_connection_tests.md
docs/10_database_extraction.md
docs/11_full_extraction_test_series.md
```

## Helyi konfiguráció és smoke test

A publikus repó nem tartalmaz valós `config/.env` fájlt. Helyi futtatáshoz a mintafájlt kell lemásolni:

```powershell
copy .\config\.env.example .\config\.env
notepad .\config\.env
```

A portok a mintában standard alapértékekkel szerepelnek, de a host, database/service, user és password értékeket a saját laborkörnyezethez kell kitölteni. Db2 esetén a JDBC driver JAR helyileg szükséges a `local_drivers/db2/` mappában, de nem része a repónak.

A közös `DB_USERNAME` / `DB_PASSWORD` változónév lab-egyszerűsítés. A jogosultsági modell ettől még forrásonként read-only export user szemléletű; valós környezetben motoronként és forrásonként külön credential- és secret-kezelés lenne indokolt.

A külön kicsomagolt repómappás smoke test a következő sorrendben futott:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" .\src\check_manual_csv_source.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" .\src\check_database_connections.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" .\src\extract_database_sources.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_full_extraction_test_series.ps1
```

## Db2 JDBC megjegyzés

Az IBM Db2 kapcsolat JDBC útvonalon működött:

```text
JayDeBeApi + JPype1 + db2jcc4.jar
```

A `db2jcc4.jar` helyi driverfüggőség, ezért nem része a publikus repónak. A mintakonfiguráció csak a várt lokális útvonalat mutatja:

```env
DB2_JDBC_JAR=local_drivers/db2/db2jcc4.jar
DB2_JDBC_CLASS=com.ibm.db2.jcc.DB2Driver
```

A `local_drivers/` mappa és a `*.jar` fájlok `.gitignore` alatt vannak.

## Hogyan készült ez a projekt?

A projekt AI-assisted fejlesztési módszerrel készült.

A rendszer architektúráját, az export view-koncepciót, az `EFF_DAT` alapú futtatási logikát, a staging → landing safe replace elvet, a read-only export access modellt, valamint a tesztforgatókönyveket én terveztem és validáltam.

A Python és PowerShell implementáció elkészítésében Codex segített a megadott specifikáció alapján, kontrollált, jóváhagyás-alapú munkafolyamatban. A projektben a hangsúly nem az önálló Python-fejlesztői bizonyításon van, hanem azon, hogy egy többforrásos adatkinyerési folyamat logikája, tesztelése, hibaági viselkedése és dokumentálása végig ellenőrzött legyen.

A működést viselkedés-alapú és integrációs tesztek igazolják: a tényleges CSV outputokat, futási logokat, újrafuttatásokat és hibaágakat vetettem össze az elvárt eredményekkel. A dokumentáció és a kód többkörös AI-assisted review-n is átment, beleértve ChatGPT-alapú ellenőrzést és külső Claude review szempontokat is.

## Scope és tudatos korlátok

A projekt célja nem egy teljes production-grade orchestration platform megvalósítása. Nem része ennek a verziónak:

- Airflow vagy más scheduler;
- control table alapú feldolgozásvezérlés;
- automatikus többnapos backfill éles logikában;
- szerverek közötti file transfer komponens;
- központi monitoring rendszer;
- unit test csomag;
- konténerizált teljes laborkörnyezet.

Tudatos későbbi fejlesztési irányok:

- a `check_database_connections.py` és `extract_database_sources.py` közös részeinek kiszervezése például `src/db_sources.py` modulba;
- `EFF_DAT` lekérdezések további paraméterezése / bind változók használata;
- manual CSV customer snapshot logika point-in-time historizálása;
- staging-kezelés egységesítése a DB és manual CSV ág között;
- PowerShell scriptek hordozhatóbb Python-útvonal kezelése `PYTHON_EXE` override + `python` / `py` fallback megoldással;
- production-grade ütemezési, monitoring és unit test réteg hozzáadása.

A v2.0.3 célja egy működő, reprodukálható, dokumentált adatkinyerési labor bemutatása: több forrás, `EFF_DAT` szűrés, CSV landing, hibatűrés, újrafuttathatóság és bizonyítékok.
