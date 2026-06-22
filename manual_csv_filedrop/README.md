# manual_csv_filedrop

Ez a mappa a manual CSV / file-drop forrás **working input** területe.

A `src/check_manual_csv_source.py` ellenőrző és kinyerő script innen olvassa be az aktuális manual CSV forrásfájlokat az `EFF_DAT` alapján. A mappa célja azt modellezni, amikor egy régi vagy manuális rendszer kontrollált CSV állományokat ad át a kinyerő folyamatnak.

A tesztek ezt a mappát módosíthatják: fájlokat törölhetnek, átírhatnak vagy visszaállíthatnak hibakezelési esetek ellenőrzéséhez. A tiszta kiinduló állapot a `manual_csv_filedrop_baseline` mappából állítható vissza.
