# Ei:s DEA-metod (exakt procedur)

Den metod/procedur som replikerar Ei:s publicerade resultat i `data/ei/EIs_DEA.xlsx`
till maskinprecision (~5·10⁻⁹), med undantag för en enda firma (REL00193, se sista
avsnittet). Beskrivningen är **data-agnostisk**: den gäller godtycklig uppsättning DMU:er
med inputvektorer och outputvektorer, oberoende av vilka kolumner eller värden som används.

## Grundbyggsten: input-orienterad supereffektivitet (leave-one-out, CRS)

För en DMU `i` som scoras mot en referensmängd `R` löses följande LP. CRS betyder att
ingen konvexitets-/summationsrestriktion på λ läggs till.

```
min   θ
λ, θ
s.t.  Σ_{j ∈ R, j ≠ i}  λ_j · y_jk  ≥  y_ik        för varje output k
      Σ_{j ∈ R, j ≠ i}  λ_j · x_jl  ≤  θ · x_il     för varje input l
      λ_j ≥ 0,  θ ≥ 0
```

Det avgörande är `j ≠ i`: DMU:n utesluts ur sin egen referens, vilket tillåter `θ > 1`
(supereffektivitet) för firmor på fronten. Ingen kolumnskalning/normalisering tillämpas
på input eller output. Saknad data (NaN) eller olösbart LP behandlas som "ingen poäng"
och hanteras som outlier i steget nedan.

## Steg 1: Outlieridentifiering via itererad IQR-fence

Outliers identifieras genom att upprepa supereffektivitet + IQR-grind tills inget nytt
flaggas. Detta är den punkt där den exakta replikeringen står och faller: ett enda varv
räcker inte, det måste itereras till konvergens.

```
R ← alla DMU:er
loop:
    1. Beräkna supereffektivitetspoäng θ_j för alla j ∈ R
       (var och en scoras leave-one-out mot resten av R).
    2. Bilda IQR-grinden enbart på de finita poängen i R:
           Q1   = percentil_25(θ over R)
           Q3   = percentil_75(θ over R)
           fence = Q3 + 2.0 · (Q3 − Q1)
    3. Flagga varje j ∈ R med θ_j > fence  ELLER  icke-finit θ_j
       som outlier, och ta bort den ur R permanent.
    4. Om inget nytt flaggades detta varv: bryt.
```

Iterationen är nödvändig eftersom en extrem outlier (mycket hög θ) blåser upp Q3 och IQR
så att grinden i första varvet är för slapp för att fånga måttligare outliers. När den
extrema firman tas bort krymper grinden och nästa firma fångas. Ei:s publicerade resultat
motsvarar denna iterering, inte ett enstaka identifieringsvarv.

Parametrar i grinden: `q_lower = 25`, `q_upper = 75`, `multiplier = 2.0`. Grinden är
ensidig (endast övre svans), eftersom outliers per definition är onaturligt
supereffektiva.

## Steg 2: Slutlig poängsättning mot rensad referensmängd

När `R` har konvergerat (alla outliers borttagna):

- **Överlevande firmor** scoras en sista gång med supereffektivitets-LP:t mot den rensade
  `R`. Resultatet θ ger:
  - effektivitet `E = min(θ, 1)`
  - supereffektivitet `= θ` (kan vara > 1 för frontfirmor)
  - potential `= 1 − E`
- **Outliers** exkluderas ur fronten och lämnas **opoängsatta** (ingen publicerad
  effektivitet). De får inte en poäng mot fulla setet, eftersom det bara skulle spegla
  just de anomalier som ledde till uteslutningen. De tilldelas istället ett schablonmässigt
  effektivitetskrav (i facit `Effkrav_proc = 0.01`).

## Invarianter som måste hålla för exakt replikering

1. Input-orienterad, **CRS** (ingen λ-summationsrestriktion).
2. **Supereffektivitet** (leave-one-out, `j ≠ i`) används i *både* outliersteget och den
   slutliga poängen.
3. **Ingen** normalisering/skalning av input/output.
4. IQR-grind: ensidig övre, `Q3 + 2·IQR`, beräknad på 25/75-percentiler av
   referensmängdens poäng.
5. Outlierdetektionen **itereras till konvergens**, inte ett enda varv.
6. Outliers tas bort ur referensfronten och lämnas opoängsatta; överlevare scoras mot den
   rensade fronten med `E = min(θ,1)`, `potential = 1 − E`.

## Undantaget: REL00193

Följs de sex punkterna ovan reproduceras Ei:s effektivitet och supereffektivitet till
solvertolerans (~5·10⁻⁹) för samtliga firmor utom REL00193. Dess facitvärde (0.5829) är
lägre än vad någon referensmängd ger på den publicerade datan (rensad front: 0.7571;
fulla setet inklusive outliers: 0.6608). Eftersom det är lägre än till och med
fulla-set-poängen kan det inte uppstå ur något val av referensmängd, utan pekar på en
dataavvikelse i just den raden snarare än i metoden.

## Inputkravet: rå `OPEXp`, inte SDF-controllable

Exakt replikering kräver att DEA:n körs på den **råa** kostnadskolumnen `OPEXp` i
`data/ei/Data_modeller.xlsx`. Det är den input Ei körde på.

Appens pipeline använder medvetet en **annan** input: i `data_loaders/baseline_data.py`
byts `OPEXp` mot en SDF-härledd `controllable_cost_average`. De två sammanfaller för
endast 92 av 148 firmor; för resten avviker SDF-värdet upp till ~16.5 % (medel ~2.4 %).
Den skillnaden propagerar in i DEA:n:

- effektiviteten ändras för ~109 firmor, varav ~65 skiftar mer än 1 procentenhet
  (max-skift ~0.23),
- outliersettet ändras (3 → 5).

Slutsats: pipelinens baseline-DEA är därför **inte** en exakt replikering av
`EIs_DEA.xlsx`, utan en omkörning av samma metod på reviderad (SDF-)kostnadsbas. Vill man
reproducera Ei:s publicerade facit ska rå `OPEXp` användas; vill man ha appens baseline
ska den SDF-härledda `controllable_cost_average` användas. Metoden (de sex invarianterna
ovan) är identisk i båda fallen, det är bara kostnadsinputen som skiljer.
