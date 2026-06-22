# Read-only export hozzáférés

## Cél

A projekt adatbázisos forrásaihoz a kinyerő folyamat nem adminisztratív vagy fejlesztői jogosultsággal kapcsolódik, hanem korlátozott read-only export felhasználóval.

A cél az volt, hogy a kinyerő oldali komponens csak azt lássa, amit a forrásoldal publikálni akar: egy dedikált, kontrollált export nézetet.

## Export user

A laborban használt export user neve:

```text
codexexp
```

A publikus repóban jelszó, valós `.env` vagy lokális secret nem szerepel.

A `codexexp` név a lab egyszerűsítése érdekében minden adatbázismotornál azonos szerepet jelöl: egy dedikált, csak olvasásra használt export felhasználót.

## Konfigurációs egyszerűsítés

A kinyerő oldali konfigurációban a közös `DB_USERNAME` / `DB_PASSWORD` változónév lab-egyszerűsítés, nem production credential-kezelési ajánlás.

A jogosultsági modell ettől még forrásonként least-privilege szemléletű: minden adatbázisban dedikált read-only export user kap hozzáférést, kizárólag a kontrollált export nézet lekérdezéséhez.

Valós környezetben ez motoronként és forrásonként külön hitelesítést, secret-kezelést, hozzáférés-rotációt és környezetspecifikus jogosultságbeállítást kapna.

## Jogosultsági modell

A célmodell:

```text
CONNECT / LOGIN jog
SELECT jog a v_daily_orders_export nézetre
nincs közvetlen SELECT jog az alaptáblákra
nincs INSERT / UPDATE / DELETE jog
nincs CREATE / ALTER / DROP jog
nincs admin jog
```

Ez a modell azt mutatja, hogy az export folyamat nem teljes adatbázis-hozzáférést kap, hanem csak a publikált adatátadási interfészt éri el.

## Miért export nézeten keresztül?

Az export nézet több szempontból hasznos:

- elrejti az alaptáblák részleteit;
- stabil interfészt ad a kinyerő folyamatnak;
- korlátozza a kinyerhető adatmezőket;
- egyszerűbbé teszi a jogosultságkezelést;
- közelebb áll egy vállalati adatátadási gyakorlathoz.

## Ellenőrzött működés

A forrásoldali tesztek során a nézetek kézi lekérdezése működött, majd a connection checker mind az öt adatbázisos forrásnál sikeresen lekérdezte a `v_daily_orders_export` nézetet `EFF_DAT=2026-06-16` szűréssel.

A v2.0 adatkinyerési script ugyanennek a read-only export hozzáférésnek a használatával már CSV landing kimeneteket is előállított mind az öt adatbázisból.

Az SQL Server környezetben külön ellenőrzés történt arra is, hogy az alaptábla közvetlen lekérdezése tiltott legyen a korlátozott felhasználó számára. Ez a viselkedés megfelel a tervezett minimális jogosultsági modellnek.

## DB2 sajátosság

Az IBM Db2 Docker konténerben futott, ezért a lokális felhasználó- és jogosultságkezelés technikai háttere eltért a többi adatbázistól.

A Db2 esetében a kapcsolódó felhasználói háttér a konténer környezetében lett kezelve, majd a Db2 adatbázisban külön grant készült az export nézetre. A kinyerő oldali Python script végül JDBC-n keresztül kapcsolódott.

A publikus repóban nem cél a teljes lokális Db2 Docker-jogosultsági hibakeresés részletes dokumentálása. A projekt szempontjából a lényeg az, hogy a read-only export hozzáférés működőképes lett, és a kinyerő folyamat nem admin jogosultsággal futott.

## Publikálási döntés

A repóba nem kerülnek be:

- jelszavak;
- lokális `.env` fájl;
- teljes lokális grant scriptek valós adatokkal;
- Db2 JDBC driver JAR;
- lokális adminisztrációs vagy gépspecifikus beállítások.

A repóban a működési bizonyítékok és a kinyerő oldali logika szerepelnek.
