# EFF_DAT alapú kinyerési logika

## Cél

A projekt `EFF_DAT` alapú, kézzel vezérelt kinyerést mutat be. A cél nem egy teljes production-grade scheduler vagy backfill keretrendszer, hanem egy kontrolláltan tesztelhető adatkinyerési lépés több különböző forrásból.

Az `EFF_DAT` értékét normál működésben a felhasználó állítja a `config/.env` fájlban. A v2.0 tesztsorozat ugyanakkor ideiglenesen több dátumra is módosította ezt az értéket, majd a futás végén visszaállította az eredeti konfigurációt.

## EFF_DAT jelentése

Az `EFF_DAT` azt az üzleti / feldolgozási napot jelöli, amelyre a forrásadatokat ki kell nyerni.

Példa:

```env
EFF_DAT=2026-06-16
```

A kinyerő logika minden forrásnál ehhez igazodik:

- manual CSV esetén az adott napi orders fájlt keresi;
- adatbázisos források esetén az export nézetet szűri `EFF_DAT` szerint.

## Manual CSV forrás

Manual CSV forrásnál az EFF_DAT szerinti orders fájlnak léteznie kell.

Példa:

```text
site06_orders_manual_export_2026-06-16.csv
```

Ha az EFF_DAT szerinti orders fájl hiányzik, az hiba.

Ha a fájl létezik, de csak fejlécet tartalmaz, az nem hiba, hanem `SUCCESS_EMPTY`.

Ha a fájlban vannak sorok, a kinyerő ág ellenőrzi:

- a szükséges oszlopok meglétét;
- az `eff_dat`, `order_date` és `last_update_at` mezők értelmezhetőségét;
- az orders fájlban szereplő `eff_dat` értékek egyezését az aktuális `EFF_DAT` értékkel;
- hogy a legnagyobb `order_date` nem későbbi, mint a kiválasztott customer snapshot fájldátuma;
- hogy az orders fájlban szereplő `customer_id` értékek megtalálhatók a customer snapshotban.

Fontos: az `order_date` nem köteles megegyezni az `EFF_DAT` értékkel. Egy korábbi rendelés későbbi exportnapon is megjelenhet, ha időközben státuszt váltott.

## Státusztörténet kezelése

A manual CSV forrás az adott `EFF_DAT` napra ismert rendelési eseményeket és állapotváltozásokat adja át. Ez nem feltétlenül csak az aznap létrejött új rendeléseket jelenti.

Ezért egy rendelés több `EFF_DAT` fájlban is megjelenhet:

```text
2026-06-16: order_id=2, status=NEW
2026-06-17: order_id=2, status=PAID
2026-06-18: order_id=2, status=SHIPPED
```

A kinyerő folyamat ezt nem végállapotként értelmezi, hanem átadja a downstream / adattárházi rétegnek. Ott lehet eldönteni, hogy aktuális állapotot vagy teljes státusztörténetet kell építeni.

## Adatbázisos források

Adatbázisos forrásoknál minden RDBMS saját export nézettel rendelkezik. A v2.0 adatbázisos kinyerő script ugyanazt a logikát alkalmazza mind az öt forrásra:

- TCP host/port ellenőrzés;
- driver / modul ellenőrzés;
- adatbázis-kapcsolódás;
- `EFF_DAT` szerinti lekérdezés;
- CSV írás staging mappába;
- sikeres futás esetén landing csere;
- hiba esetén meglévő landing fájl érintetlenül hagyása.

A script minden forrást külön kezel. Egy forrás hibája nem állítja meg a többi forrás sikeres kinyerését.

## Staging → landing biztonságos csere

A projekt safe replace logikát használ.

Sikeres futás esetén:

```text
data/staging/{EFF_DAT}/...
        ↓
data/landing/{EFF_DAT}/...
```

Ha a landing fájl még nem létezett:

```text
CREATED_NEW_FILE
```

Ha már létezett, és az új kinyerés sikeres:

```text
REPLACED_EXISTING_FILE
```

Ha a forrás hibára fut, de volt korábbi landing fájl:

```text
LEFT_EXISTING_FILE_UNCHANGED
```

Ha a forrás hibára fut, és nem volt korábbi landing fájl:

```text
NO_OUTPUT_CREATED
```

## Staging-kezelési megjegyzés

A DB extractor és a manual CSV ág ugyanazt a fő safe replace célt követi: csak sikeres kinyerés után frissülhet a landing output, hiba esetén pedig a meglévő landing fájl érintetlen marad.

A staging mappa kezelése a v2.0 állapotban technikailag nem teljesen azonos a két ágban:

- az adatbázisos extractor esetén a staging fájl a landing fájl frissítése után is megmarad;
- a manual CSV ágban az `os.replace()` a staging fájlt mozgatja át a landing helyére, ezért sikeres futás után a staging mappában nem marad ugyanaz a kimeneti fájl.

Ez a különbség a landing-védelem lényegét nem érinti, de a staging mappa utólagos ellenőrizhetősége szempontjából fontos technikai eltérés.

TODO: Későbbi verzióban érdemes a DB és manual CSV ág staging-kezelését egységesíteni, például úgy, hogy a manual CSV ág is megőrizze a staging kimenetet a landing frissítése mellett.

## v2.0 tesztsorozat

A teljes tesztsorozat ezekre a napokra futott:

```text
2026-06-16
2026-06-17
2026-06-18
2026-06-19
2026-06-20
```

Minden napra lefutott:

- manual CSV extraction;
- database extraction;
- landing mappák és database CSV-k meglétének ellenőrzése.

Külön tesztelt esetek:

- ugyanazon `EFF_DAT` nap újrafuttatása;
- MySQL port-hiba szimulációja;
- hibás MySQL futás esetén a korábbi landing fájl védelme;
- annak ellenőrzése, hogy MySQL hiba közben a többi DB forrás továbbra is sikeresen fut.

A lezáró állapot:

```text
final_status=PASS
```

## Tudatos korlát

A v2.0 nem automatikus többnapos éles feldolgozó keretrendszer. A többnapos futtatást a tesztharness végezte kontrollált validációs céllal. Normál működésben az `EFF_DAT` kézi beállítás alapján futtatható.
