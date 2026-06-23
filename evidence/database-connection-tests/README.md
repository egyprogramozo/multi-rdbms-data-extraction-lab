# Database connection test evidence

Ez a mappa az adatbázisos források connection + export view SELECT tesztjeinek válogatott bizonyítékait tartalmazza.

## Végső sikeres futások

A lezáró 5/5 sikeres checkpoint:

```text
final-5db-success/database_connection_test_20260621_075511.log
```

Ebben a futásban mind az öt adatbázisos forrás `SUCCESS_WITH_ROWS` státuszt adott `EFF_DAT=2026-06-16` értékre.

A mappában szerepel egy korábbi 5/5 sikeres futás is:

```text
final-5db-success/database_connection_test_20260621_060350.log
```

Ez támogató bizonyíték arra, hogy az 5 adatbázisos kapcsolati réteg már korábban is sikeresen lefutott; a dokumentáció elsődlegesen a későbbi `075511` logra hivatkozik.

## Diagnosztikai előzmények

A `diagnostic-history/` mappa néhány köztes kapcsolati tesztlogot tartalmaz. Ezek azt mutatják, hogyan szűkült a hiba:

- kezdetben csak egyes források voltak elérhetők;
- port / tűzfal problémák után több kapcsolat sikeressé vált;
- PostgreSQL-nél `pg_hba.conf` beállítás kellett;
- MSSQL-nél `pymssql` lett a működő út;
- IBM Db2-nél JDBC lett a működő út.

A képernyőképek és a logok válogatott diagnosztikai checkpointokat mutatnak, nem a teljes fejlesztési napló minden köztes futását.

## Publikálási döntés

A publikus repó nem tartalmaz:

- valós `.env` fájlt;
- jelszót vagy secretet;
- lokális IBM Db2 JDBC driver JAR fájlt;
- teljes adatbázis-adminisztrációs vagy tűzfalszabály-beállítási naplót.

A bizonyítékok célja annak bemutatása, hogy a kinyerő oldali connection checker végül mind az öt adatbázisos export nézetet sikeresen elérte és `EFF_DAT` szerint lekérdezte.
