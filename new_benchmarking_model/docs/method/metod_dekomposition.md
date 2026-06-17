# Att dela upp ett benchmarkingutfall i dess beståndsdelar

## Syfte

Syftet med denna not är att förklara hur den förändring i det årliga
effektiviseringskravet som följer av Energimarknadsinspektionens omarbetade
benchmarkingmodell kan delas upp i de enskilda komponenter som modellen bygger på.
Läsaren antas känna till modellens beståndsdelar: DEA-skattningen, justeringen av
kapitalbasen för förläggningsmiljö, hanteringen av icke påverkbara kostnader och
nätförluster, samt ledningslängd som utfallsmått. Däremot förutsätts inte att läsaren
känner till hur varje komponents bidrag kan isoleras. Vi beskriver här enbart metoden.
De substantiella resultaten redovisas i en separat del.

Den centrala svårigheten kan formuleras kort. Vi vill kunna säga hur stor del av kravet
som beror på var och en av komponenterna, på ett sätt som summerar exakt till helheten.
Den uppenbara vägen, att slå av en komponent i taget och avläsa skillnaden, ger inte ett
sådant svar. Resten av noten förklarar varför, och vilken metod som gör det.

## Varför komponenterna inte kan subtraheras var för sig

Skälet ligger i att DEA-skattningen är relativ. Effektiviteten mäts mot en front av de
mest effektiva bolagen, och referensnivån E75 bestäms som en percentil i samma
fördelning. När en kostnadspost förs in i modellen förskjuts både det enskilda bolagets
position och fronten, vilket ändrar utfallet för samtliga bolag samtidigt. En komponents
effekt är därför inte ett fast tal. Den beror på vilka övriga komponenter som redan ingår.

Konsekvensen är att en komponents marginaleffekt skiljer sig åt beroende på i vilken
ordning komponenterna betraktas. Ett konkret exempel illustrerar storleksordningen.
Ledningslängd som utfallsmått förskjuter medianbolagets krav med omkring 0,02
procentenheter per år (absolutbelopp) när måttet förs in sist, i en modell där övriga
komponenter redan ingår, men med omkring 0,13 procentenheter per år när det förs in
först, i den bara baslinjen. Det är samma komponent och samma data. Det enda som skiljer
är kontexten.

De två talen är ändpunkterna för komponentens effekt. Vi benämner dem leave-one-out
(komponenten tas bort ur den fullständiga modellen) respektive add-one-in (komponenten
läggs till den bara baslinjen). Gapet mellan dem är inte ett mätfel, utan en upplysning:
det mäter hur starkt komponenten samverkar med de övriga. För ledningslängd är gapet stort
relativt komponentens egen storlek, vilket innebär att dess värde är starkt
ordningsberoende. För icke påverkbara kostnader är gapet litet, vilket innebär att den
komponentens effekt är nära oberoende av kontexten.

Eftersom DEA är icke-linjär summerar dessa marginaleffekter inte till den totala
förändringen. Om man adderar leave-one-out-bidragen för de fyra komponenterna missar man
den faktiska totalen med i median omkring 0,13 procentenheter per år, och för enskilda
bolag pekar summan till och med åt fel håll. En additiv uppdelning kräver därför en metod
som hanterar ordningsberoendet uttryckligen, inte en enskild av-och-på-jämförelse.

## Shapley-värdet: genomsnittet över alla ordningar

Shapley-värdet, hämtat från den kooperativa spelteorin, löser ordningsberoendet genom att
inte välja någon enskild ordning. Varje komponents bidrag beräknas som dess marginaleffekt
genomsnittad över samtliga ordningar i vilka komponenterna kan läggas till modellen. Med
fyra komponenter finns det 24 sådana ordningar, motsvarande 16 delmängder av komponenter,
och varje delmängd kräver en egen DEA-körning.

Formellt tilldelas komponent *k* bidraget

> φ_k = Σ_S  w(|S|) · [ v(S ∪ {k}) − v(S) ],   där   w(s) = s! (n−s−1)! / n!
>
> Summan löper över alla delmängder S av de övriga komponenterna. v(S) är bolagets
> signerade årskrav (i procentenheter) när endast komponenterna i S ingår, och n är
> antalet komponenter. Vikten w(s) är andelen av alla ordningar i vilka komponent k läggs
> till just efter komponenterna i S.

Det avgörande är inte formeln i sig, utan att denna genomsnittsbildning är den enda
uppdelning som uppfyller fyra egenskaper samtidigt. Var och en av dem är rimlig att kräva
av en rättvis fördelning, och tillsammans bestämmer de uppdelningen entydigt:

1. Bidragen summerar exakt till den totala förändringen, inte ungefär. I vår tillämpning
   håller denna identitet till maskinprecision för varje bolag.
2. En komponent som aldrig påverkar utfallet, oavsett kontext, tilldelas exakt noll.
3. Två komponenter som är utbytbara tilldelas lika stora bidrag.
4. Bidragen är additiva: om modellen delas i två oberoende delar är en komponents bidrag i
   helheten summan av dess bidrag i delarna.

För ledningslängd i exemplet ovan placerar sig Shapley-bidraget mellan de två
ändpunkterna, omkring 0,07 procentenheter per år vid medianen. Det är den
ordningsoberoende sammanvägningen av de kontexter där komponenten har liten respektive
stor effekt. På detta sätt försonar Shapley-värdet leave-one-out och add-one-in i ett enda
tal som ändå adderar korrekt.

## Den nästlade strukturen: vad som räknas som en komponent

Den nya modellen skiljer sig från den nuvarande på fler sätt än vilka kostnader som ingår.
Två förändringar är av ett annat slag: övergången från den tidigare front-referensen till
den tvåsidiga E75, och övergången från två separata DEA-inputs till en sammanslagen
TOTEX-input. Dessa bestämmer *hur kravet beräknas*, snarare än *vilka kostnader* som ingår
i det. Att behandla dem som vilka komponenter som helst i samma spel vore missvisande.

Vi delar därför upp förändringen i två skikt. Det yttre skiktet attribuerar steget från
Energimarknadsinspektionens publicerade krav till den nya modellens baslinje, och fördelar
det mellan de två beräkningsmässiga förändringarna med ett eget tvåkomponents-Shapley. Det
inre skiktet attribuerar därefter kravet mellan de fyra kostnadskomponenterna, givet den
nya beräkningsregimen. Båda skikten är exakta Shapley-spel, och tillsammans summerar de
exakt till hela förändringen från det publicerade kravet till det nya utfallet.

Valet att hålla de beräkningsmässiga förändringarna i ett separat yttre skikt är medvetet,
och det är värt att motivera, eftersom det är just den punkt en granskande analytiker har
skäl att pröva. Alternativet vore ett enda spel med samtliga förändringar som likställda
komponenter. Ett sådant spel skulle attribuera varje kostnadskomponents bidrag delvis i
kontexter som använder den övergivna front-referensen, det vill säga en beräkningsregim som
inte längre tillämpas. Den storhet vi vill redovisa är kostnadskomponenternas fördelning av
kravet *i den modell som faktiskt gäller*, vilket är precis vad det inre skiktet ger. Den
nästlade strukturen är därmed inte en förenkling vi tvingats till, utan den konditionering
som frågan kräver.

## Hur bidragen ska tolkas

Tre förbehåll bör åtfölja varje läsning av bidragen.

För det första, och viktigast: eftersom DEA är relativ är bidragen fördelningsmässiga, inte
absoluta. Att flytta en komponent förskjuter fronten och E75, vilket innebär att ett bidrag
som sänker ett bolags krav i regel motsvaras av en höjning hos andra. En komponents bidrag
över bolagen summerar därför nära noll. När vi skriver att en komponent gynnar ett bolag är
det ett påstående om bolagets läge i förhållande till sina jämförelsebolag, inte om kostnader
som skapats eller tagits bort i absoluta termer.

För det andra följer av detta att en komponent kan vara liten i genomsnitt men stor i
omfördelning. Genomsnittet över bolagen säger hur en komponent påverkar sektorns samlade
krav; spridningen säger hur den flyttar om de enskilda bolagen. En komponent vars
genomsnittsbidrag ligger nära noll kan ändå vara den som mest avgör de enskilda bolagens
utfall. Den aggregerade bilden och den fördelningsmässiga bilden besvarar därför två olika
frågor, och vi redovisar dem i två separata figurer snarare än att låta den ena tala för
den andra.

För det tredje är Shapley-värdet en rättvis redovisning av vad modellen mekaniskt gör,
given modellvalen: vilka komponenter som räknas som spelare, och vad baslinjen är. Det är
betingat på dessa val och på den enda specifikation och period som analyserats. Det är inte
en kausal kontrafaktisk utsaga om vad som skulle hänt om en komponent avlägsnades ur
verkligheten, och inte heller en policyrekommendation. Det är en exakt bokföring av en
befintlig modell, och bör läsas som en sådan.

## Sammanfattning av metoden

1. En komponents effekt kan inte avläsas genom att slå av komponenten, eftersom DEA är
   relativ och en komponents marginaleffekt beror på vilka övriga komponenter som ingår.
2. Leave-one-out och add-one-in är de två ändpunkterna för en komponents effekt. Gapet
   mellan dem mäter samverkan och motiverar en ordningsoberoende metod.
3. Shapley-värdet genomsnittar marginaleffekten över alla ordningar. Det är den enda
   uppdelning som summerar exakt till helheten och samtidigt behandlar komponenterna
   konsekvent.
4. De beräkningsmässiga förändringarna (mekanik och inputstruktur) hålls i ett yttre skikt
   och attribueras separat, så att kostnadskomponenterna fördelas givet den gällande
   modellen. Båda skikten är exakta och summerar tillsammans till hela förändringen.
5. Bidragen är fördelningsmässiga och betingade på modellvalen, inte absoluta eller
   kausala. Aggregerad nivå och fördelning redovisas separat.
