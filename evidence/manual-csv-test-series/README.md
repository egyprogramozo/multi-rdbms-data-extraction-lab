# Manual CSV tesztbizonyítékok

Ez a mappa a manual CSV kinyerő ág futási bizonyítékait tartalmazza.

## Lezáró manual CSV tesztsorozat

A Codex által futtatott lezáró local file-drop tesztsorozat itt található:

```text
codex-local-filedrop-test-series/
```

Tartalom:

```text
manual_csv_test_series_20260621_030249.log
extraction-logs/
sample-landing-outputs/
sample-success-empty-output/
```

A tesztsorozat eredménye: **8 teszt futott, 8 a várt státuszt adta**.

A fő tesztsorozat-log tartalmazza a T01–T08 esetek teljes bontását, ezért ez az elsődleges bizonyíték a lezáró manual CSV tesztsorozat eredményére.

Megjegyzés: a lezáró futás logjaiban még a korábbi lokális munkamappanevek szerepelnek (`qlite_filepost_csv`, `qlite_filepost_csv_baseline`). A publikus repóban ezek beszédesebb néven jelennek meg (`manual_csv_filedrop`, `manual_csv_filedrop_baseline`). A szerepük ugyanaz: working input mappa és baseline visszaállítási mappa.

## Korábbi validációs bizonyítékok

A `logs/` almappa a korábbi kézi PowerShell validációk logjait tartalmazza. Ezek segítettek a hibaágak és az UNC megosztásos működés ellenőrzésében.

A gyökérszintű `sample-landing-outputs/` és `sample-success-empty-output/` mappák korábbi validációs mintakimeneteket tartalmaznak. A lezáró Codex tesztsorozat saját mintakimenetei a `codex-local-filedrop-test-series/` almappán belül találhatók.
