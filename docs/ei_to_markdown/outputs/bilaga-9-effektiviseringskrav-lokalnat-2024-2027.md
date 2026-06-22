---
title: "Bilaga 9 – Effektiviseringskrav för lokalnätsföretag (tillsynsperioden 2024–2027)"
source_file: "DEA Bilaga-9-Effektiviseringskrav-för-elnät-lokalnät.pdf"
publisher: "Energimarknadsinspektionen (Ei)"
author: "Mattias Önnegren"
creator: "Microsoft Word"
document_date: "2024-01-18"
subject: "För tillsynsperioden 2024–2027"
pages: 24
retrieved: "2026-06-22"
language: sv
note: >
  Migrerad från Ei:s PDF (Bilaga 9) till markdown avsedd som kontext för en
  kodagent, inte för visuell läsning. All brödtext är ordagrann; avstavningar
  och PDF:ens kolumn-/sidbrytningar har lagts ihop till löpande stycken och
  sidnummer/sidfötter har tagits bort. Fotnoter återges med markdown-fotnoter
  ([^n]) och är ordagranna. Figur 1 och Figur 2 är spridda diagram (scatterplots)
  som återges som beskrivande text eftersom dokumentet är avsett att läsas av en
  AI. De fem datatabellerna (Tabell 1–5) återges som markdown-tabeller med exakt
  samma siffror som källan (svensk formatering: mellanslag som tusentalsavgränsare,
  komma som decimaltecken). Formler återges i otvetydig text-/Unicode-notation.
  På sidan 7 hade käll-PDF:en en trasig korsreferens ("Error! Reference source
  not found.") som här lösts upp till "Figur 2", vilket är den åsyftade figuren.
---

# Bilaga 9 – Effektiviseringskrav för lokalnätsföretag

**Datum:** 2024-01-18
**Avser:** Effektiviseringskrav för lokalnätsföretag, tillsynsperioden 2024–2027

## Innehåll

1. Metodik för framtagande av effektiviseringskrav
   - 1.1 Beskrivning DEA-metoden
   - 1.2 Variabler som ska ingå i produktionsmodellen
   - 1.3 Skalavkastning
   - 1.4 Rensning för ej jämförbara redovisningsenheter
2. Val av data
3. Från potential till effektiviseringskrav
4. Genomförande
   - 4.1 Exempel på beräkning enligt metoden
   - 4.2 Beräknat effektiviseringskrav för exempelföretagen
5. Uppmätta effektiviseringspotentialer med DEA-metoden

## Effektiviseringskrav för tillsynsperioden 2024–2027

Ei fastställer individuella effektiviseringskrav för lokalnätsföretagen inför tillsynsperioden 2024–2027. Detta dokument redovisar Ei:s metod för framtagande av dessa individuella krav. Länkar till rapporter med mera som refereras återfinns på Ei:s webbplats eller kan begäras hos Ei.

Elnätsföretagen utgör lokala naturliga monopol och regleras för att maximera den samhällsekonomiska effektiviteten. För att kunderna ska få del av förväntade produktivitetsökningar innefattar regleringen krav på effektiviseringar hos företagen. Att ett effektiviseringskrav ska ingå i regleringen framgår av förarbetena till ellagen (prop. 2008/09:141 s. 65 f och prop. 2017/18:237 s. 87).

För tillsynsperioden 2012–2015 fastställde Ei ett generellt effektiviseringskrav som innebar en årlig minskning av intäktsramen motsvarande en procent av de påverkbara kostnaderna.[^1] För tillsynsperioderna 2016–2019 och 2020–2023 utformades de årliga effektiviseringskraven individuellt för lokalnätsföretagen och innebar att företag som bedrev sin verksamhet mindre effektivt än andra jämförbara elnätsföretag tilldelades ett högre effektiviseringskrav. Den lägsta nivån som effektiviseringskravet kunde uppgå till var 1 procent och den högsta nivån innebar en årlig minskning med 1,82 procent av de påverkbara kostnaderna.

För att bedöma om verksamheten bedrevs effektivt utgick Ei från en modell där företag som bedrev verksamheten under likartade objektiva förutsättningar jämfördes med varandra. Eftersom modeller alltid innebär förenklingar av verkligheten genomförde Ei inför tillsynsperioden 2020–2023 analyser för att kontrollera att den valda metodiken var rimlig. Slutsatsen var att den tillämpade metodiken fångade upp skillnader i effektivitet mellan företagen på ett bra sätt och att det inte fanns något systematiskt samband mellan undersökta potentiella exogena faktorer och ett företags effektivitet.

I februari 2020 lämnade Ei in ett förslag på lagändring för att möjliggöra ett effektiviseringskrav applicerat på totala kostnader, TOTEX.[^2] Lagförslaget har inte genomförts och förutsättningarna för att fastställa elnätsföretagens effektiviseringskrav har inte förändrats sedan den föregående tillsynsperioden. Ei fastställer därför effektiviseringskraven för tillsynsperioden 2024–2027 utifrån samma metodik och utgångspunkter som för de tidigare tillsynsperioder då individuella effektiviseringskrav har tillämpats.

Sammanfattningsvis innebär metoden att Ei vid fastställandet av effektiviseringskravet har utgått från metoden Data Envelopment Analysis (DEA) som bygger på jämförelser mellan elnätsföretagens prestationer. Varje elnätsföretag får ett individuellt krav baserat på hur deras prestationer förhåller sig till de andra nätföretagen. Genom att jämföra företagen med varandra simuleras ett konkurrenstryck där företagen får incitament att minska sina kostnader i förhållande till sina konkurrenter. De effektivaste företagen tilldelas ett krav som ska reflektera branschens genomsnittliga produktivitetsutveckling, vilket innebär att de årligen ska minska sina påverkbara kostnader med en procent.[^3] De mindre effektiva företagen får ett högre individuellt krav med avsikten att de ska komma ikapp de effektiva företagen. Om ett företag ökar produktiviteten mer än det fastställda kravet får de behålla mellanskillnaden fullt ut.

Effektiviseringskravet dras av från de påverkbara kostnaderna, exklusive kostnader för flexibilitetstjänster. För tillsynsperioden 2024–2027 beräknas de påverkbara kostnaderna utifrån företagens kostnader för en historisk referensperiod, vilket för tillsynsperioden är åren 2018–2021. Effektiviseringskravet fastställs individuellt för varje elnätsföretag och innebär en minskning av företagens påverkbara kostnader för den historiska referensperioden med minst 1 procent och som mest 1,82 procent per år.

## 1 Metodik för framtagande av effektiviseringskrav

Syftet med metodiken är att ställa rimliga krav på företagen. Med metodik menas här metoden för beräkning av effektiviseringspotentialer som ligger till grund för effektiviseringskraven. Metodiken kan delas upp i två huvudsakliga delar, beräkningsmetod och modell.

Effektivitet kan bedömas på olika sätt och det finns en rad olika metoder för att beräkna effektiviseringspotentialer. Det kan ske med allt ifrån relativt enkla nyckeltal till komplexa metoder över vad som teoretiskt sett kan vara rimligt. Vid jämförelser mellan företag är ett vanligt tillvägagångsätt att använda någon form av frontmetod där effektiva företag bildar en front som utgör förebilden för de övriga företagen inom jämförelsen. I frontmetoder kan flera resurser och slutprodukter hanteras samtidigt. Genom att flera resurs- och produktionsvariabler kan inkluderas i metoden ges en mer verklighetstrogen bild av de förhållanden som finns inom en bransch. De flesta av frontmetoderna utgår från två antaganden vid skattning av effektivitet. Det första antagandet är att det är möjligt att utan kostnad öka resursåtgången eller minska produktion. Det andra antagandet är konvexitet, dvs. att kombinationer av företag kan användas för att skapa fiktiva förebilder.

Det första antagandet sätter ramarna för var det är möjligt att producera baserat på tillgängliga observationer. Baserat på en observation görs antagandet att det är möjligt att producera mindre till samma kostnad och att det är möjligt att ha den befintliga produktionen till en högre kostnad.

Antagandet om konvexitet innebär att det är möjligt att kombinera existerande enheter för att kunna skapa en fiktiv enhet som utgör ett mellanting av de kombinerade enheterna. En vanlig användning av konvexitet är att utgå från att om två företag har olika produktion[^4] så kommer en linjär kombination av dessa att vara möjlig. Det innebär att vi kan utgå från faktiska observationer av möjlig produktion och skapa en fiktiv förebild utifrån dessa. Antagandet blir av störst vikt när det endast finns få observationer.

I figur 1 nedan illustreras produktionsmöjligheterna för flera företag under båda ovan beskrivna antaganden.

### Figur 1 – Möjlig produktion givet antaganden

Diagram (scatterplot). Y-axel: Produktion (output), y. X-axel: Resursåtgång (input), x. Sex företag (1–6) är utritade som punkter. Den "effektiva fronten" ritas som en konvex, styckvis linjär kurva genom de effektiva företagen 1, 3 och 6. Området innanför fronten (det "prickiga området") markerar vad som är möjligt att producera givet det första antagandet. På x-axeln markeras två punkter för företag 2: x2 (faktisk resursåtgång) och x2* (lägre, effektiv resursåtgång), som illustrerar att företag 2 skulle kunna minska resursåtgången från x2 till x2* utan att minska sin produktion.

I figur 1 utgör företag 1, 3 och 6 effektiva företag och den effektiva fronten bildas som en konvex funktion av dessa (linjära kombinationer av dessa). Inom det prickiga området är det möjlig att producera, givet det första antagandet ovan. Baserat på urvalet av företagen innebär antagandena att inget företag kan producera någon kvantitet till en lägre kostnad än företag 1 och ingen kan producera mer än företag 6 oavsett kostnad. Det är däremot fullt möjligt att för företag 1 att öka sina kostnader eller företag 6 att minska sin produktion. För exempelvis företag 2 finns det möjligheter till effektiviseringar i förhållande till de företag som utgör fronten. Det skulle enligt de antaganden som görs vara möjligt för företag 2 att minska sin resursåtgång från x2 till x2* utan att minska sin produktion.

Det finns flera olika frontmodeller med olika egenskaper för att uppskatta effektivitet. Baserat på de förutsättningar som råder på den svenska elnätsmarknaden anser Ei att det inte finns skäl att byta från den tidigare använda DEA-metoden.

### 1.1 Beskrivning DEA-metoden

Som nämns ovan är DEA den beräkningsmetod som Ei använder för att uppskatta den effektiva fronten. Metoden gör det möjligt att skapa en modell av en verksamhet där flera olika resurser används för att producera flera olika slutprodukter.

De två antaganden som nämns ovan för frontmetoder definierar vad som bedöms som möjlig produktion enligt DEA. Konvexitet innebär att en artificiell förebild baserad på linjära kombinationer av de effektiva företagen är med och bildar den effektiva fronten. Att företag antas kunna öka kostnader och minska produktion ger en bild av vad som är möjligt att producera. Detta illustreras i figur 1. Bortsett från de två ovan nämnda antagandena behövs det för DEA-metoden endast göras antaganden om vilken skalavkastning och vilka variabler, för att bedöma resursåtgång och produktion, som ska inkluderas i modellen.

DEA-metoden är en deterministisk, icke-parametrisk beräkningsmetod. Det innebär att avvikelser från fronten betraktas helt som ineffektivitet. Icke-parametriska modeller kräver inte lika många antaganden och de befintliga observationerna definierar fronten (likt figur 1 ovan). De befintliga företagen och dess faktiska produktion definierar vad som utgör effektiv produktion vilket blir mer flexibelt och speglar branschspecifika förhållanden bra.

Nackdelen med icke-parametriska modeller är att det inte alltid är tydligt hur företagen ska förbättra sig eller vilken effekt varje variabel har på effektiviteten. Att metoden är deterministisk innebär att den inte tar hänsyn till slump, vilket ställer höga krav på insamlingen av data och att modellspecifikationen fångar upp den variation mellan företagen som inte utgörs av ineffektivitet. Metoden bygger på att all variation i data innehåller information om hur effektiva företagen är och om den underliggande teknologin, men att ingenting sker slumpmässigt. Avsaknaden av slump ställer även höga krav på identifiering av ej jämförbara företag.

Eftersom DEA-metoden är icke-parametrisk behövs inga antaganden om funktionell form eller någon fördelning på slumptermen. Uppskattningen av effektiviteten sker genom en jämförelse mellan företagens rapporterade resursåtgång och produktion. I metoden definierar företagens inrapporterade data den teknologiska nivån, som indikerar vad som är möjligt att producera med givna resurser utan att många stränga antaganden behövs. Metoden bygger inte på statistiska samband och ger därför inte heller några osäkerhetsintervall för de beräknade estimaten.

DEA-metoden innebär att det för varje observation, i detta fall elnätsföretag, formuleras ett optimeringsproblem (maximering av produktion givet existerande resursanvändning eller minimering av resursanvändningen givet faktisk produktion) där ett specifikt företag jämförs med de andra elnätsföretagen. Eftersom elnätsföretagens produktion på kort sikt styrs av kundernas efterfrågan är det naturligt att beräkna kostnadseffektiviteten genom minimering av resursåtgången givet det som producerats. Elnätsföretagens effektivitet mäts därför med en inputorienterad effektivitetsmätning. En sådan mätning utgår från att elnätsföretagen minimerar resursåtgången för att åstadkomma ett givet produktionsmål.

Metoden jämför hur nätföretag med liknande förutsättningar har lyckats prestera givet tillgängliga resurser. De nätföretag som enligt modellen är fullt effektiva är med och bildar den effektiva fronten. De effektiva företagen utgör potentiella förebilder för andra nätföretag eftersom de av olika skäl lyckats möta sin efterfrågade produktion till lägre kostnader relativt övriga företag. Avståndet mellan den effektiva fronten och företagen utgör förbättringspotentialen hos de observerade företagen.

### Figur 2 – Effektiv front

Diagram (scatterplot). Y-axel: Produktion (output), y. X-axel: Resursåtgång (input), x. Sex företag (1–6) är utritade som punkter och den effektiva fronten ritas genom de effektiva företagen. För företag 2 markeras dels den faktiska punkten 2 (vid resursåtgång x2), dels en projicerad punkt 2* (vid lägre resursåtgång x2*) på fronten, som utgör en linjär kombination av företag 1 och 3. Avståndet längs X-axeln mellan 2 och 2* är företag 2:s effektiviseringspotential.

När den bedömda effektiviteten (kostnadseffektivitet) mäts inom DEA-metoden, mäts avståndet längs X-axeln från den observerade verksamheten till den effektiva fronten. I figur 2 ovan jämförs resultatet för företag 2 med en linjär kombination av företag 1 och 3 (2*). Verksamhet 2 är relativt ineffektiv eftersom de skulle kunna minska resursåtgången till samma nivå som verksamhet 2* utan att behöva minska produktionen. Verksamhet 1, 3 och 6 räknas däremot som effektiva eftersom det inte finns något företag, eller linjära kombinationer av företag, som producerar mer. I en resursminimerande effektivitetsberäkning skulle företag 1 och 3 få ett värde på 1 eftersom de är fullt effektiva. För företag 2 skulle effektiviteten beräknas enligt följande:

> Eff₂ = x₂* / x₂,  vilket innebär att  x₂* = Eff₂ · x₂.

Där Eff₂ är kostnadseffektiviteten för företag 2, hur mycket resurser ett effektivt företag (2*) använder för att ha samma produktion som det studerade företaget (2). Ett värde på 0,9 innebär att företag 2* har samma produktion med endast 90 procent av resurserna, det finns alltså möjlighet för 2 att minska sin resursåtgång med 10 procent utan att minska sin produktion. I många fall finns inte en ren förebild med exakt samma produktion, i de fallen används en linjär kombination av effektiva företag för att skapa en artificiell förebild för företagen innanför fronten. Antagande om konstant, fallande eller variabel skalavkastning påverkar kurvan på den effektiva fronten och hur företag jämförs mot varandra. Mer information om DEA går att läsa i nedanstående referenslitteratur, från vilka den mesta informationen ovan är hämtad ifrån.[^5]

### 1.2 Variabler som ska ingå i produktionsmodellen

Vid valet av vilka variabler som ska ingå i modellen är det viktigt att utgå ifrån de egenskaper som DEA-metoden har. Eftersom metoden inte tar hänsyn till slump blir det viktigt att den valda metoden fångar upp de skillnader som finns mellan företag som inte utgörs av ineffektivitet, exempelvis kundtäthet. Eftersom en metod som baseras på kostnadsminimering används för att beräkna effektiviteten antas i modellen att produktionen är fast. Av den anledningen benämns variabler som ska förklara strukturella skillnader mellan företagen som produktionsvariabler eftersom de hanteras på samma sätt i modellen.

De parametrar som ingår som produktionsvariabler i modellen utgör en logisk beskrivning av verksamheten och är tydliga kostnadsdrivare. Det innebär att en ökning i någon av produktionsvariablerna samtidigt ger upphov till ökade kostnader för företagen. Sambandet mellan kostnader och de valda produktionsvariablerna har testats genom regressionsanalys.

En felaktig modellspecifikation kan leda till felaktiga uppskattningar av elnätsföretagens effektiviseringspotential. Om relevant information inte fångas upp i modellen kan det medföra en för låg effektivitet för vissa företag. Det finns även en risk med att för många variabler inkluderas i modellen, vilket kan resultera i att många företag blir unika och därmed bedöms som fullt effektiva.

Inför tillsynsperioden 2016–2019 tog Ei fram en metodrapport[^6] där flera olika modellspecifikationer testades. I metodrapporten föreslog Ei en modell som skulle användas vid beräkningen av effektiviseringspotentialer och modellen kom att utgöra grunden för beräkningarna av effektiviseringspotentialen. Sedan besluten med de första individuella effektiviseringskraven, 2016–2019, har överväganden gjorts rörande alternativa modeller. Utgångspunkten vid analyserna var att undersöka ifall det fanns någon modell som på ett bättre sätt kunde förklara kostnaderna som uppstår inom elnätsverksamhet. Analyserna visade att det finns en hög inbördes korrelation, både mellan de tillgängliga variablerna och gentemot kostnadsvariablerna, till exempel var korrelationen under vissa år 0,99 mellan total ledningslängd och antal nätstationer. Det är därför inte lämpligt att inkludera både ledningslängd och nätstationer i samma modell. Två potentiella nya parametrar som lyftes fram av särskilt intresse är kundtäthet och kvalitet. Ei har undersökt olika möjligheter att inkludera kvalitet i modellen och anser att det är en aspekt som kan komma att utredas vidare. För flera dimensioner gav analyserna inget entydigt svar om vilken modell som är den mest lämpliga.

För att bibehålla stabiliteten i metodiken har Ei valt att fortsätta med den modell som användes för tillsynsperioderna 2016–2019 och 2020–2023, även för tillsynsperioden 2024–2027.

Modellen består av två kostnadsvariabler som utgör resursåtgången, påverkbara kostnader (OPEXp) och kapitalkostnader (CAPEX), samt av fem produktionsvariabler; levererad energi fördelat på hög- respektive lågspänning, antal abonnemang, antal nätstationer och det högsta värdet av abonnerad och uttagen effekt mot överliggande nät.

#### 1.2.1 Variabler för att bedöma resursåtgång

I modellen ska de variabler som representerar resursåtgången (inputvariabler eller kostnadsvariabler) ingå på kostnadssidan. I intäktsramsregleringen är kostnaderna uppdelade i tre kategorier: påverkbara kostnader, opåverkbara kostnader och kapitalkostnader. Ett av effektiviseringskravets syften är att simulera ett konkurrenstryck som uppstår på en konkurrensutsatt marknad. På en konkurrensutsatt marknad skulle samtliga kostnadsposter omfattas av effektiviseringen. Ineffektivitet skulle innebära en lägre avkastning oavsett vilken typ av kostnader som gett upphov till ineffektiviteten.

Ei har klassificerat vissa kostnader som opåverkbara och dessa kostnader varierar mycket i storlek mellan företagen. Ei bedömer därför att en korrigering för dessa kostnader måste göras i modellen. Det kan göras antingen i likhet med tidigare tillsynsperioder, då de opåverkbara kostnaderna exkluderats från effektivitetsberäkningarna. Alternativt är det möjligt att korrigera för variationen inom dessa kostnader. Korrigering skulle kunna ske genom att inkludera fler variabler i modellen eller att i ett andra steg justera resultaten för dessa skillnader.

Ei har valt att bibehålla samma inputvariabler som för tillsynsperioden 2016–2019 och 2020–2023, det innebär att de opåverkbara kostnaderna exkluderas från beräkningen av företagens effektivitet. De variabler som ska användas i modellen för att mäta elnätsföretagens resurser är därmed påverkbara kostnader och kapitalkostnader enligt regleringen. För att minimera effekterna av den osäkerhet som finns gällande företagens kapitalkostnader, till följd av prognostiserade investeringar och utrangeringar, används kapitalkostnaderna endast för det första året i tillsynsperioden (2024). Det begränsar prognoserna till de investeringar och utrangeringar som förväntas genomföras 2023 och 2024H1, vilka elnätsföretagen borde ha god kännedom om. Kostnadsposterna definieras på samma sätt vid beräkning av effektiviseringspotentialen som i den övriga intäktsramsregleringen.

Från och med tillsynsperioden 2024–2027 särredovisas kostnader för flexibilitetstjänster (lagrum) vilket klassificeras som en påverkbar kostnad. Även dessa kostnader inkluderas för att bedöma resursåtgången eftersom nätföretagen bör ha ett incitament att endast välja dem i de fall det förbättrar effektiviteten i verksamheten.[^7]

#### 1.2.2 Variabler för att bedöma produktion

Produktionsvariablerna är sådana som företagen inte själva kan påverka, men som påverkar verksamhetens kostnader. Det innebär att en ökning i en produktionsvariabel medför en ökad resursåtgång på kostnadssidan. Utöver att vara kostnadsdrivande ska prestationerna dessutom ha en logisk förklaring och nivåerna ska skilja sig mellan företagen. Ur ett statistiskt perspektiv kan enskilda variabler i en regressionsanalys förklara över 90 procent av variationen i de ovan definierade kostnadsposterna. Eftersom det finns en hög inbördes korrelation mellan produktionsvariablerna finns en stor risk att samma variation förklaras av flera variabler i modellen. Det blir därför viktigt att inte inkludera för många variabler i modellen. Samtidigt måste alla exogena skillnader som inte beror på ineffektivitet fångas upp tillräckligt mycket av modellen.

Elnätsföretagens uppgift är att överföra el, vilket mäts genom mängden överförd energi till slutkund. Mängden överförd energi till slutkund är kostnadsdrivande och bestäms av kundernas efterfrågan. Kostnaderna för att leverera energi till slutkunder skiljer sig mellan högspänningskunder och lågspänningskunder. Därför inkluderas överförd energi till slutkund fördelat på lågspänning respektive högspänning i modellen. Vidare är det högsta effektuttaget dimensionerande för storleken på företagets anläggningar och därmed kostnadsdrivande. Även effektuttaget styrs av hur kunderna använder nätet och den effekt som efterfrågas. För att få fram den dimensionerande effekten används det maximala värdet av abonnerad effekt och maximalt uttagen effekt. Antalet kunder påverkar kostnaden för att överföra el, där fler kunder i normalfallet leder till högre kostnader, allt annat lika. På grund av anslutningsplikt kan företagen inte påverka vilka som får ansluta till nätet. Antalet kunder mäts i modellen genom antalet abonnemang.

De variabler som ska användas för att mäta elnätsföretagens produktion är samma som för tillsynsperioderna 2016–2019 och 2020–2023, alltså levererad energi fördelat på hög- respektive lågspänning, antal abonnemang, antal nätstationer och det högsta värdet av abonnerad och uttagen effekt mot överliggande nät.

### 1.3 Skalavkastning

Vid beräkning av effektivitetskrav med DEA-metoden används antaganden om skalavkastning. Dessa antaganden påverkar hur företagen jämförs mot varandra och vilka effektiva företag som utgör förebilder. De två vanligaste alternativen är konstant skalavkastning (CRS) och variabel skalavkastning (VRS). CRS innebär att alla företag jämförs mot varandra oavsett storlek. Att använda sig av CRS ger incitament för företagen att sträva efter en optimal storlek på företaget som minimerar kostnaderna i förhållande till produktion. VRS innebär att hänsyn tas till storleken på företagen och ger en rättvisande bild givet att företagen inte förändrar sin storlek. Eftersom regleringen är utformad för att vara neutral och ska gynna de mest kostnadseffektiva lösningarna, oavsett företagsstorlek, bör därför ett antagande om konstant skalavkastning tillämpas eftersom det inte finns något som förhindrar att företag går samman eller delar upp sig för att uppnå en effektiv storlek på företaget.

### 1.4 Rensning för ej jämförbara redovisningsenheter

En modell av företags effektiviseringspotentialer är alltid en abstraktion av verkligheten. Det innebär att det inte finns någon modell som kan fånga upp alla aspekter för alla företag. Det är därför möjligt att beräkningarna kan ge avvikelser från den verkliga potentialen. Eftersom DEA är en deterministisk metod, som inte tar hänsyn till slump, inkluderas all information vid beräkning av företagens effektivitet. Det innebär att om något företag har rapporterat in felaktiga uppgifter, eller om det saknas någon viktig variabel i modellen, kan den uppskattade effektiviteten bli missvisande. I de fall ett företag med felaktiga uppgifter är fullt effektivt och agerar som förebild för andra företag kommer det medföra en missvisande effektivitet även för andra företag. För att minska risken att företag ska få en felaktigt bedömd effektivitet exkluderar Ei ej jämförbara redovisningsenheter. Dessa utgörs av observationer vars mönster utifrån modellens uppbyggnad inte stämmer överens med övriga observationer och som inte är typiska för resterande data. Det innebär att företag med avvikande kostnadsdata eller produktion exkluderas från effektivitetsberäkningarna.

Metodiken för att identifiera vilka företag som ej är jämförbara med de övriga ska fånga upp skillnader som finns mellan företagen som modellen inte tar hänsyn till och som inte utgörs av skillnader i effektivitet. När ett ej jämförbart företag identifieras exkluderas det från urvalet av data och effektivitetsberäkningarna genomförs på nytt. De företag som klassas som "ej jämförbara" tilldelas det lägsta effektiviseringskravet eftersom de inte har några andra företag att jämföras mot. Inför tillsynsperioden 2024–2027 är tre av de ingående 148 företagen så pass avvikande enligt DEA-modellen att de betraktas som ej jämförbara och exkluderas ur modellen (se Tabell 5).

Det finns många metoder för att identifiera ej jämförbara enheter. De flesta av dessa utgår dock från rent statistiska antaganden och går därför inte att tillämpa inom DEA-metoden eftersom den är icke-parametrisk. De två vanligaste testerna som används inom DEA-metoden är "dominance test" och det så kallade testet för supereffektivitet (super efficiency test). Det första testet innebär att en observation ska bedömas som ej jämförbar om den agerar som förebild för väldigt många andra enheter och att den genomsnittliga effektiviteten påverkas markant. Testet tenderar dock att endast fånga upp ett fåtal ej jämförbara enheter. Det andra testet (för supereffektivitet) bygger på en jämförelse av relativ effektivitet mellan enheter som erhållit en effektivitet på 1. En observation blir klassad som ej jämförbar om den överstiger ett på förhand satt kritiskt värde. En av utmaningarna med testet är att sätta ett så korrekt kritiskt värde som möjligt. Testet har i flera akademiska rapporter[^8] visat sig fungera bra för att identifiera ej jämförbara enheter. En viktig aspekt att beakta är att testet bör genomföras upprepade gånger. Det gör att om det är fler än en enhet med avvikande men liknande produktion så kommer testet att kunna fånga upp även dessa.

Ei har för tillsynsperioderna 2016–2019 och 2020–2023 använt testet för supereffektivitet upprepade gånger för att identifiera ej jämförbara enheter. Ei finner inte någon anledning till att förändra vare sig metoden eller nivån på det tidigare använda intervallet. Kriteriet för att ett företag ska klassas som ej jämförbart är följande:

> Eff_i > q(75) + 2 · [q(75) − q(25)]

där:

- **Eff_i** = mättalet på effektivitet för företag *i* som erhålls genom körningar med supereffektivitet.
- **q(75)** = effektiviteten i den tredje kvartilen för alla företag.
- **q(25)** = effektiviteten i den första kvartilen för alla företag.

En observation ska alltså betraktas som ej jämförbar mot de övriga om mättalet för effektivitet överstiger summan av den tredje kvartilen och skillnaden mellan den första och tredje kvartilen multiplicerat med 2.

## 2 Val av data

Eftersom DEA-metoden utgår från en deterministisk ansats som inte tillåter slumpmässighet innebär det att modellen blir känslig för felaktigheter i data. Det är därför viktigt att det inte förekommer några felaktigheter vid datainsamling av underlaget.

Av förarbetena till ellagen framgår att nätmyndigheten vid utarbetande av modeller för effektivisering ska ta hänsyn till de enskilda nätföretagens objektiva förutsättningar, till exempel kundtätheten i ett koncessionsområde och nätets ålder. Eftersom intäktsramen ska bestämmas i förväg får myndigheten ta fram en kostnadsnorm med hjälp av historiska data (prop. 2017/18:237 s. 87).

För produktionsdata, påverkbara kostnader och strukturella faktorer har data från företagens årsrapporter 2018–2021 använts. För att undvika att vissa år ska få för stort genomslag i beräkningarna har medelvärdet av posterna för de fyra åren använts. Underlaget från årsrapporterna för de påverkbara kostnaderna har kompletterats med inrapporteringen av löpande kostnader som ligger till grund för intäktsramarna. Kapitalkostnaderna har beräknats med utgångspunkt från den kapitalbas som företagen har rapporterat inför tillsynsperioden 2024–2027. Beräkningen av kapitalkostnader görs i 2022 års prisnivå med beaktande av anläggningarnas ålder 2024 samt investeringar och utrangeringar för 2023 och 2024. Vid beräkning av kapitalkostnaderna har en kalkylränta på 4,53 procent använts för samtliga redovisningsenheter. Beräkningen av både de påverkbara kostnaderna och kapitalkostnaderna görs enligt samma principer som vid beräkningen av företagens intäktsramar.

För sammanslagningar, samredovisning och uppköp har historiken i största möjliga utsträckning vägts samman mellan företagen där kostnader och produktion summeras för redovisningsenheterna.

Det dataunderlag som använts är det som var känt för Ei den 15 januari 2024. Ändringar som företagen rapporterat in efter detta datum har därför inte ingått vid beräkningarna.

## 3 Från potential till effektiviseringskrav

I DEA-metoden beräknas elnätsföretagens långsiktiga potential för effektiviseringar. Effektiviseringspotentialen anger hur mycket kostnaderna skulle kunna minskas, givet samma produktion, för att företaget ska vara lika effektivt som de fullt effektiva företagen (enligt DEA-modellen). Denna potential måste översättas till ett krav för den fyraåriga tillsynsperioden. Den framtagna DEA-metoden innehåller vissa förenklade antaganden. Det är nödvändigt för att kunna konstruera en modell som ska beskriva och analysera en komplex verksamhet som överföring av el. Det framgår även av ellagens förarbeten att det ur ett administrativt perspektiv och för att göra regleringen någorlunda enkel får accepteras att nätföretagen inom en grupp avviker från varandra. Det ligger också i regleringens natur att vissa förenklingar och schabloniseringar måste tillåtas (prop 2008/09:141 s. 65).

Eftersom det är elnätsföretagens långsiktiga effektiviseringspotential som uppskattas i metodiken innebär det att det kommer ta tid att realisera möjliga effektiviseringar. Det är därför inte rimligt att kräva att företagen ska realisera hela den beräknade potentialen under en tillsynsperiod på fyra år. Samtidigt skulle alla former av ineffektivitet medföra en lägre avkastning på en konkurrensutsatt marknad. Med hänsyn till att det inte bara är löpande kostnader som ligger till grund för beräkningarna anser Ei att det är rimligt att elnätsföretagen får två tillsynsperioder, åtta år, på sig att genomföra effektiviseringar. Effektivisering inom påverkbara löpande kostnader kan förväntas realiseras under en tillsynsperiod, medan anläggningarna i kapitalbasen har en duration[^9] på cirka 12 år och motiverar därför en längre realiseringstid. Kravet på effektiviseringar för företagen bestäms därför som mättalet på kostnadseffektivitet från beräkningen i den valda modellen multiplicerat med en realiseringsfaktor på 50 procent.[^10]

För att företagen ska ha incitament att effektivisera sin verksamhet delas den förväntade realiseringen lika mellan kunderna och elnätsföretagen. Det innebär att hälften av den potential som ska realiseras under tillsynsperioden kommer att utgöra grunden för effektiviseringskravet.

För att beakta att DEA-metoden innehåller ett visst mått av förenkling är det rimligt att tillämpa en högsta nivå för kraven på effektiviseringar. Den högsta nivån ska begränsas till vad som är möjligt för företagen att åtgärda inom den angivna realiseringstiden. Utifrån uppmätta effektiviseringspotentialer för tidigare tillsynsperioder (2016–2019 och 2020–2023) samt även 2024–2027 är det tydligt att effektiviteten, i förhållande till de fullt effektiva företagen, är relativt jämnt fördelad inom spannet 70 till 100 procent. Det är knappt tio företag som har en effektivitet under 70 procent, vilket motsvarar en effektiviseringspotential på mer än 30 procent. Då dessa avviker från den jämna fördelningen, och därmed indikerar att modellen eventuellt inte är fullt tillämplig för dem, bedöms 30 procent som en rimlig högsta nivå, det vill säga ett tak för effektiviseringspotentialen.

För tillsynsperioden 2012–2015 fastställde Ei ett generellt effektiviseringskrav som innebar en reduktion med en procent per år av de påverkbara kostnaderna. Samtliga företag omfattades av detta effektiviseringskrav. Kravet grundade sig på en bedömning som visade att en produktivitetsutveckling på två procent per år var en rimlig förväntan. Bedömningen gjordes utifrån egna analyser och andra relevanta produktivitetsanalyser och redogörs för i rapporten Förhandsregleringens krav på effektiviseringar (Ei R2010:11). För att skapa incitament för företagen att rationalisera verksamheten delades hälften av den förväntade produktivitetsökningen med kunderna, vilket alltså motsvarar ett effektiviseringskrav på en procent per år. Från och med tillsynsperioden 2016–2019 beräknas dessutom ett individuellt krav, utöver en procent, såsom har beskrivits i denna PM, för att spegla den effektiviseringspotential som uppmätts med hjälp av DEA-modellen. För de företag som beräknats effektiva och de som inte är jämförbara (enligt avsnitt 1.4) är det rimligt att likt för de tidigare tillsynsperioderna tillämpa en lägstanivå på effektiviseringskravet på en procent per år, eftersom detta kan anses motsvara den genomsnittliga produktivitetsökningen inom branschen.

Med de valda begränsningarna som beskrivs ovan uppgår effektiviseringskravet som högst till 7,5 procent (motsvarande ett årligt krav på högst 1,82 procent), på de påverkbara kostnaderna för tillsynsperioden 2024–2027. Som lägst uppgår effektiviseringskravet till 1 procent årligen av de påverkbara kostnaderna.

## 4 Genomförande

Givet den angivna metoden beräknas i ett första steg effektiviseringspotentialen. Det kan göras med hjälp av en rad olika statistikprogram, exempelvis i "R" där det finns ett stort antal paket[^11] för att beräkna effektiviseringspotentialer. Oavsett vilken programvara som används för att göra beräkningarna för effektiviseringspotentialen är det viktigt att specificera att det ska vara en kostnadsminimerande ansats (input efficiency), det ska vara konstant skalavkastning (CRS) och det ska gå att korrigera för så kallade supereffektiva företag. Baserat på den framräknade effektiviseringspotentialen genomförs en analys av ej jämförbara företag och dessa exkluderas från dataunderlaget. När det inte längre förekommer några ej jämförbara företag fastställs effektiviseringspotentialen för de olika redovisningsenheterna. Denna potential omvandlas sedan baserat på ovan beskrivna filtreringar till ett effektiviseringskrav som innebär en årlig minskning av intäktsramen med 1 till 1,82 procent av de påverkbara kostnaderna.

### 4.1 Exempel på beräkning enligt metoden

Nedan kommer en stegvis genomgång av genomförandet vid framtagande av effektiviseringskraven att beskrivas. I exemplet redovisas beräkningarna för ett datamaterial baserat på data inför tillsynsperioden 2020–2023 från 20 elnätsföretag. Dataunderlaget presenteras i Tabell 1 nedan. I tabellen utgör de två första variablerna resursåtgången som består av kostnadsvariablerna påverkbara kostnader (OPEXp) och kapitalkostnader (CAPEX). De fem efterkommande variablerna utgörs av produktionsvariablerna: antal abonnemang (Abonnemang), antal nätstationer (Nätstationer), levererad energi lågspänning (EnergiLS), levererad energi högspänning (EnergiHS) samt det högsta värdet av abonnerad och uttagen effekt från överliggande nät (Effekt). Vid jämförelser när samtliga redovisningsenheter inkluderas kommer resultaten att skilja sig från de som presenteras i exemplet nedan.

#### Tabell 1 – Dataexempel till beräkningar

Resursåtgång = OPEXp, CAPEX. Produktionsvariabler = Abonnemang, Effekt, Nätstationer, EnergiLS, EnergiHS.

| Företags-ID | OPEXp (tkr) | CAPEX (tkr) | Abonnemang (st) | Effekt (MW) | Nätstationer (st) | EnergiLS (MWh) | EnergiHS (MWh) |
|---|---|---|---|---|---|---|---|
| 1 | 23 661,91 | 28 683,92 | 14 379,00 | 52,25 | 226,75 | 170 996,25 | 40 930,00 |
| 2 | 11 666,43 | 11 429,44 | 3 996,00 | 20,00 | 191,50 | 50 340,50 | 31 635,50 |
| 3 | 14 348,04 | 10 064,55 | 3 150,00 | 27,25 | 126,25 | 41 222,00 | 68 656,75 |
| 4 | 4 295,98 | 4 906,12 | 1 944,25 | 6,25 | 123,50 | 23 881,50 | 0,00 |
| 5 | 37 516,03 | 43 505,47 | 13 740,75 | 70,00 | 583,50 | 192 965,25 | 63 318,75 |
| 6 | 44 871,94 | 42 771,08 | 19 630,50 | 89,00 | 207,25 | 243 229,50 | 116 949,50 |
| 7 | 39 510,40 | 59 622,00 | 34 379,50 | 119,50 | 374,00 | 366 010,75 | 180 591,00 |
| 8 | 21 972,75 | 29 706,37 | 10 645,50 | 43,75 | 284,00 | 143 140,50 | 40 931,50 |
| 9 | 12 411,44 | 8 077,79 | 2 428,75 | 9,00 | 173,75 | 27 174,00 | 1 078,50 |
| 10 | 50 783,87 | 50 901,45 | 27 621,75 | 137,75 | 306,75 | 423 928,75 | 78 686,00 |
| 11 | 10 389,53 | 14 761,79 | 9 552,50 | 38,00 | 98,75 | 104 749,50 | 52 154,75 |
| 12 | 15 754,55 | 13 280,33 | 7 319,50 | 36,00 | 162,75 | 93 941,75 | 69 594,00 |
| 13 | 6 759,92 | 7 811,64 | 3 522,25 | 14,25 | 71,75 | 46 056,00 | 10 814,25 |
| 14 | 12 085,16 | 15 674,52 | 7 154,50 | 37,25 | 188,00 | 126 620,25 | 13 170,50 |
| 15 | 523,46 | 531,18 | 284,50 | 1,25 | 15,00 | 2 404,75 | 0,00 |
| 16 | 13 707,92 | 12 180,66 | 5 488,75 | 18,25 | 157,25 | 63 769,75 | 1 715,00 |
| 17 | 4 808,76 | 3 083,02 | 1 499,75 | 5,00 | 70,25 | 16 654,75 | 0,00 |
| 18 | 2 991,63 | 3 557,82 | 594,75 | 10,00 | 30,00 | 26 325,75 | 619,75 |
| 19 | 48 601,97 | 44 246,03 | 21 141,75 | 76,25 | 573,50 | 234 906,50 | 94 359,50 |
| 20 | 34 974,36 | 33 753,79 | 21 903,50 | 85,75 | 196,50 | 265 466,75 | 139 325,00 |

Baserat på den information som finns i Tabell 1 formuleras ett optimeringsproblem. Optimeringen går ut på att minimera kostnader för en given nivå på produktionen. Att konstant skalavkastning används innebär att alla företag jämförs mot varandra. De som har den lägsta nivån på kostnader i förhållande till sin produktion kommer att falla ut som effektiva i modellen. I Tabell 2 nedan presenteras de resultat på effektivitet som kommer från beräkningarna. I tabellen visas även de resultat som kommer från beräkningar baserade på supereffektivitet, för att kunna identifiera om det finns ej jämförbara observationer med i dataunderlaget.

#### Tabell 2 – Kostnadseffektivitet och ej jämförbara observationer

| FTG ID | Effektivitet | Beräknad supereffektivitet |
|---|---|---|
| 1 | 83 % | 83 % |
| 2 | 95 % | 95 % |
| 3 | 100 % | 130 % |
| 4 | 100 % | 106 % |
| 5 | 77 % | 77 % |
| 6 | 78 % | 78 % |
| 7 | 95 % | 95 % |
| 8 | 75 % | 75 % |
| 9 | 77 % | 77 % |
| 10 | 100 % | 106 % |
| 11 | 100 % | 122 % |
| 12 | 100 % | 114 % |
| 13 | 80 % | 80 % |
| 14 | 100 % | 118 % |
| 15 | 100 % | 135 % |
| 16 | 80 % | 80 % |
| 17 | 97 % | 97 % |
| 18 | 100 % | 107 % |
| 19 | 82 % | 82 % |
| 20 | 100 % | 108 % |

Som beskrivs tidigare i bilagan ska en observation betraktas som ej jämförbar mot de övriga om: mättalet för effektivitet överstiger summan av den tredje kvartilen och skillnaden mellan den första och tredje kvartilen multiplicerat med två. I exemplet ovan blir en redovisningsenhet klassad som ej jämförbar om:

> Eff_i > q(75) + 2 · [q(75) − q(25)],  där  q(75) = 1  och  q(25) = 0,80

Det medför i sin tur att observationer med en beräknad supereffektivitet på över 139 procent (Eff_i > 1 + 2·[1 − 0,8]) ska tas bort från dataunderlaget vid fastställande av fronten. Dessa företag tilldelas det lägsta effektiviseringskravet eftersom de inte har några som de kan jämföras emot. Baserat på det gränsvärde vi fått fram kan vi se att inga av de inkluderade redovisningsenheterna får ett värde högre än gränsvärdet.

Efter att rensning för ej jämförbara enheter är klar erhålls den effektivitet som ligger till grund för effektiviseringskraven. Den slutliga effektiviseringspotentialen erhålls genom att ta 1 minus mättalet på effektivitet för varje observation. Det beskriver avståndet till effektiv produktion. De slutliga mättalen på effektivitet och effektiviseringspotentialen samt vilka enheter som utgör förebilder presenteras i Tabell 3 nedan.

#### Tabell 3 – Mättal för effektivitet, förebilder och effektiviseringspotential

| FTG ID | Effektivitet | Förebilder (FTG ID) | Effektiviseringspotential |
|---|---|---|---|
| 1 | 83 % | 11, 14, 15 och 20 | 17 % |
| 2 | 95 % | 3, 11 och 15 | 5 % |
| 3 | 100 % | – | 0 % |
| 4 | 100 % | – | 0 % |
| 5 | 77 % | 4, 11, 12 och 15 | 23 % |
| 6 | 78 % | 10, 11 och 12 | 22 % |
| 7 | 95 % | 11 och 15 | 5 % |
| 8 | 75 % | 4, 11 och 14 | 25 % |
| 9 | 77 % | 3 och 15 | 23 % |
| 10 | 100 % | – | 0 % |
| 11 | 100 % | – | 0 % |
| 12 | 100 % | – | 0 % |
| 13 | 80 % | 11, 14, 15 och 20 | 20 % |
| 14 | 100 % | – | 0 % |
| 15 | 100 % | – | 0 % |
| 16 | 80 % | 14, 15 och 20 | 20 % |
| 17 | 97 % | 14 och 15 | 3 % |
| 18 | 100 % | – | 0 % |
| 19 | 82 % | 12, 14, 15 och 20 | 18 % |
| 20 | 100 % | – | 0 % |

Totalt är 9 av de 20 utvalda företagen klassificerade som fullt effektiva och utgör möjliga förebilder för de 11 övriga företag som inte blir klassificerade som fullt effektiva. För att illustrera beräkningarna från effektiviseringspotential till slutliga effektiviseringskrav kommer företaget med nummer 13 i tabell 3 att användas. Företaget uppmäter i exemplet en effektivitet på 80 procent. Det innebär att det skulle vara möjligt att möta samma produktion till 80 procent av de nuvarande kostnaderna genom att ställa om till en effektivare produktion. För företag 13 finns fyra förebilder, 11, 14, 15 och 20. Dessa innehåller information om hur företaget kan förbättra sig. Bland förebilderna är tre större (företag 11, 14 och 20) och ett mindre (15) företag sett till antal kunder. Företag 13 har en något högre kostnad per abonnemang än dess förebilder. De har även en något högre kostnad per levererad megawattimme än tre av förebilderna (företag 11, 14 och 20). Den högre kostnaden i förhållande till produktion som företag 13 har jämfört med sina förebilder gör att de inte blir klassade som fullt effektiva.

### 4.2 Beräknat effektiviseringskrav för exempelföretagen

Eftersom inget av företagen har en potential som överstiger 30 procent, behöver ingen korrigering för en undre gräns genomföras för exempelföretagen. Skulle något företag ha en potential på över 30 procent skulle den korrigeras till det angivna gränsvärdet.

I nästa steg multipliceras potentialen med realiseringsfaktorn 0,5 för att få fram den potential som ska realiseras inom en tillsynsperiod. För företag 13 skulle detta innebära att de under den kommande tillsynsperioden ska realisera en effektiviseringspotential på 10 procent (20 % · 0,5). För att skapa incitament för företagen får de behålla hälften av effektiviseringen, vilket innebär att den kvarvarande effektiviseringspotentialen halveras. Det ger ett effektiviseringskrav för tillsynsperioden på 5 procent. För att omvandla kravet för hela tillsynsperioden om fyra år till ett årligt avdrag används det geometriska medelvärdet för en fyraårsperiod.

> (1 + 0,05)^(1/4) − 1 ≈ 0,0123 = 1,23 %

Det framräknade kravet skulle alltså innebära ett årligt effektiviseringskrav på 1,23 procent för företag nummer 13, vilket motsvarar en effektivisering på 5 procent under en fyraårsperiod. Eftersom kravet överstiger det lägsta möjliga kravet på 1 procent ska det framräknade kravet gälla. För företag 13 innebär det att de påverkbara kostnaderna reduceras enligt Tabell 4 nedan.

#### Tabell 4 – Beräkning av effektiviseringskrav

| Post | År 1 | År 2 | År 3 | År 4 | Total |
|---|---|---|---|---|---|
| Påverkbara kostnader innan avdrag för effektiviseringskrav | 6 760 | 6 760 | 6 760 | 6 760 | 27 040 |
| Effektiviseringskrav % | 1,23 % | 2,47 % | 3,73 % | 5 % | |
| Effektiviseringskrav tkr | 83 | 167 | 252 | 338 | 840 |
| Påverkbara kostnader efter avdrag för effektiviseringskrav | 6 677 | 6 593 | 6 508 | 6 422 | 26 200 |

I tabellen framgår att företag 13 under den kommande fyraårsperioden ska minska sina påverkbara kostnader med 5 procent jämfört med sina historiska kostnader. Det totala effektiviseringskravet för fyraårsperioden uppgår till 840 tkr eftersom de årliga kraven på effektiviseringar ackumuleras i takt med att effektiviseringspotentialen realiseras.

## 5 Uppmätta effektiviseringspotentialer med DEA-metoden

Nedan redovisas effektiviseringspotentialen för samtliga redovisningsenheter. Siffrorna avser potentialer uppmätta med DEA-metoden, alltså före de justeringar som beskrivs i avsnittet "Från potential till effektiviseringskrav". I tabellen nedan är potentialen avrundad till hela procenttal. I besluten sker avrundning först vid de slutliga effektiviseringskraven.

#### Tabell 5 – Elnätsföretagens effektiviseringspotential

Asterisk (`*`) efter potentialen markerar att företaget är exkluderat från dataunderlaget på grund av att det är ett ej jämförbart företag.

| ReID | Företagsnamn | Potential (ojusterad) |
|---|---|---|
| REL00018 | AB Borlänge Energi Elnät | 1 % |
| REL03046 | PiteEnergi Elnät AB | 2 % |
| REL00091 | Affärsverken Elnät i Karlskrona AB | 30 % |
| REL00001 | Ale El ek. för. | 32 % |
| REL03049 | Alingsås Energi Elnät AB | 25 % |
| REL00003 | Almnäs Bruk AB | 0 % |
| REL00004 | Alvesta Elnät AB | 29 % |
| REL00005 | Arvika Teknik AB | 23 % |
| REL00007 | Bengtsfors Energi Nät AB | 29 % |
| REL00008 | Bergs Tingslags Elektriska AB | 34 % |
| REL03048 | Bjäre Kraft Elnät AB | 27 % |
| REL00011 | Bjärke Energi ek. för. | 38 % |
| REL00014 | Blåsjön Nät AB | 13 % |
| REL00015 | Bodens Energi Nät AB | 0 % |
| REL00016 | Boo Energi ek. för. | 0 % |
| REL00017 | Borgholm Energi Elnät AB | 23 % |
| REL00019 | Borås Elnät AB | 2 % |
| REL01012 | Brittedals Elnät ek. för. | 23 % |
| REL00021 | Bromölla Energi och Vatten AB | 16 % |
| REL00023 | C4 Elnät AB | 0 % |
| REL00024 | Carlfors Bruk E Björklund & Co KB | 0 %* |
| REL03009 | Dala Energi Elnät AB | 22 % |
| REL03054 | Degerfors Elnät AB | 15 % |
| REL03028 | E.ON Energidistribution AB | 0 % |
| REL00030 | Eksjö Elnät AB | 0 % |
| REL03035 | Ellevio AB | 2 % |
| REL00031 | Emmaboda Elnät AB | 11 % |
| REL00035 | Eskilstuna Energi och Miljö Elnät AB | 0 % |
| REL00037 | Falbygdens Energi Nät AB | 31 % |
| REL00038 | Falkenberg Energi AB | 8 % |
| REL03015 | Falu Elnät AB | 20 % |
| REL00040 | Filipstad Energinät AB | 33 % |
| REL00043 | Gislaved Energi Elnät AB | 0 % |
| REL00945 | Gotlands Elnät AB | 19 % |
| REL00049 | Grästorps Energi ek. för. | 8 % |
| REL03057 | Gävle Energi Elnät AB | 10 % |
| REL00062 | Göteborg Energi Nät AB | 0 % |
| REL00585 | Götene Elförening ek. för. | 8 % |
| REL00064 | Habo Kraft AB | 29 % |
| REL00067 | Hallstaviks Elverk ek. för. | 0 % |
| REL00033 | Halmstads Energi och Miljö Nät AB | 0 % |
| REL00938 | Hedemora Elnät AB | 29 % |
| REL00072 | Herrljunga Elektriska AB | 3 % |
| REL03041 | Hjo Elnät AB | 18 % |
| REL00074 | Hjärtums Elförening ek. för. | 16 % |
| REL00075 | Hofors Elverk AB | 8 % |
| REL00576 | Härjeåns Nät AB | 18 % |
| REL00077 | Härnösand Elnät AB | 24 % |
| REL00078 | Härryda Energi AB | 39 % |
| REL00080 | Höganäs Energi AB | 14 % |
| REL00083 | Jukkasjärvi Sockens Belysningsförening u.p.a. | 25 % |
| REL00085 | Jämtkraft Elnät AB | 32 % |
| REL00086 | Jönköping Energinät AB | 5 % |
| REL00087 | Kalmar Energi Elnät AB | 3 % |
| REL03043 | Karlsborgs Elnät AB | 22 % |
| REL03047 | Karlshamn Elnät AB | 4 % |
| REL00090 | Karlskoga Elnät AB | 22 % |
| REL00092 | Karlstads El- och Stadsnät AB | 13 % |
| REL00886 | Kraftringen Nät AB | 21 % |
| REL00098 | Kristinehamns Elnät AB | 29 % |
| REL00100 | Kungälv Energi AB | 18 % |
| REL00899 | Kvänumbygdens Energi ek. för. | 0 % |
| REL00121 | LEVA i Lysekil AB | 12 % |
| REL00590 | LKAB Nät AB | 29 % |
| REL00103 | Landskrona Energi AB | 0 % |
| REL00106 | Lerum Energi AB | 20 % |
| REL03038 | Lidköping Elnät AB | 4 % |
| REL00944 | Linde Energi AB | 1 % |
| REL00112 | Ljungby Energinät AB | 0 % |
| REL00113 | Ljusdal Elnät AB | 22 % |
| REL00118 | Luleå Energi Elnät AB | 10 % |
| REL00123 | Malung-Sälens Elnät AB | 22 % |
| REL00126 | Mellersta Skånes Kraft ek. för. | 32 % |
| REL00127 | Mjölby Kraftnät AB | 31 % |
| REL00267 | Mälarenergi Elnät AB | 12 % |
| REL00128 | Mölndal Energi Nät AB | 0 % |
| REL00130 | Nacka Energi AB | 30 % |
| REL00182 | Njudung Energi Sävsjö AB | 7 % |
| REL00936 | Njudung Vetlanda Elnät AB | 10 % |
| REL00133 | Norrtälje Energi AB | 16 % |
| REL00135 | Nossebroortens Energi ek. för. | 6 % |
| REL00137 | Nybro Elnät AB | 13 % |
| REL00139 | Näckåns Elnät AB | 22 % |
| REL03050 | Näckåns Elnät AB (tidigare Viggafors Elektriska andelsförening UPA) | 0 % |
| REL00141 | Nässjö Affärsverk Elnät AB | 0 % |
| REL00143 | Olofströms Kraft Nät AB | 0 % |
| REL00144 | Olseröds Elektriska Distributionsförening u.p.a. | 31 % |
| REL00146 | Oskarshamn Energi Nät AB | 3 % |
| REL00147 | Oxelö Energi AB | 0 % |
| REL00148 | Partille Energi Nät AB | 19 % |
| REL00152 | Ronneby Miljö och Teknik AB | 29 % |
| REL00156 | Rödeby Elverk ek. för. | 33 % |
| REL00160 | SEVAB Nät AB | 25 % |
| REL00157 | Sala-Heby Energi Elnät AB | 5 % |
| REL00158 | Sandhult-Sandared Elektriska ek. för. | 0 % |
| REL01010 | Sandviken Energi Elnät AB | 21 % |
| REL00163 | Sjogerstads Elektriska Distributionsförening ek.för. | 28 % |
| REL00164 | Sjöbo Elnät AB | 21 % |
| REL03042 | Skara Elnät AB | 0 % |
| REL00824 | Skellefteå Kraft Elnät AB | 0 % |
| REL00167 | Skurups Elverk AB | 1 % |
| REL00168 | Skyllbergs Bruks AB | 13 % |
| REL00169 | Skånska Energi Nät AB | 6 % |
| REL00170 | Skövde Energi Elnät AB | 0 % |
| REL00171 | Smedjebacken Energi Nät AB | 8 % |
| REL00173 | Sollentuna Energi och Miljö AB | 2 % |
| REL00175 | Staffanstorps Energi AB | 22 % |
| REL00177 | Sturefors Eldistribution AB | 11 % |
| REL00178 | Sundsvall Elnät AB | 21 % |
| REL00183 | Söderhamn Elnät AB | 18 % |
| REL00184 | Södra Hallands Kraft ek. för. | 24 % |
| REL00185 | Sölvesborgs Energi & Vatten AB | 19 % |
| REL00965 | Sörbylunds Elnät HB | 0 %* |
| REL00093 | Tekniska verken Katrineholm Nät AB | 2 % |
| REL00111 | Tekniska verken Linköping Nät AB | 0 % |
| REL00186 | Telge Nät AB | 0 % |
| REL00187 | Tibro Elnät AB | 12 % |
| REL00332 | Tidaholms Elnät AB | 32 % |
| REL00937 | Tranås Energi Elnät AB | 28 % |
| REL03019 | Trelleborgs Elnät AB | 30 % |
| REL00191 | Trollhättan Energi Elnät AB | 0 % |
| REL00193 | Töre Energi ek. för. | 42 % |
| REL00195 | Uddevalla Energi Elnät AB | 7 % |
| REL03044 | Ulricehamn Energi Elnät AB | 18 % |
| REL00584 | Umeå Energi Elnät AB | 20 % |
| REL00012 | Upplands Energi ek. för. | 24 % |
| REL03016 | Vaggeryds Elverk AB | 0 % |
| REL00201 | Vallebygdens Energi ek. för. | 0 % |
| REL00203 | Vara Energi ek. för. | 14 % |
| REL00204 | Varberg Energi AB | 13 % |
| REL00205 | Varbergsortens Elkraft ek. för. | 29 % |
| REL03030 | Vattenfall Eldistribution AB | 6 % |
| REL00958 | Vimmerby Energi Nät AB | 24 % |
| REL00594 | VänerEnergi AB | 16 % |
| REL00235 | Värnamo Elnät AB | 9 % |
| REL00570 | Västerbergslagens Elnät AB | 6 % |
| REL00239 | Västerviks Kraft-Elnät AB | 6 % |
| REL00242 | Västra Orusts Energitjänst ek. för. | 27 % |
| REL00243 | Växjö Energi Elnät AB | 17 % |
| REL03056 | Ystad Energi Elnät AB | 21 % |
| REL00246 | Ålem Energi AB | 27 % |
| REL00249 | Årsunda Kraft & Belysningsförening ek. för. | 15 % |
| REL00959 | Åsele Elnät AB | 0 % |
| REL00904 | Öresundskraft AB | 16 % |
| REL00364 | Österlens Kraft AB | 20 % |
| REL00255 | Östra Kinds Elkraft ek. för. | 0 % |
| REL00029 | Övertorneå Energi AB | 1 % |
| REL00257 | Övik Energi Nät AB | 0 %* |

*) Exkluderad från dataunderlaget på grund av ej jämförbart företag.

## Fotnoter

[^1]: Kravet gällde ej för de företag som enbart hade prognostiserade kostnader.

[^2]: Ei PM2020:01.

[^3]: Ei R2010:11, Förhandsregleringens krav på effektiviseringar.

[^4]: Det kan vara olika produktion och/eller olika insatsvaror, exempelvis ett större och ett relativt mindre företag.

[^5]: An introduction to Efficiency and Productivity Analysis. Av: T. J. Coelli, D. S. P. Rao, C. J. O'Donnell, och G. E. Battese. – Benchmarking with DEA, SFA, and R. Av: P. Bogetoft, och L. Otto. – Data Envelopment Analysis: A Handbook on the Modeling of internal Structures and Networks. Av: W. D. Cook, och J. Zhu.

[^6]: Metodik för bestämning av effektiviseringskrav i intäktsramsregleringen för elnätsföretag REMISS.

[^7]: Däremot tillämpas inte effektiviseringskravet på kostnaderna för flexibilitetstjänster eftersom Ei bedömt att nätföretagen bör få kostnadstäckning för dessa under innevarande tillsynsperiod istället för utifrån den historiska referensperioden.

[^8]: Exempelvis: Banker, R. D., & Chang, H. (2006). The super-efficiency procedure for outlier identification, not for ranking efficient units. European Journal of Operations Research, 175, 1311–1320. Eller: Wilson, P. (1995). Detecting influential observations in data envelopment analysis. Journal of Productivity Analysis, 6, 27–45.

[^9]: Med duration i detta avseende menas den nuvärdesvägda, genomsnittliga löptiden på kassaflödena från investeringen.

[^10]: Fyra år (en tillsynsperiod) dividerat med åtta år (realiseringstid).

[^11]: Exempel på paket i R: Benchmarking, FEAR, rDEA, Frontier.
