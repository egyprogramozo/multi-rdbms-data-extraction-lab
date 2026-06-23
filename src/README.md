# Source code

Ez a mappa tartalmazza a Multi-RDBMS Data Extraction Lab Python alapú kinyerő és ellenőrző scriptjeit.

A kód célja:

- az adatbázisos források elérhetőségének ellenőrzése;

- az export nézetek `EFF_DAT` szerinti lekérdezése;

- CSV landing állományok előállítása;

- staging → landing safe replace logika alkalmazása;

- futási eredmények és hibák naplózása.

A projekt v2.0 állapotában a működés viselkedés-alapú és integrációs tesztekkel lett ellenőrizve: a tényleges CSV outputok, futási logok, újrafuttatások és hibaágak kerültek összevetésre az elvárt eredményekkel.

## TODO: közös adatbázis-forrás modul

A `check_database_connections.py` és az `extract_database_sources.py` között jelenleg van átfedés az adatbázis-források felépítésében és a kapcsolódási segédfüggvényekben.

Későbbi fejlesztési irányként érdemes ezeket közös modulba kiszervezni, például:

```text
src/db_sources.py
```

Ide kerülhetnek többek között:

- `build_sources()`;

- `tcp_check()`;

- `import_optional()`;

- az öt adatbázismotor közös connection konfigurációja;

- a motoronként eltérő, de újrahasznosítható kapcsolódási segédlogika.

Ez csökkentené a kódduplikációt, egyszerűbbé tenné új forrás hozzáadását, és mérsékelné annak kockázatát, hogy a connection checker és az extraction script konfigurációja idővel eltérjen egymástól.
