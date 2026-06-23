# data

Ez a mappa a futási kimenetek helye.

A projekt két fő runtime output területet használ:

```text
data/staging/
data/landing/
```

A `staging` mappa az ideiglenes írási terület. A kinyerő folyamat először ide írja az új CSV állományokat.

A `landing` mappa a végleges, frissített kimeneti terület. Egy meglévő landing fájl csak akkor cserélődik, ha az adott forrás új kinyerése sikeresen lefutott.

A generált runtime CSV fájlok szándékosan nem részei a publikus repónak. A mappaszerkezetet `.gitkeep` fájlok őrzik meg, míg a tesztelt mintakimenetek és futási logok az `evidence/` mappában találhatók.
