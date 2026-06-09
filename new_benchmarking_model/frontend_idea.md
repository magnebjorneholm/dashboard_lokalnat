# Idéer/punkter
1. I nuläget möts användaren av konfiguration direkt och det är för mycket grejer att ändra. Jag föreslår att användaren ser följande när hen kommer in:
    - Kort, saklig information om ändringarna som görs i modellen
    - Eftersom det är så mycket som "kan" ändras (trots att Ei har en i princip fastställd modell) bör vi ha resultat för en "main new benchmarking model" (vi bestämmer exakta specs ihop för denna) som vi jämför visuellt med övergripande och utforskande statistik för alla företag (övergripande effekter) samt effekter på det enskilda företaget.
    - Endast om användaren vill "experimentera" så ska det finnas möjlighet att ändra på spec för "main benchmarking model" (från ovan) och detta ska bara va finjusteringar.
    - "Finjusteringarna" är i princip nuvarande parameterval för "Konfiguration"

2. Visuellisering av "konfiguration"
    - I nuläget delas det upp i tre kategorier (Nätförluster, Förläggningsmiljö (capex), Outputs) på första raden och sen TOTEX-komponenter längre ned. Detta känns felaktigt eftersom det "delar upp för mycket som är i praktiken väldigt lite", man ska kunna ändra...
        - Gemensamt pris för nätförlustkostnad
        - "Metod kabel och station" med mycket tydligare förklaring hur varje metod gör justeringen
        - Vilka ledningstyper som inkluderas i variabeln "ledningslängder" (ledningslängder ska alltid va med i outputs tillsammans med de fem föregående NS, MW, MWhh, MWhl, CU)
    - Detta är allt man ska ändra i nuläget. Gör hellre en sak bra än flera dåligt.
    - Om man kör ny spec med finjustering ska bara visualiseringarna beskrivna i "1" ändras


3. Visualisering
    - Vad har vi att jämföra? (1) Ei's äldre benchmarking modell, (2) Ei's nya benchmarking modell (vår main spec), (3) användarens finjustering
    3a. Sektor-headline (överst)
        - KPI-rad: median/medel Δ krav, antal företag med höjt krav, antal med sänkt, antal oförändrade/outliers.
        - Histogram över Δ krav och (pp), med ditt företags läge utmarkerat (vertikal markör). Färgdelning vid 0 — men obs: höjt krav = sämre för företaget, så vi måste vara medvetna om delta-konventionen (inte automatiskt "grönt = positivt").
        - Histogram över effektivitet med antal och andel inom respektive trunkeringszon
    3b. Utforskande
        - Scatter: Δ krav (y) mot en valbar strukturvariabel (x): kundtäthet (kunder per km ledning), storlek (CU), förläggningsmiljö-exponering (env_capex reduction-factor), ledningslängd. Ditt företag highlightat.