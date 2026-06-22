# Projektáttekintés

## Cél

A Multi-RDBMS Data Extraction Lab egy portfólióprojekt, amely egy többforrásos adatkinyerési folyamatot modellez.

A projekt fő célja annak bemutatása, hogy különböző forrásrendszerekből kontrollált export interfészeken keresztül, `EFF_DAT` alapján, forrásonkénti CSV landing állományok készíthetők.

A v2.0 end-to-end extraction állapot áttekintése:

- manual CSV / file-drop forrásból kinyerés;
- öt adatbázisos forrás connection + export view SELECT ellenőrzése;
- öt adatbázisból tényleges CSV landing kinyerés;
- többnapos futtatási tesztsorozat;
- újrafuttathatóság;
- hiba esetén meglévő landing fájl védelme;
- részletes logolás és bizonyítékok.

## Fejlesztési és validálási megjegyzés

A projektben a forrásrendszer-logika, az `EFF_DAT` alapú működés, a staging → landing safe replace elv, az újrafuttathatóság és a tesztforgatókönyvek a fejlesztő logikai tervezése és jóváhagyása alapján készültek.

A Python / PowerShell implementáció elkészítésében az OpenAI Codex CLI segített, az elkészült megoldást pedig ChatGPT- és Claude-alapú review is támogatta.

A projekt elsősorban **rendszertervezési, specifikációs, tesztelési és kontrollált AI-assisted development** gyakorlatként értelmezendő. A tényleges validáció viselkedés-alapú és integrációs ellenőrzéssel történt: a CSV outputok, futási logok, újrafuttatások és hibaágak kerültek összevetésre az elvárt eredményekkel.

## Források

A projekt hat forrást kezel:

| Forrás                 | Típus            | Szerep                      |
| ---------------------- | ---------------- | --------------------------- |
| MSSQL                  | RDBMS            | kontrollált export view     |
| Oracle                 | RDBMS            | kontrollált export view     |
| PostgreSQL             | RDBMS            | kontrollált export view     |
| MySQL                  | RDBMS            | kontrollált export view     |
| IBM Db2                | RDBMS            | kontrollált export view     |
| Manual CSV / file-drop | fájl alapú input | legacy / kézi export modell |

A relational database források mindegyike `v_daily_orders_export` jellegű export nézeten keresztül adja át az adatokat. A manual CSV forrás céloldali local file-drop mappából dolgozik.

Az adatbázisos források logikai modellje least-privilege szemléletre épül. Az export folyamat nem közvetlen táblákat használ, hanem dedikált, csak olvasásra szánt export nézeteket. A lab egyszerűsítése érdekében a különböző adatbázisok kapcsolati beállításai egységes mintaszerkezetet követnek; valós credential nem kerül a repóba.

## Adatkinyerési modell

A projekt tudatosan nem automatikus napi schedulert valósít meg. Az `EFF_DAT` értéket a felhasználó állítja a `config/.env` fájlban.

Példa:

```env
EFF_DAT=2026-06-16
```

A kinyerő scriptek ez alapján dolgoznak:

```text
forrásrendszer
  ↓
EFF_DAT szerinti szűrés / fájlválasztás
  ↓
staging output
  ↓
siker esetén landing output csere
  ↓
log
```

## Safe replace logika

A projekt egyik fontos technikai döntése, hogy egy meglévő landing fájl csak akkor cserélődik, ha az adott forrás új kinyerése sikeresen lefutott.

Ez azt jelenti, hogy részleges forráshiba esetén:

- a hibás forrás korábbi landing fájlja érintetlen marad;
- a sikeres források frissülhetnek;
- a teljes futás exit code-ja hibát jelezhet;
- a log pontosan rögzíti, melyik forrás sikerült és melyik nem.

## v2.0 bizonyított állapot

A v2.0 tesztsorozatban a következő napok futottak:

```text
2026-06-16
2026-06-17
2026-06-18
2026-06-19
2026-06-20
```

Minden napon sikeres volt:

- a manual CSV kinyerés;
- az öt adatbázisos forrás kinyerése;
- az öt adatbázisos landing CSV meglétének ellenőrzése.

A tesztsorozat külön ellenőrizte, hogy MySQL port-hiba esetén a MySQL landing fájl változatlan marad, miközben a többi adatbázisos forrás továbbra is sikeresen frissül.

## Nem cél ebben a verzióban

A projekt v2.0 állapota nem teljes production orchestration rendszer. Nem célja:

- automatikus scheduler;
- Airflow DAG;
- control table alapú feldolgozásvezérlés;
- több szerver közötti file transfer megvalósítása;
- egységteszt-csomag;
- konténerizált teljes deployment;
- BI / riport réteg.

Ezek későbbi fejlesztési irányok lehetnek.
