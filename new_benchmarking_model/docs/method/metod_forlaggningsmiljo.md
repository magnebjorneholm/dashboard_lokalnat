# Korrigering för förläggningsmiljö i benchmarkingen

*Status: Denna not beskriver vår operationalisering av Energimarknadsinspektionens
korrigering för förläggningsmiljö, given den information myndigheten har offentliggjort fram
till juni 2026. Inriktningen och dess motivering är Energimarknadsinspektionens; de konkreta
procentsatserna är vår härledning, eftersom myndighetens officiella schablonavdrag ännu inte
är publicerat. De siffror som anges bygger på föregående periods data och är illustrativa.*

## Syfte

Syftet med denna not är att förklara metodiken bakom korrigeringen för förläggningsmiljö,
alltså den justering av kapitalbasen som syftar till att ett nätföretag inte ska falla ut
sämre i benchmarkingen för en förläggningsmiljö det inte kan påverka. Läsaren antas känna
till DEA-modellen, TOTEX-ansatsen och kapitalbasen. Vi skiljer genomgående mellan vad
Energimarknadsinspektionen har angett som inriktning och vad som är vår härledning. En
viktig avgränsning: korrigeringen är en justering av benchmarkingens kostnadsunderlag, inte
av intäktsramen.

## Problemet och Energimarknadsinspektionens inriktning

Det kostar olika mycket att anlägga elnät beroende på förläggningsmiljö, exempelvis beroende
på om jordkabel förläggs i stadsmiljö eller på landsbygd. Detta är förhållanden ett nätföretag
normalt inte kan påverka utifrån sitt givna nätområde. Ett företag med en dyrare
förläggningsmiljö får därför en högre kapitalkostnad, och faller i benchmarkingen ut sämre på
ett sätt som inte speglar dess effektivitet. I avsnittet "Korrigering görs för dyrare
förläggningsmiljö" anger Energimarknadsinspektionen att skillnaden kan påverka effektiviteten
i så hög grad att det är motiverat att korrigera för den.

Inriktningen är att i benchmarkingen justera ned anskaffningsvärdet till en och samma
kostnadsnivå, landsbygd normal, för de förläggningsmiljöer som är dyrare. För att inte kräva
alltför detaljerad inrapportering per jordkabeltyp anger myndigheten att det går att beräkna
ett tillräckligt träffsäkert schablonavdrag i procent för respektive förläggningsmiljö, på det
totala anskaffningsvärdet för jordkabel. Avgränsningen i kostnadsslag är likaså angiven:
jordkabel ingår, eftersom den utgör en stor del av kapitalbasen och uppvisar stora
prisskillnader mellan miljöer; kabelskåp utesluts, eftersom dess andel och prisskillnader är
små nog att sakna betydelse; och en motsvarande korrigering ska göras för nätstationer.

Korrigeringen påverkar enbart jämförelsen, inte ersättningen. Effektiviseringsincitamentet
tillämpas på de okorrigerade anskaffningsvärdena, så att relativpriserna får genomslag i det
slutliga utfallet i kronor. Det är benchmarkingen som sker på mer lika villkor, medan
intäktsramen utgår från de faktiska kostnaderna.

## Premien ligger redan i prislistan

Den metodiskt avgörande observationen är att förläggningsmiljöns premie redan är inbyggd i
prisuppgiften. I dagens kapacitetsbevarande metod är varje kabeltyps normvärde, alltså priset
per kilometer, satt för den exakta kabeltypen (techspec och spänning) i dess specifika
förläggningsmiljö. En city-kabel av en viss typ har därför ett högre normvärde per kilometer
än samma kabeltyp på landsbygd normal. Som ett exempel ur normvärdeslistan kostar PEX 3x1x95
mm² vid 12 kV 441 285 kronor per kilometer på landsbygd normal, 596 153 på landsbygd svår,
1 179 781 i tätort och 1 610 809 i city.

Kapitalbasvärdet för en komponent uppfyller identiteten anskaffningsvärde lika med normvärde
gånger längd, vilket i datan håller exakt. Korrigeringen är därmed inte ett mätproblem utan ett
omprissättningsproblem: för att nivellera en kabel till landsbygd normal ersätter man dess pris
med landsbygd-normal-priset för samma kabeltyp. Premien behöver alltså inte skattas utifrån
någon extern källa, utan är skillnaden mellan miljöns pris och landsbygd-normal-priset i samma
lista.

## Att härleda schablonavdraget

Schablonavdraget härleds direkt ur denna prisstruktur. För varje justerbar förläggningsmiljö,
alltså city, tätort och landsbygd svår, mäter vi hur mycket dyrare samma kabeltyp är jämfört med
landsbygd normal, matchat på kabeltyp och volymvägt med den faktiskt installerade
kilometermixen. Resultatet är ett procentavdrag per förläggningsmiljö, vilket är just det
schablonavdrag i procent som inriktningen efterfrågar, härlett ur prislistans premiestruktur.
Landsbygd normal är referensen och justeras inte, och kablar utan miljöetikett, exempelvis
sjökabel, lämnas oförändrade.

Som illustration, på föregående periods data och med vår härledning, blir avdraget i
storleksordning 71 procent av värdet för city, 62 procent för tätort och 28 procent för
landsbygd svår, med ordningen city över tätort över landsbygd svår. Dessa procenttal är inte
Energimarknadsinspektionens publicerade siffror utan vår rekonstruktion ur prisstrukturen.

## Tillräckligt träffsäkert

Inriktningen ställer kravet att schablonavdraget ska vara tillräckligt träffsäkert. Vi prövar
detta genom att jämföra procentschablonen mot en exakt omprissättning per kabeltyp, där varje
komponent prissätts om individuellt mot landsbygd-normal-priset för sin egen typ. De två
ansatserna sammanfaller till en bråkdel av en procent på sektornivå, väl inom en procent. Detta
fastställer att den grövre procentschablonen är tillräckligt träffsäker i inriktningens mening,
och att den detaljerade inrapportering per kabeltyp som myndigheten vill undvika därför inte
behövs. Den exakta per-typ-ansatsen är alltså inte en konkurrerande tillämpningsmetod utan den
precisionsreferens som validerar schablonen.

## En strukturell egenskap: korrigeringen nivellerar bara nedåt

Två egenskaper i korrigeringen är värda att lyfta, eftersom de är lätta att läsa fel.

För det första nivelleras samtliga dyrare miljöer ned till landsbygd normal, inklusive
landsbygd svår. Korrigeringen är alltså inte en lättnad enbart för stadsnät, utan en
normalisering av hela förläggningsmiljögradienten ned till den billigaste standardmiljön. Även
ett företag i svår terräng får sin kapitalbas nedjusterad.

För det andra justerar korrigeringen bara nedåt, aldrig uppåt. Avdraget kapas till intervallet
noll till komponentens värde, vilket innebär att en kabel som är billigare än landsbygd normal
lämnas oförändrad i stället för att skrivas upp. Korrigeringen är därmed enkelriktad: den kan
bara minska den mätta kapitalbasen. I aggregat krymper den sektorns mätta jordkabelbas, och i
benchmarkingen komprimerar den de kostnadsskillnader mellan företag som härrör ur
förläggningsmiljö. Eftersom DEA är relativ är effekten på det enskilda företagets krav
fördelningsmässig, inte absolut.

## Nätstationer: en parallell korrigering

Energimarknadsinspektionen anger att även nätstationers värde skiljer sig mellan
förläggningsmiljöer, och att en liknande korrigering ska kunna göras som för jordkabel. Vi
operationaliserar den analogt: stationerna nivelleras mot en referensmiljö, och ett
procentavdrag härleds ur prisstrukturen på samma sätt som för jordkabel. Den enda
datamässiga skillnaden är att en stations förläggningsmiljö läses ur dess typuppgift i stället
för ur en separat miljöetikett. Stationskorrigeringen är mindre utförligt dokumenterad än
jordkabelkorrigeringen, och dess kalibrering bör verifieras separat.

## Integration och arbetsspecifikation

Korrigeringen ger ett justerat jordkabelvärde per företag. Eftersom den nuvarande
regleringens kapitalkostnadskedja är linjär i kapitalbasvärdet kan den justerade kapitalkostnad
som går in i benchmarkingen erhållas exakt genom att multiplicera jordkabelns
kapitalkostnadskomponent med reduktionsfaktorn, alltså justerat värde delat med ursprungligt
värde. Den justerade kapitalkostnaden ingår sedan i TOTEX, vilket beskrivs separat.

Följande punkter är vår härledning och inte fastställda av Energimarknadsinspektionen, och bör
läsas som arbetsantaganden tills myndighetens specifikation publiceras.

1. **De konkreta procentsatserna** är vår rekonstruktion ur prisstrukturen. Myndighetens
   officiella schablonavdrag är ännu inte publicerat.
2. **Normvärde som grund för premien.** Den kommande förmögenhetsbevarande metoden ersätter
   utifrån faktiska anskaffningsvärden, medan vi härleder premien ur normvärdeslistan, eftersom
   anskaffningsvärdet saknas i 98,5 procent av den tillgängliga datan. Härledningen vilar
   därmed på antagandet att relationen i pris mellan förläggningsmiljöer är densamma i
   anskaffningsvärde som i normvärde. Antagandet är rimligt, eftersom normvärdena enligt
   inriktningen i dag bär förläggningsmiljöns ersättning, men det är inte verifierbart ur denna
   data.
3. **Datan är från föregående period.** De redovisade procenttalen är illustrativa, och
   samtliga magnituder i noten är betingade på punkterna ovan.

## Sammanfattning

1. Ett företag ska inte falla ut sämre i benchmarkingen för en dyrare förläggningsmiljö det inte
   kan påverka. Kapitalbasen justeras därför ned till en gemensam nivå, landsbygd normal.
2. Premien ligger redan i prislistan, så korrigeringen är en omprissättning mot
   landsbygd-normal-priset för samma kabeltyp, inte en ny mätning.
3. Schablonavdraget i procent per förläggningsmiljö härleds ur denna prisstruktur och är
   tillräckligt träffsäkert: det sammanfaller med en exakt per-typ-omprissättning till väl inom
   en procent på sektornivå.
4. Korrigeringen nivellerar bara nedåt och omfattar hela gradienten, inklusive landsbygd svår,
   inte enbart stadsnät. Dess effekt på kravet är fördelningsmässig, eftersom DEA är relativ.
5. Jordkabel ingår, kabelskåp utesluts som försumbart, och en parallell korrigering görs för
   nätstationer. Korrigeringen påverkar benchmarkingen, inte intäktsramen.
6. Procentsatserna är vår härledning, inte Energimarknadsinspektionens beslut, och vilar på att
   miljörelationen är densamma i anskaffningsvärde som i normvärde.
