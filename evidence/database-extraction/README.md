# Adatbázisos kinyerési bizonyítékok

Ez a mappa az öt adatbázisos forrásból történő tényleges CSV landing kinyerés válogatott bizonyítékait tartalmazza.

## Tartalom

```text
logs/
```

## Kiemelt logok

Tiszta smoke extraction futás:

```text
logs/database_extraction_20260621_075521.log
```

Ebben mind az öt adatbázisos forrás `SUCCESS_WITH_ROWS` státuszt adott, az output action pedig `CREATED_NEW_FILE` volt, mert a landing fájlok ebben a friss tesztmappában még nem léteztek.

Újrafuttatás / safe replace ellenőrzés:

```text
logs/database_extraction_20260621_075557.log
```

Ebben mind az öt adatbázisos forrás `SUCCESS_WITH_ROWS` státusszal zárult, és a landing CSV-k `REPLACED_EXISTING_FILE` output actionnel frissültek.

MySQL port-hiba szimuláció:

```text
logs/database_extraction_20260621_075606.log
```

Ebben a MySQL forrás `FAILED_PORT_UNREACHABLE` státusszal zárult, miközben a többi adatbázisos forrás sikeresen lefutott. A MySQL landing fájl `LEFT_EXISTING_FILE_UNCHANGED` actionnel védve maradt.

## Korábbi támogató logok

A mappában szerepelnek korábbi támogató futások is:

```text
logs/database_extraction_20260621_063628.log
logs/database_extraction_20260621_064417.log
logs/database_extraction_20260621_064547.log
```

Ezek ugyanazt a működési logikát mutatják egy korábbi lokális munkamappában: sikeres kinyerés, újrafuttatás és MySQL port-hiba esetén a landing védelem.

## Megjegyzés a lokális útvonalakról

A logokban látható lokális mappanevek, például `RepoSmokeTest` vagy `multi-rdbms-data-extraction-lab-v2.0.1`, a teszteléshez használt helyi munkamappák nevei. Ezek nem publikus release-verzióként értelmezendők.

A runtime `data/` kimenetek nem kerülnek közvetlenül verziózásra. A többnapos teljes tesztsorozat válogatott mintakimenetei külön evidence commitban szerepelnek majd:

```text
evidence/full-extraction-test-series/sample-landing-outputs/
```

## Publikálási döntés

A publikus repó nem tartalmaz:

- valós `.env` fájlt;
- jelszót vagy secretet;
- lokális Db2 JDBC driver JAR fájlt;
- teljes runtime `data/` kimeneti mappát.

A bizonyítékok célja annak bemutatása, hogy a DB extractor képes volt az öt adatbázisos export nézetből `EFF_DAT` alapján CSV landing kimeneteket előállítani, újrafuttatáskor cserélni a meglévő landing fájlokat, és forráshiba esetén megvédeni a korábbi sikeres kimenetet.
