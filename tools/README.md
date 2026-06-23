# Tools

Ez a mappa a laborhoz használt PowerShell segédscripteket tartalmazza.

A scriptek célja nem production scheduler vagy teljes orchestration réteg megvalósítása, hanem a labban kialakított adatkinyerési logika kontrollált tesztelése és bizonyítása.

## run_manual_csv_test_series.ps1

A manual CSV ág kontrollált tesztsorozatát futtatja.

A script fő feladatai:

- baseline mappából visszaállítja a working input mappát;
- tesztenként módosítja az `EFF_DAT` értékét;
- szándékosan manipulálja a working forrásfájlokat;
- futtatja a manual CSV kinyerő scriptet;
- ellenőrzi az elvárt státuszokat;
- tesztsorozat-logot ír;
- a végén visszaállítja a working input mappát és a `config/.env` tartalmát.

A tesztsorozat célja annak ellenőrzése, hogy a manual CSV ág helyesen kezeli többek között:

- sikeres, sorokat tartalmazó kinyerést;
- `SUCCESS_EMPTY` esetet;
- hiányzó vagy hibás input fájlokat;
- customer hivatkozási hibákat;
- staging → landing safe replace működést.

## run_full_extraction_test_series.ps1

A teljes v2.0 end-to-end kinyerési tesztsorozatot futtatja.

A script fő feladatai:

- menti a `config/.env` aktuális tartalmát;
- több `EFF_DAT` értékre futtatja a manual CSV és database extraction scripteket;
- ellenőrzi a landing és staging mappák meglétét;
- ellenőrzi az öt adatbázisos landing CSV-t;
- újrafuttatási tesztet végez;
- MySQL port-hibát szimulál;
- ellenőrzi, hogy hibás MySQL futás esetén a korábbi MySQL landing fájl érintetlen maradt-e;
- ellenőrzi, hogy MySQL hiba közben a többi DB forrás továbbra is sikeresen fut;
- visszaállítja a `config/.env` eredeti tartalmát;
- részletes tesztsorozat-logot ír.

Ez a script adja a projekt teljes end-to-end bizonyításának alapját: manual CSV + öt adatbázisos forrás + több `EFF_DAT` nap + újrafuttatás + hibaági landing védelem.

## Futtatás PowerShellből

PowerShell execution policy miatt szükség lehet ilyen futtatásra:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_full_extraction_test_series.ps1
```

Manual CSV tesztsorozat futtatása:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_manual_csv_test_series.ps1
```

## Kapcsolódó source scriptek

A fő Python scriptek a `src/` mappában találhatók:

```text
src/check_manual_csv_source.py
src/check_database_connections.py
src/extract_database_sources.py
```

A futtatáshoz szükséges DB-specifikus csomagok:

```text
requirements_database.txt
```

A publikus repóban a tényleges `.env` nem szerepel, ezért futtatás előtt a `config/.env.example` alapján lokálisan létre kell hozni a `config/.env` fájlt.

## Megjegyzés a Python útvonalhoz

A v2.0 labkörnyezetben a PowerShell scriptek a lokálisan használt Python telepítéshez igazodtak.

TODO: Későbbi verzióban a hardcode-olt Python útvonal helyett érdemes `PYTHON_EXE` környezeti változó override-ot használni, majd fallback-ként a `python` vagy `py` parancsot keresni a `PATH` alapján.

Ez hordozhatóbbá tenné a tesztfuttató scripteket más gépeken vagy eltérő Python-verziók mellett.
