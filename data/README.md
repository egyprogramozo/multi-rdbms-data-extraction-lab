# data

Ez a mappa a futási kimenetek helye.

A projekt két fő runtime output területet használ:

```text
data/staging/
data/landing/
```

A `staging` mappa az ideiglenes írási terület. A kinyerő folyamat először ide írja az új CSV állományokat.

A `landing` mappa a végleges, frissített kimeneti terület. Egy meglévő landing fájl csak akkor cserélődik, ha az adott forrás új kinyerése sikeresen lefutott.

A safe replace logika szempontjából fontos, hogy ha a staging fájl írása közben hiba történik, például betelik a lemez, akkor a landing csere nem fut le, ezért a korábbi landing fájl megmarad. Ilyenkor részleges staging fájl maradhat vissza, ezért production környezetben a runtime adatkönyvtárat érdemes külön adatlemezen, megfelelő szabad hely figyeléssel és karbantartással kezelni, hogy a kimeneti fájlok növekedése ne veszélyeztesse az operációs rendszer működését.

A generált runtime CSV fájlok szándékosan nem részei a publikus repónak. A mappaszerkezetet `.gitkeep` fájlok őrzik meg, míg a tesztelt mintakimenetek és futási logok az `evidence/` mappában találhatók.

Megjegyzés: a projekt jelenlegi verziója CSV landing kimeneteket használ, mert ez egyszerűen ellenőrizhető és jól olvasható portfólió-lab környezetben. Későbbi fejlesztési irányként érdemes lehet oszlopalapú, sémát is megőrző fájlformátumok, például Apache Parquet vizsgálata is. Ez modern Data Lake / Lakehouse környezetek felé természetes továbbfejlesztési lépés lehet.
