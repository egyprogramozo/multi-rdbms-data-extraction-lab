# Full extraction test series evidence

Ez a mappa a v2.0 teljes kinyerési tesztsorozat bizonyítékait tartalmazza.

## Fő log

```text
logs/full_extraction_test_series_20260621_075529.log
```

A lezáró log eredménye:

```text
restored_config_env=True
final_status=PASS
```

Ez a dokumentáció elsődleges hivatkozási alapja.

A mappában szerepel egy korábbi sikeres full extraction futás is:

```text
logs/full_extraction_test_series_20260621_064404.log
```

Ez támogató bizonyíték, de a lezáró állapotot a későbbi `075529` log dokumentálja.

## Tesztelt EFF_DAT értékek

```text
2026-06-16
2026-06-17
2026-06-18
2026-06-19
2026-06-20
```

## Ellenőrzött működés

A tesztsorozat ellenőrizte:

- manual CSV extraction futását minden napra;
- database extraction futását minden napra;
- 5/5 adatbázisos landing CSV meglétét;
- újrafuttatást `2026-06-16` napra;
- MySQL hibaszimulációt rossz porttal;
- hibás MySQL futásnál a korábbi landing fájl védelmét;
- a többi DB forrás sikeres továbbfutását;
- a `config/.env` visszaállítását.

## Log almappák

```text
logs/manual/
logs/database/
```

Ezek a teljes tesztsorozat közben keletkezett reprezentatív futási logokat tartalmazzák.

## Mintakimenetek

```text
sample-landing-outputs/
```

A mappa napokra bontva tartalmazza a tesztelt landing CSV-ket:

```text
2026-06-16/
2026-06-17/
2026-06-18/
2026-06-19/
2026-06-20/
```

Minden naphoz tartozik:

- egy manual CSV landing kimenet;
- öt adatbázisos landing CSV kimenet a `database_sources/` mappában.

A mintakimenetek a lezáró loggal összhangban naponta eltérő sorszámokat tartalmaznak. Például `2026-06-20` napra a manual CSV output 10 sort, az adatbázisos források pedig forrásonként 8 sort tartalmaznak.

Megjegyzés: az adatbázis-driverek dátumformázása eltérhet. Oracle esetén az `EFF_DAT` mező `YYYY-MM-DD 00:00:00` formában jelenhet meg, míg más forrásoknál `YYYY-MM-DD` formában. Ez formátumbeli eltérés.

## Smoke test megjegyzés

A fő log egy külön kicsomagolt repómappából futtatott ellenőrzést is dokumentál. A futás igazolja, hogy helyi `.env` és lokális Db2 JDBC driver beállítása után a repó friss kicsomagolásból is működőképes.

A logban látható `RepoSmokeTest` és `multi-rdbms-data-extraction-lab-v2.0.1` lokális mappanevek tesztelési útvonalak, nem publikus release-verziók.

## Publikálási döntés

A publikus repó nem tartalmazza a runtime `data/` mappát teljes egészében. Ehelyett ez az evidence mappa válogatott, napokra bontott landing output mintákat és futási logokat tartalmaz a többnapos tesztsorozat bizonyítására.
