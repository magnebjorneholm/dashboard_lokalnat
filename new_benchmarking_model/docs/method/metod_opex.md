# OPEX-variabeln i den nya TOTEX-modellen

*Status: Denna not beskriver hur vi bygger OPEX-variabeln i den nya benchmarkingmodellen,
given den information Energimarknadsinspektionen har offentliggjort fram till juni 2026. Vilka
kostnadsposter som ska ingå, och principen för deras inkludering, är myndighetens inriktning.
Urvalet av enskilda poster utöver de namngivna, hanteringen av perioder, och att i nuläget bara
nätförluster värderas till ett gemensamt pris är våra arbetsval eller följer av tillgänglig data.
De storheter som anges är betingade på detta.*

## Syfte

Syftet med denna not är att förklara hur OPEX-variabeln byggs i den nya benchmarkingmodellen,
alltså vilka löpande kostnadsposter som ingår i den gemensamma TOTEX-kostnadsvariabeln, vilka
som utesluts, och hur nätförluster värderas. Läsaren antas känna till DEA-modellen och
TOTEX-ansatsen. Vi skiljer genomgående mellan Energimarknadsinspektionens inriktning och våra
arbetsval. En avgränsning: noten behandlar konstruktionen av OPEX-variabeln. Själva
sammanslagningen av löpande kostnader och kapitalkostnad till en enda DEA-input behandlas
separat.

## TOTEX-principen: samtliga poster i en gemensam variabel

Utgångspunkten i en TOTEX-modell är att samtliga kostnadsposter ska ingå, och att de ska ingå i
en och samma kostnadsvariabel. Skälet är en mer rättvisande jämförelse. Ett nätföretag kan ha
ett mer utbyggt nät med högre kapitalkostnad men lägre kostnader för abonnemang till
överliggande nät, medan ett annat har den omvända sammansättningen. Bedöms företagen bara på en
delmängd av kostnaderna straffas eller gynnas de för sin kostnadssammansättning snarare än för
sin totala effektivitet. Genom att föra in samtliga utbytbara och påverkbara poster i en
gemensam variabel jämförs de i stället på den totala kostnaden.

Myndighetsavgifter utesluts, eftersom de varken är påverkbara eller utbytbara, utan en bestämd
summa som följer av antalet kunder och deras spänningsnivåer. De är den enda post som faller
utanför. OPEX-variabeln består därmed av de påverkbara löpande kostnaderna, värderade
nätförluster, och ett urval icke-påverkbara men utbytbara poster, minus myndighetsavgifterna.

## De påverkbara kostnaderna

De påverkbara löpande kostnaderna är en uttrycklig kostnadspost redan i dagens benchmarking. I
den nya modellen återanvänds samma påverkbara belopp som i baslinjen, så att den nya och den
nuvarande modellen utgår från exakt samma påverkbara siffra. Det gör jämförelsen mellan
modellerna direkt, eftersom en skillnad i utfall då inte kan bero på olika definitioner av den
påverkbara delen.

## Nätförluster till ett gemensamt pris

Nätförluster förs in i TOTEX. Det innebär samtidigt att det fristående incitamentet för
nätförluster tas bort, eftersom en TOTEX-modell redan ger incitament att sänka förlusterna: en
lägre förlustkostnad sänker den totala kostnaden och därmed det relativa utfallet.

I benchmarkingen värderas förlusterna till ett gemensamt pris, alltså inte till varje företags
faktiska förlustkostnad. Skälet är att den faktiska kostnaden beror på elpriset i företagets
elområde, vilket företaget inte kan påverka. Genom att värdera förlusterna till ett gemensamt
pris neutraliseras denna prisskillnad i jämförelsen. Vid tillämpningen av incitamentet görs
däremot ingen sådan justering: incitamentet utgår från de faktiska, okorrigerade
förlustkostnaderna, så att relativpriserna får genomslag i det slutliga utfallet i kronor. Det
är samma logik som korrigeringen för förläggningsmiljö, att normalisera i jämförelsen och ge
incitament på de faktiska kostnaderna.

Energimarknadsinspektionens inriktning är att värdera nätförluster, abonnemang eller båda till
ett gemensamt pris. I nuläget värderar modellen bara nätförluster på detta sätt. Det är inte ett
ställningstagande om att abonnemang inte bör korrigeras, utan en följd av att tillräckligt
detaljerad data för att göra motsvarande för abonnemang ännu saknas. En utvidgning till
abonnemang är önskvärd men förutsätter mer detaljerade uppgifter än de tillgängliga.

## De icke-påverkbara men utbytbara posterna

Utöver de påverkbara kostnaderna förs ett urval icke-påverkbara poster in. Abonnemang till
överliggande och angränsande nät är den post som inriktningen namnger uttryckligen, och den
inkluderas trots att den är svår att påverka på kort sikt, just därför att den är utbytbar mot
kapitalkostnad: ett företag som bygger eget nät i stället för att abonnera flyttar kostnad mellan
posterna, och en rättvisande jämförelse kräver att båda ingår.

Ytterligare poster förs in under det generella kriteriet att en kostnad ska vara i någon grad
utbytbar eller påverkbar för att alls ingå. Vilka dessa poster är följer av en klassificering i
datapipelinen snarare än av en uppräkning i inriktningstexten. Urvalet utöver abonnemang vilar
därmed på det generella kriteriet, inte på en specifik förteckning från myndigheten, vilket är
värt att vara tydlig med.

## Perioder och annualisering

En teknisk anmärkning om perioder. De påverkbara kostnaderna är ett indexerat medel för 2018 till
2021, medan nätförluster och de icke-påverkbara posterna är hämtade ur prognosen för 2024 till
2027. De kombineras som de är, och prognosdelarna annualiseras genom medelvärde över de fyra
åren. Detta speglar dagens modell, som på samma sätt blandar ett OPEX-medel för 2018 till 2021
med en kapitalkostnad för 2024. Att utgå från prognosperioden 2024 till 2027 i stället för den
historik som regleringen i övrigt beskriver är en pragmatisk substitution och en känd
modellförenkling.

## Arbetsspecifikation

Följande är Energimarknadsinspektionens inriktning: att samtliga kostnadsposter utom
myndighetsavgifter ska ingå i en gemensam kostnadsvariabel; att påverkbara kostnader,
nätförluster och abonnemang ingår; att nätförluster, abonnemang eller båda värderas till ett
gemensamt pris i benchmarkingen medan incitamentet utgår från de faktiska kostnaderna; och att
det fristående förlustincitamentet tas bort.

Följande är våra arbetsval eller följer av tillgänglig data, och bör läsas som sådana tills
modellspecifikationen är fastställd:

1. Urvalet av icke-påverkbara poster utöver abonnemang vilar på det generella
   utbytbarhets- och påverkbarhetskriteriet och är klassificerat i datapipelinen, inte uppräknat
   av myndigheten.
2. Att i nuläget bara värdera nätförluster, och inte abonnemang, till ett gemensamt pris följer
   av att tillräckligt detaljerad data saknas, inte av ett metodval.
3. Blandningen av perioder, ett påverkbart medel för 2018 till 2021 mot en prognos för 2024 till
   2027, och valet av prognosperiod, är kända modellförenklingar som speglar dagens modell.

## Sammanfattning

1. OPEX-variabeln samlar samtliga löpande kostnadsposter utom myndighetsavgifter i en gemensam
   kostnadsvariabel, så att företagen jämförs på total kostnad och inte på kostnadssammansättning.
2. Den består av de påverkbara kostnaderna, återanvända från baslinjen för jämförbarhet,
   värderade nätförluster, och ett urval icke-påverkbara men utbytbara poster, minus
   myndighetsavgifter.
3. Nätförluster värderas till ett gemensamt pris i benchmarkingen för att neutralisera
   elområdets prisskillnad, medan incitamentet utgår från de faktiska kostnaderna. Det
   fristående förlustincitamentet tas därmed bort.
4. Inriktningen tillåter gemensam prissättning av nätförluster, abonnemang eller båda. I nuläget
   modelleras bara nätförluster, vilket följer av en databegränsning.
5. Abonnemang är den enda icke-påverkbara post som namnges uttryckligen; övriga förs in under det
   generella utbytbarhetskriteriet och är klassificerade i datapipelinen.
6. Periodblandningen och valet av prognosperiod är kända modellförenklingar som speglar dagens
   modell.
