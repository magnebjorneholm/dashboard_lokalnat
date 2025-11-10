# Dashboard för Intäktsramsreglering av Lokalnätföretag

Interaktivt analysverktyg för decomposition och analys av intäktsramar för svenska lokalnätföretag enligt Energimarknadsinspektionens regelverk för tillsynsperioden 2024-2027.

## Systemöversikt

Detta dashboard tillhandahåller ett komplett analysverktyg för förståelse och beräkning av intäktsramar för lokalnätföretag. Systemet bygger på Energimarknadsinspektionens (Ei) metodologi och regelverket som styr hur elnätsföretag får ta betalt för distribution av el.

**Målgrupp**: Elmarknadsforskare, analytiker och myndighetspersonal som arbetar med reglering av lokalnät.

## Systemets huvudmoduler

### 1. IR-Dekomposition (Intäktsram)

Visualiserar och analyserar intäktsramens olika komponenter:

- **Kapitalkostnad**: Avkastning och avskrivningar på kapitalbas
- **Påverkbara kostnader**: Drifts- och underhållskostnader (efter effektiviseringskrav)
- **Avbrottsersättning**: Ersättning för elavbrott baserat på kvalitetsnormer
- **Intäkter från nättjänster**: Kompensation för nätrelaterade tjänster
- **Volymjustering**: Anpassning för förändringar i utmatad energi

**Interaktivt diagram**: Visar hur olika komponenter bygger upp den totala intäktsramen, med möjlighet att simulera scenarier.

### 2. Kapitalkostnad (Beräkningskedja)

Fullständig beräkning av kapitalkostnad enligt KENT-metoden:

- **Kapitalbas**: Normvärdering av nätanläggningar
- **Avskrivningar**: Årlig värdeminskning baserat på ekonomisk livslängd
- **Avkastning**: Kalkylerad avkastning på kapitalbas med WACC-metodik
- **Scenarioanalys**: Möjlighet att testa olika kalkylräntor och se påverkan

Modulen implementerar Ei:s kompletta beräkningsmetodik för kapitalkostnader.

### 3. DEA-Analys (Effektivitet)

Data Envelopment Analysis för bedömning av företags relativa effektivitet:

**Metodik**:
- Jämför företag baserat på input (CAPEX, OPEX) och output (kunder, effekt, stationer, levererad energi)
- Identifierar effektiv front och beräknar avstånd från denna
- Hanterar outliers och icke-jämförbara företag
- Stöd för både OPEX- och TOTEX-modeller

**Visualiseringar**:
- Effektivitetsfördelning för alla företag
- Geografisk analys av effektivitet
- Jämförelse mellan företag inom samma region

**Enligt Ei:s specifikation**:
- Konstant skalavkastning (CRS)
- Kostnadsminimerande ansats
- Outlier-identifiering med supereffektivitet

### 4. Effektiviseringskrav

Beräkning och tillämpning av individuella effektiviseringskrav:

- **Import från DEA**: Hämtar effektivitetsvärden från DEA-analys
- **Trunkering**: Begränsar maximalt effektiviseringskrav (standard: 30%)
- **Metodval**: OPEX (endast påverkbara kostnader) eller TOTEX (inkl. kapitalkostnad)
- **Årlig påverkan**: Beräknar reduktion av påverkbara kostnader per år

Effektiviseringskravet appliceras på påverkbara kostnader och reducerar intäktsramen.

## Regleringskontext

### Intäktsram

Intäktsramen är det maximala belopp som ett lokalnätföretag får ta ut från sina kunder under en tillsynsperiod. Den sätts på förhand av Energimarknadsinspektionen enligt principen om incitamentsreglering.

**Grundprincip**: Företag som är effektiva får behålla vinsten, ineffektiva företag måste förbättra sig eller bära kostnaden själva.

### Tillsynsperiod 2024-2027

Detta system baseras på Ei:s regelverk för nuvarande tillsynsperiod:

- **Intäktsramsförordningen (2023:1177)**: Juridisk grund
- **Beräkningsföreskrifterna (EIFS 2023:6)**: Detaljerad beräkningsmetodik
- **DEA-metodologi**: Bilaga 9 i föreskrifterna
- **KENT-metoden**: Kapitalbas- och kapitalkostnadsberäkning

## Dataflöde i systemet

```
1. Kapitalbas (KENT) → Kapitalkostnad
2. DEA-analys → Effektivitetsvärden
3. Effektivitetsvärden → Effektiviseringskrav → Påverkbara kostnader
4. Alla komponenter → Intäktsram (baseline eller scenario)
```

## Scenariohantering

Systemet stödjer scenarioanalys för:

- **Kapitalkostnad**: Olika kalkylräntor (WACC)
- **Effektiviseringskrav**: Olika trunkeringsnivåer och metoder
- **Kombinationer**: Simultana justeringar av flera komponenter

Scenarier kan sparas och laddas för jämförelse och dokumentation.

## Datakällor och referenser

**Regelverk**:
- Intäktsramsförordningen (2023:1177)
- EIFS 2023:6 - Beräkningsföreskrifter
- Ellagen (1997:857)

**Metodik**:
- DEA-metodologi: Bilaga 9, EIFS 2023:6
- KENT-metodik: Handbok kapitalbas och kapitalkostnad (Ei)
- Kvalitetsincitament: Bilaga 4-5, EIFS 2023:6

**Senast uppdaterad**: November 2025  
