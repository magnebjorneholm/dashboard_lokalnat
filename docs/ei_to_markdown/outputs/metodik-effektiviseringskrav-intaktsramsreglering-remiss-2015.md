---
title: "Metodik för bestämning av effektiviseringskrav i intäktsramsregleringen för elnätsföretag (REMISS)"
subtitle: "Empiri och metodik"
source_file: "Metodik-for-bestamning-av-effektiviseringskrav-i-intaktsramsregleringen-for-elnatsforetag-REMISS.pdf"
publisher: "Energimarknadsinspektionen (Ei)"
author: "Göran Ek"
creator: "Acrobat PDFMaker 11 för Word"
document_date: "2015-03"
status: "Remiss (remissversion)"
regulatory_period: "2016–2019"
pages: 92
retrieved: "2026-06-22"
language: sv
note: >
  Migrerad från Ei:s remiss-PDF (mars 2015) till markdown avsedd som kontext för
  en kodagent, inte för visuell läsning. Detta är den metodrapport som i senare Ei-
  dokument refereras som "Metodik för bestämning av effektiviseringskrav i
  intäktsramsregleringen för elnätsföretag REMISS" (t.ex. fotnot 6 i Bilaga 9 för
  tillsynsperioden 2024–2027). Den beskriver metodvalet (DEA med CRS, TOTEX-modell
  D8(3+5), SFA som komplement, realiseringsfaktor 50 %, supereffektivitetsfilter)
  inför regleringsperioden 2016–2019.

  Konventioner: All brödtext är ordagrann. Avstavningar och PDF:ens kolumn-/
  sidbrytningar har slagits ihop till löpande stycken; sidnummer och sidfötter har
  tagits bort. Uppenbara stavfel i källan har behållits ordagrant (dokumentet är en
  remissversion och innehåller flera korrekturfel). Fotnoter återges med markdown-
  fotnoter ([^n]) med källans egen numrering (1–78) och samlas under "## Noter".
  Tabeller (Tabell 1–22) återges som markdown-tabeller med källans exakta siffror
  (svensk formatering: komma som decimaltecken). Figurer (Figur 1–19) är diagram/
  principskisser utan extraherbar data och återges som beskrivande text. Formler
  återges i otvetydig text-/Unicode-notation. Innehållsförteckningens sidnummer har
  utelämnats; rubrik 4 i källans innehållsförteckning hade en felinklistrad mening
  ("Sammanfattningsvis visar statistiken …") som här är struken ur rubriken och
  återförd till sin plats i löptexten i avsnitt 3.
---

# Metodik för bestämning av effektiviseringskrav i intäktsramsregleringen för elnätsföretag

*Empiri och metodik — remissversion, Energimarknadsinspektionen, mars 2015.*

## Innehåll

1. Sammanfattning
2. Inledning — Ellagen om effektiviseringskrav · Effektiviseringskrav · Syfte · Avgränsning · Genomförande
3. Eldistribution — Den tekniska strukturen · En heterogen bransch
4. Effektiviseringskrav — Reglering av monopol för samhällsnyttan · Incitamentsreglering (X-faktorn; asymmetrisk information) · Produktivitet · Effektiviseringskrav i intäktsramen · Val av modell
5. Data och metoder — Data · Metoder (partiella nyckeltal; regressions- och paneldataanalys; DEA; SFA)
6. Kostnadssamband — Modeller · Resultat (årliga tvärsnitt)
7. Analys av nätverksamheten — empiriskt underlag, modeller, DEA/panel-resultat, val av modell, utökad modell, OPEX/TOTEX D7 och D8, DEA vs SFA, användning av SFA
8. Studier av effektivitet och produktivitetsutveckling — elnätsföretagens utveckling · andra branscher · prognoser
9. Effektiviseringskrav i regleringar av elnät
10. Metodik för effektiviseringskraven — sammanfattning, val av metod/modell/data, från potential till krav, försiktighetsfilter, översikt, region-/stamnät
- Referenser
- Bilaga 1 Metoder — tvärsnitt/paneldata · Cobb-Douglas och translog · DEA och Malmquistindex · SFA
- Bilaga 2 Modeller av elnätsverksamhet — val av modell · modellöversikt

## Förord

Den 16 juni 2009 beslutade riksdagen om ändringar i ellagen (1997:857) som innebar att Ei från och med år 2012 på förhand beslutar hur stora elnätsföretagens intäkter får vara genom en så kallad intäktsram för en fyraårsperiod.

Inför den andra regleringsperioden 2016-2019 kommer nya effektiviseringskrav att ställas på elnätsföretagen. Föreliggande rapport behandlar metodiken för hur dessa krav ska fastställas. Metodiken innefattar att flera val måste göras. De faktiska effektiviseringskrav som respektive företag kommer att fastställas i beslutet om intäktsram.

Förslaget på metodik grundas på empiriska analyser av både kostnadseffektivitet och hur utvecklingen i produktiviteten varit historisk för de svenska elnätsföretagen över åren. Uppföljningen av elnätsföretagen kompletteras med referat av studier från andra länders eldistribution och de krav som ställs i andra länders regleringar av elnäten.

Eskilstuna, mars 2015

## 1 Sammanfattning

Energimarknadsinspektionen (Ei) har för avsikt att vid fastställandet av intäktsramarna inför nästa reglerperiod 2016-2019 ställa så kallade effektiviseringskrav på elnätsföretagen. Tanken bakom sådana är att nätkunderna ska få ta del av uppkomna produktivitetsökningar. Samtidigt innebär dessa incitament att företagen bör öka sin produktivitet. Om företaget inte ökar sin produktivitet genom att realisera de potentialer som finns, kommer elnätsföretagets avkastning successivt att minska. Om ökningen i produktivitet är större än de ställda kraven ökar avkastningen av verksamheten. Kravet ger incitament att rationalisera verksamheten och därmed öka produktiviteten. Genom att intäktsramen fixerar intäkten för en given verksamhetsnivå får företagen incitament att reducera kostnaderna. På så vis ökar överskottet och därmed avkastningen på det kapital som används. Kravet innebär således både "en morot och en piska".

Eftersom nätföretagen utgör naturliga monopol som är legalt reglerade, bör ökad produktivitet till viss del komma kunderna tillgodo i form av lägre nättariffer. Det ställda kravet på effektiviseringar syftar därför både till att få nätföretagen att bli mer rationella i sin verksamhet, och att resultaten av denna rationalisering också ska komma nätkunderna till godo. För marknader med konkurrerande företag sker detta via konkurrensen om konkurrensen är tillräckligt skarp. Men för en monopolmarknad, som distribution av el, behövs en reglering för att ökad produktivitet ska komma kunderna till del i form av lägre elnätstariffer.

För den första perioden 2012-2015 ställdes ett generellt krav som var lika för alla elnätsföretag. Ett generellt effektiviseringskrav på 1 % per år på de löpande påverkbara kostnaderna. För perioden 2016-2019 är avsikten att även ställa företagsspecifika krav. För att få fram underlag för bestämningen av storleken på effektiviseringskravet har flera analyser gjorts.

Den empiriska grunden för att formulera kraven bygger på hur produktiviteten utvecklats för elnätsföretagen i Sverige och skillnaderna i kostnadseffektivitet mellan elnätsföretagen. Referenser görs även till de studier av elnätsdistribution som gjorts i andra länder och de effektivitetskrav som ställts i andra länders regleringar av elnäten.

Den empiriska analysen baseras på de data som elnätsföretagen rapporterar in till Ei. Flera olika modeller som abstraherar elnätsverksamheten har prövats med flera olika metoder. Detta för att få kunskap om effektiviseringspotentialer och produktivitetsutveckling.

Analysen av det empiriska underlaget med olika modeller och metoder samt andra principiella överväganden kring incitamentsreglering har resulterat i följande förslag på metodik för bestämningen av effektiviseringskrav:

- **Metod för att beräkna kostnadseffektivitet:** Data Envelopment Analysis (DEA) med antagande om konstant skalavkastning (CRS).
- **Modell för att avbilda nätverksamheten:** en totalkostnadsmodell (TOTEX) med tre separata kostnadsposter som minimeras givet fem "produkter" - kostnadsdrivare: antal uttagskunder, antal nätstationer, maximalt effektuttag mot överliggande nät, överförd lågspänningsel och överförd högspänningsel.
- **Kostnadsposterna** består av operativt påverkbara kostnader (OPEXp), operativt opåverkbara kostnader (OPEXo) och kapitalkostnader (CAPEX).
- **Kapitalkostnaderna** beräknas med utgångspunkt i åldersjusterade återanskaffningsvärden, fastställd ekonomisk livslängd och fastställd kalkylränta.
- **Data** för jämförelsen av nätföretagen utgörs av de underlag som nätföretagen lämnar in till Ei i sin ansökan om intäktsram samt årsrapportdata över verksamheten för åren 2010-2013. Medelvärdet för de fyra åren för respektive företag används vid beräkningen. Kostnaderna realprisjusteras före beräkningen med användning av SCB:s faktorprisindex för elnätsföretag.
- **Det generella kravet** utgör ett minimikrav och fastställs till 1 procent per år för påverkbara löpande kostnader, vilket är det krav som tillämpats för innevarande reglerperiod 2012-2015. Nivån på denna baserades på analyser av produktivitetsutvecklingen för svenska elnät, utvecklingen i andra elnät samt de krav som ställs i regleringen av andra elnät.
- **Det företagsspecifika kravet** bestäms med utgångspunkt från estimerade effektiviseringspotentialer. För så kallat hypereffektiva företag enligt DEA-beräkningen används resultaten från en SFA-beräkning istället.[^1]
- **Transformeringen från potential till krav** sker genom en realiseringsfaktor, som bygger på överväganden om den möjliga takten i framtida effektiviseringar. Mätetal på effektivitet i TOTEX-modellen multiplicerat med realiseringsfaktorn appliceras på de operativt påverkbara kostnaderna. Ett tak på ett högsta krav sätts för de företag som avviker mycket i effektivitet relativt övriga företag.
- **Hantering av osäkerhet** i inrapporterade data görs genom att extrema effektivitetsresultat för enskilda företag exkluderas från att vara med och bilda den kostnadsfronten av effektiva företag. För vidimering av DEA-resultaten används även metodiken med panelregressioner och stokastiska kostnadsfronter.

Den valda metodiken innebär att incitamenten för effektivisering av alla delar i nätverksamheten ingår – inte bara de kostnader som på kort sikt är möjliga att påverka. Vidare ger den valda metodiken incitament till rationalisering av företagsstrukturen genom att effektivitetsjämförelserna görs med antagande om konstant skalvkastning. Ett antagande som innebär att oavsett storlek på verksamheten räknat i termer av antal kunder, ledningslängd eller annan kostnadsdrivare mm, och bör man kunna uppnå samma produktivitet (kostnad per kund eller kostnad per km ledning). Empiriska studier visar att det finns vissa skalfördelar, dvs att en större nätverksamhet har lägre kostnader på marginalen för att öka verksamheten ytterligare. Genom antagandet om konstant skalavkastning i beräkningen av kostnadseffektiviteten blir måttstockskonkurrensen hårdare för de mindre företagen, vilket innebär ett visst incitament till samgående med annat nätföretag.

Det är dock inte möjligt att tillämpa denna metod på regionnätsföretagen och stamnätsföretag då det finns få regionnätsföretag och endast ett stamnätsföretag. Av denna anledning avgränsas metoden till att endast omfatta de lokala elnätsföretagen. Resultaten av effektivitetsmätningarna av lokalnätsföretagen kan dock komma att utgöra del av beslutsunderlag för effektivitetskrav för regionnätsföretagen och stamnätet.

## 2 Inledning

Elnätsverksamhet är ett så kallat naturligt monopol och därför har det i ellagen införts regler för elnätsföretagen.[^2] Reglerna avser bland annat hur stora intäkter elnätsföretagen får ha och hur tarifferna ska utformas. Ei har för avsikt att vid fastställandet av intäktsramarna inför nästa regleringsperiod 2016-2019 ställa så kallade effektiviseringskrav på elnätsföretagen. Sådana krav innebär ett avdrag på i den intäktsram som nätföretagen tilldelas. Tanken bakom detta är att ge företagen incitament att rationalisera verksamheten och därmed öka produktiviteten. Genom att intäktsramen fixerar intäkten för en given verksamhetsnivå får företagen incitament att reducera kostnaderna. På så vis ökar överskottet och därmed avkastningen på det kapital som används. Det ställda kravet på effektiviseringar är ett verktyg för att fördela ut förväntade produktivitetsökningar till kunderna. Normalt sker detta automatiskt på marknader med fungerande konkurrens.

För den första perioden 2012-2015 ställdes ett generellt krav, lika för alla elnätsföretag på 1 procent per år på de löpande påverkbara kostnaderna.[^3] För perioden 2016-2019 är avsikten att även ställa företagsspecifika krav. För att få fram underlag för att bestämma av storleken på det företagsspecifika effektiviseringskravet har flera analyser gjorts.

### Ellagen om effektiviseringskrav

Reglerna för att ställa krav på effektiviseringar finns i 5 kap. 8 § ellagen (1997:857). "Som skäliga kostnader för att bedriva nätverksamheten ska anses kostnader för en ändamålsenlig och effektiv drift av en nätverksamhet med likartade objektiva förutsättningar".

Formuleringen: "…ändamålsenlig och effektiv drift av en nätverksamhet med likartade objektiva förutsättningar", kan tolkas som att elnätsföretagen dels "gör rätt saker", dels "gör saker på rätt sätt". Ändamålsenligt (göra rätt saker) kan tolkas som att företagen erbjuder de tjänster som kunderna efterfrågar till den kvalitet som kunderna önskar. Med "effektiv drift av en nätverksamhet med likartade objektiva förutsättningar" att de mest produktiva elnätsföretagen i Sverige ska utgöra en norm för vad som är skälig kostnad. Sådana företag har relativt övriga företag utfört sina prestationer (tjänster) på rätt sätt – till lägre kostnader per producerad enhet. Det innebär att bestämningen av effektiviseringskraven ska grundas på jämförelser av elnätsföretagen. Nätverksamhet bör här tolkas som att svenska elnätsföretag (distribution respektive region) utgör den population av företag som ska jämföras i första hand. Resultaten kan verifieras med information om effektivitetsskillnader och produktivitetsutveckling i andra länders eldistribution.[^4]

Även om förutsättningar och den legala regleringen skiljer sig åt mellan olika länders reglering, kan studier från andra elnät ge en kompletterande bild av effektivitetsskillnader och produktivitetsutveckling. I tredje hand kan även information om andra nätverksamheter, som distribution av gas eller VA-tjänster ge kompletterande underlag. I avsnitt 8 redovisas underlaget för detta.

Utmaningen i fastställandet av effektivitetskrav ligger i jämförelsen av elnätsföretagen. För att få en konkret nivå på den skäliga kostnaden behövs en referens av andra elnätsföretag som har "likartade objektiva förutsättningar" och som har producerat tjänsterna till lägre kostnad. Den ideala situationen är om flera (många) företag är lika med avseende på de olika faktorer som påverkar kostnaderna - som antal kunder, uttagen effekt, överförd elvolym, ledningslängder, geografiska förhållanden etc. Sådana "enäggstvillingar" till företag existerar tyvärr inte. Den näst-bästa-situationen är att jämföra företag som är relativt lika varandra utifrån tillgången på de data som finns tillgängliga. "Likartade" innebär således att en viss variation i förutsättningar med nödvändighet kan få finnas vid jämförelsen. Formuleringen "Objektiva förutsättningar" innebär att de faktorer som i första ger upphov till kostnader i verksamheten ska användas vid jämförelserna och att dessa faktorer inte är påverkbara). T ex antalet kunder eller deras lokalisering i distributionsområdet.

### Effektiviseringskrav

Formuleringen i ellagen visar på att effektiviseringskraven ska bygga på jämförelser av nätverksamheter, dvs att ett enskilt elnätsföretag jämförs med andra elnätsföretag och att det är effektiva elnätsföretag som utgör normen. De kan både sätta en norm för effektiviseringskrav och utgöra förebilder för andra företag, dvs studieobjekt i rationaliseringsarbetet i de enskilda företagen. Sådana jämförelser går under beteckningen benchmarking i företagsekonomisk managementlitteratur. I den internationella regleringsekonomiska litteraturen används termen "yardstick competition", vilket kan översättas med måttstockskonkurrens. Ett sådant underlag kan sedan kompletteras med studier av andra länders elnätsföretag, vilka krav som ställs i andra länders regleringar av elnätsföretag, av krav som ställs på andra verksamheter som producerar infrastrukturtjänster, som t ex vatten och avlopp.

Lagens formulering om att kostnaderna är skälighet för effektiva företag kan tolkas som att företag som identifierats som fullt effektiva inte behöver få något effektiviseringskrav. För den nu gällande regleringsperioden gäller ett generellt krav oberoende av hur effektiva företagen är. I vissa regleringar av elnätsföretag och andra infrastrukturtjänster har effektiviseringskraven delats upp i två komponenter: en del som mäter avståndet till effektivitetsfronten och en del som mäter hur fronten ändras över tiden. Förändringen i avståndet till fronten – upphinnardelen - visar hur avståndet till fronten har ändrats mellan perioderna, medan avståndet mellan den tidigare fronten och den nya fronten visar hur de effektiva företagen har utvecklats över tiden. Även fullt effektiva företag kan öka sin produktivitet och därmed flytta effektivitetsfronten – frontändringsdel.[^5]

För att även ställa krav på fullt effektiva företag kan det vara motiverat att även sådana företag får ett krav som motsvarar en viss del av hur produktiviteten har utvecklats historiskt (t ex föregående regleringsperiod), medan företag som inte är fullt effektiva även får ett företagsspecifikt krav som utgör en viss andel av uppmätt potential.

Den skillnad som mäts upp mellan företagen utgör en effektiviseringspotential. Tiden för att realisera uppmätta potentialer varierar beroende på kostnadsslag och kontraktstider. En vägledning är naturligtvis de mätningar som finns över hur produktiviteten utvecklas över tiden i olika studier. I flera länders regleringar har regleringsmyndigheten bestämt att potentialen ska kunna realiseras fullt ut på t ex åtta år (Finland).[^6] I Tyskland bestämdes att potentialen skulle kunna realiseras till hälften på fem år i den första perioden och fullt ut i den andra perioden.[^7] Ofta sätts ett tak på kravet. Även om kostnadseffektiviteteten är lägre än en viss nivå så får företagen det krav som denna nivå anger.[^8]

Även de företag som enligt mätningen är fullt effektiva företag kan förväntas kunna öka sin produktivitet över tiden. Vid ingången till den nya perioden kan man anta att dessa förväntningsmässigt kommer att höja sin produktivitet med vad som motsvararar den genomsnittliga frontförändringen. Det innebär att det även bör ställas ett krav på dessa företag och att dessa krav bör grundas på en viss andel, t ex 50 procent av den genomsnittliga frontförändringen.

### Syfte

Denna rapport har som syfte att ge ett kunskapsunderlag för bestämningen av effektiviseringskrav i intäktsramen för respektive elnätsföretag. Empiriska analyser av den svenska eldistributionen görs för att få kunskap om effektivitetsskillnader och produktivitetsutveckling. Resultat från studier av produktivitetsutveckling och effektivitetsskillnader i nätverksamhet i andra länder, samt vilka krav som ställs i andra länders regleringar av intäkten.

Med utgångspunkt i kunskapsunderlaget ska rapporten bestämma metodiken för fastställande av effektiviseringskraven för regleringsperioden 2016-2019.

### Avgränsning

Analysen i rapporten bygger på metoder som kan användas när det finns många företag som kan jämföras. Underlaget har varit de cirka 170 lokalnätsföretag som finns i Sverige. Det är dock inte möjligt att tillämpa denna metod på regionnätsföretagen och stamnätsföretag då det finns få regionnätsföretag och endast ett stamnätsföretag. Av denna anledning avgränsas metoden till att endast omfatta de lokala elnätsföretagen. Resultaten av effektivitetsmätningarna av lokalnätsföretagen kan dock komma att utgöra del av beslutsunderlag för effektivitetskrav för regionnätsföretagen och stamnätet.

### Genomförande

Arbetet har utförts i projektform. Projektgruppen har bestått av Göran Ek och Anders Falk. En referensgrupp har använts för diskussion av förslag och resultat. Gruppen har bestått av experter från några elnätsföretag samt branschorganisationen Svensk Energi.[^9] Ei har också anlitat två konsulter vilka bistått metodutvecklingen genom beräkningar av kostnadssamband, kostnadseffektivitet och produktivitetsutveckling.[^10]

## 3 Eldistribution

### Den tekniska strukturen

Det svenska elnätet är indelat i tre nivåer utifrån den spänning som ledningarna har: stam-, region- och lokalnät. Stamnätet är "ryggraden" i elnätet eller eltransportens motorvägar. Den el som produceras i de större anläggningarna matas in på stamnätet för att transporteras till landets olika delar. Stamnätet är uppbyggt av ledningar som har en spänning på 220 eller 400 kV. Stamnätet ägs och förvaltas av affärsverket Svenska kraftnät.

Regionnäten är länken mellan stamnätet och lokalnäten. Elen transformeras ned till en lägre spänningsnivå, vanligtvis 40-130 kV, innan den förs över till regionnätet. Lokalnäten är anslutna till regionnäten och har normalt en spänningsnivå på 0,4-20 kV. I huvudsak sker distributionen till konsumenterna via lokalnätet med undantag för ett antal större industrier med hög elförbrukning som är anslutna direkt till regionnätet.

### En heterogen bransch

Strukturen på lokalnätsdistributionen skiljer sig inte bara åt vad gäller ägandet utan också vad gäller storlek och kundtäthet. I figur 1 visas spridningen mellan företagen med avseende på både kundtäthet och storlek. Bredden på staplarna anger storleken mätt i antalet uttagspunkter. Höjden på staplarna visar hur många meter ledning det i genomsnitt går per uttagspunkt för respektive elnätsföretag. För de 156 företagen i figur 2 varierar kundtätheten från 20 till 308 meter per kund. Median- och medelvärdena uppgår till 90 respektive 99 meter per kund. Storleken varierar från 2 205 till 771 183 kunder. För de 21 företagen med färre än 2000 kunder varierar tätheten från 39 till 347 meter per kund. Median- och medelvärdena uppgår till 156 respektive 172 meter per kund. Medianföretaget har 12 503 kunder och medelföretaget har 33 324 kunder.

Utvecklingen mot färre och större företag har varit en pågående process under lång tid. I slutet av 50-talet fanns det drygt 1 500 företag och i början av 80-talet hade antalet minskat till 380 företag.[^11]

De två största områdena är Vattenfall Eldistribution AB (REL00583) med 727 000 kunder respektive E.ON Elnät Sverige AB (REL00593) med 771 000 kunder. Kundtätheten för Vattenfall är i genomsnitt 107 meter per kund. Eftersom det är ett mycket stort område med distribution i både glesbygd och tätort varierar naturligtvis kundtätheten kraftigt inom området.

#### Figur 1 – Kundtäthet och storlek 2006

Diagram (stapeldiagram/spridning). Varje elnätsföretag är en stapel: bredden anger storlek (antal uttagspunkter, x-axel 0 till ca 5 000 000) och höjden anger genomsnittlig kundtäthet (meter ledning per uttagspunkt, y-axel 0 till 300). Visar stor spridning i både storlek och kundtäthet mellan företagen.

I figur 2 har en Lorenzkurva ritats över den ackumulativa fördelningen av kunderna. Den visar att 75 procent av företagen (redovisningsområdena) har endast 19 % av kunderna och 90 procent av företagen har 35 procent av kunderna. Vid en helt jämn fördelning av kunderna blir grafen en rät linje mellan noll och ett.

#### Figur 2 – Fördelningen av kunderna mellan elnätsföretagen år 2011

Diagram (Lorenzkurva). Visar den ackumulerade fördelningen av kunder mellan elnätsföretagen. Axlar: kundtäthet (meter per uttag) mot antal uttagspunkter. Kurvans form illustrerar att kunderna är mycket ojämnt fördelade: 75 % av företagen har bara 19 % av kunderna; 90 % av företagen har 35 % av kunderna.

*Sammanfattningsvis visar statistiken att det finns skillnader i branschen med avseende på både kundtäthet och storlek.*

## 4 Effektiviseringskrav

### Reglering av monopol för samhällsnyttan

Regleringen av monopol har normalt flera mål för att få till stånd en så hög samhällsnytta för given kostnad (samhällsekonomiskt optimum). För det första bör regleringen se till att företaget inte kan utöva marknadsmakt och via denna ta ut alltför höga priser. För det andra ska regleringen ge incitament till effektiv verksamhet. I detta ligger att företagen successivt effektiviserar verksamheten och att även kvaliteten i produktionen upprätthålls på en väl avvägd nivå. Förutom dessa två mål finns även ett mål att företagen på lång sikt anpassar verksamheten med investeringar i rätt tid, med rätt kapacitet och rätt teknik.

I välfärdsekonomisk teori är reglerarens uppgift att maximera samhällets välfärd. Det innebär att summan av konsument- respektive producentöverskotten blir så stor som möjligt. För att uppnå detta ska marknaden vara priseffektiv, vilket innebär att den enhet som produceras på marginalen säljs till sin marginalkostnad och att marknaden är i balans.

Traditionell självkostnadsreglering är fokuserad på att kunderna skulle få lika stort konsumentöverskottet som skulle uppstå om det vore en konkurrensmarknad, dvs. hindra eller åtminstone motverka att monopolföretaget tar ut monopolpriser. Syftet med regleringen är då primärt att motverka monopolvinster, dvs. en fördelningspolitisk funktion.

Pris- och intäktstaksreglering har delvis flyttat fokus från fördelningsaspekten till produktionen genom att skapa incitament för att öka produktiviteten. Det innebär en avvägning i regleringen mellan att motverka monopolpriser (och höga vinster – monopolräntor) och att stimulera företagen till rationaliseringar som ökar produktiviteten.

Regleringen ska således dels se till att företagen inte tar ut för höga priser (nätavgifter), dels även sätta krav på effektiviseringar eftersom konkurrensen mellan företag saknas på grund av monopolställningen. För att regleringen ska vara långsiktigt uthållig bör den även ge nätföretagen möjlighet att få skälig avkastning på det kapital som krävs för att driva verksamheten. Regleringen ska således både ha ett kortsiktigt och långsiktigt perspektiv. Det kortsiktiga (statiska) perspektivet har kunden i centrum för att denne inte ska betala för mycket för tjänsten, medan det långsiktiga (dynamiska) perspektivet är till för att skydda kunden på sikt och att företagen får tillräcklig avkastning för att långsiktigt bedriva verksamheten.

Därför har olika typer av reglering utvecklats som sätter restriktioner på vilka priser som monopolisten kan ta ut för att förhindra att marknadsdominansen utnyttjas. Även krav på effektiviseringar och spelregler så att företagen får incitament till effektiviseringar av verksamheten och till att vara dynamiskt effektiva över tiden så att kapaciteten anpassas optimalt till hur efterfrågan på tjänsterna utvecklas är centralt för regleringar.

### Incitamentsreglering

Med incitamentsreglering (pris- och intäktstaksreglering) avses att stimulera en verksamhet till att bli mer effektiv. Företagsledningen ska få en drivkraft att effektivisera verksamheten. Minskade kostnader per producerad enhet innebär en samhällsekonomisk vinst generellt. Men även att vinsten för företaget ökar. Eftersom företaget är ett monopol ska regleringen tvinga företagen att dela med sig av produktivitetsökningen. De effektiviseringsvinster som förtaget uppnått utöver det ställda kravet får de behålla, vilket ger incitament till att rationalisera verksamheten.

#### 4.2.1 X-faktorn

Effektivitetskravet är den s.k. X-faktorn i teorin för incitamentsreglering. För drygt 20 år sedan inleddes en omstrukturering av flera infrastrukturbranscher i flera länder och där England i många avseenden gick före denna ideologiska utveckling. Med incitamentsreglering avsågs att regleringen skulle ge de reglerade företagen incitament till att bli mer effektiva. Den då gällande regleringen var utformad som en avkastningsreglering eller självkostnadsreglering och dessa gav incitament till överkapitalisering och ineffektiv produktion. Den reglering som då för drygt 20 år sedan började tillämpas vid privatisering av den brittiska el- och telemarknaderna fick benämningen RPI – X. Denna regleringsprincip innebär att från en godkänd utgångsnivå på priserna, skulle företagen få kompensation från inflation (RPI=prisindex som framförallt använts i Storbritannien och som skiljer sig något från konsumentprisindex), men också få ett "beting" i form av en X-faktor, som ger ett krav på att en del av uppnådda och förväntade ökningar i produktiviteten ska komma kunderna till del. Eftersom regleringen gjordes av hur mycket priserna fick förändras, benämndes regleringsmetoden som pristaksreglering. En sådan reglering är lämplig om antalet produkter är begränsat och det går att väga samman sålda produkter av olika slag med respektive priser. Intäktsandelarna från respektive produkt utgör vikter i en varukorg som ger ett sammantaget pris för hela verksamheten.[^12] Om antalet produkter (priser) är stort är det lättare att utforma regleringen som ett intäktstak.[^13] Att den totala intäkten får öka med utvecklingen av ett valt prisindex samt en reduktion av denna nivå utifrån en vald X-faktor.

En nackdel med ett generellt krav är hur företagen kommer att reagera på kravet. När regleringsperioden närmar sig slutet kommer regleraren att notera om företaget ökat sin produktivitet. När regleraren sätter det nya intäktstaket med en ny X-faktor kommer den lägre kostnadsnivån att utgör ett ingångsvärde. Sett i detta långsiktiga perspektiv kan företagets incitament att reduceras om de vet att uppnådda produktivitetsökning till viss del kommer att omfördelas till kunderna. Denna s.k. spärrhjulseffekt kan få företagen att öka sina kostnader i slutet av en regleringsperiod för att undvika framtida krav. Denna effekt har framförallt uppmärksammats när det handlar om reglering av ett (1) monopol, dvs. det finns endast ett monopolföretag i branschen. Om det finns ett mindre antal lokala monopol är det i princip möjligt att de kan bilda en implicit (tyst) kartell att agera gemensamt för att undvika spärrhjulseffekten. I en bransch som elnätsdistribution i Sverige med 170 lokala monopol med olika ägande (privat, kommunalt, statligt), är det troligen mycket svårt att få till stånd en tyst kartell. Den konkurrens som måttstockskonkurrens innebär skapar incitament till ökad produktivitet. De uppgifter som ligger till grund för jämförelsen grundas på medelvärdet av fyra års verksamhet, vilket innebär att en medveten kostnadsökning kan medverka till ett mer negativt utfall i kommande jämförelsen. Om ett företag inte rationaliserar, medan andra företag gör det kommer det första företaget att få låga effektivitetstal i nästa uppföljning och därpå följande krav på effektiviseringar i nästa period. Det innebär att spärrhjulseffekten troligen inte kommer att uppstå om företagens jämförs och de får företagsspecifika krav.

#### 4.2.2 Regleraren har ett kunskapsunderläge - asymmetrisk information

Det reglerade företaget vet mer om både sina egna kostnadsförutsättningar samt sin arbetsinsats (ansträngning) än vad tillsynsmyndigheten gör, vilket ger företaget en informationsfördel. Den välfärdsmaximerande tillsynsmyndigheten står således inför både ett problem med dold information och dold handling. Dold information (eller dolda egenskaper) innebär i detta fall en osäkerhet (eller okunskap) för tillsynsmyndigheten om de faktiska kostnaderna som det reglerade företaget har. Monopolet har således en möjlighet att övertyga tillsynsmyndigheten att detta har högre kostnader än vad det egentligen har, och därmed få en högre vinst. Dold handling innebär en osäkerhet (eller okunskap) för tillsynsmyndigheten kring hur stor arbetsinsatsen (ansträngningen) är från det reglerade företaget. Om det inte finns någon möjlighet till vinst, finns det inte heller något incitament att effektivisera (Se t ex Joskow, 2006).[^14]

Med perfekt information om kostnads- och efterfrågeförhållanden skulle den reglerande myndigheten kunna bestämma de samhällsekonomiskt optimala priserna och kvaliteten på produkten eller tjänsten ifråga och ge direkta order för dessa. Men då regleraren inte har den nödvändiga informationen för att bestämma den bästa lösningen måste regleraren istället försöka härma en marknad genom att utnyttja den information som finns tillgänglig. Tillgången på information är därmed en nyckelfråga vid reglering.

### Produktivitet

Med produktivitet avses generellt kvoten mellan producerad volym av en eller flera produkter och de resurser som förbrukats vid denna produktion. Om enbart en (1) produkt produceras med hjälp av en (1) resurs är det enkelt att mäta produktivitet.[^15] Detta förutsatt att det inte förekommer skillnader i kvalitet på använda resurser och presterade produkter. Om flera olika produkter produceras med hjälp av flera olika slags resurser blir uppgiften betydligt svårare. En sammanvägning måste då ske. Ett flertal metoder för detta finns. Den mest förekommande är sammanvägningen av produktionen sker via de priser som bildas på marknaden. Vägning sker genom att priserna på producerade produkter respektive använda resurser får fungera som vikter. För att en sådan sammanvägning ska bli rättvisande måste dessa priser vara samhällsekonomiskt rättvisande, d v s att de bildats på marknader med tillräckligt hög konkurrens. Endast då uttrycker priserna den samhällsekonomiska alternativkostnaden. På många marknader är konkurrensen ofullständig vilket gör att priserna inte helt rättvisande visar på alternativkostnader. Det finns också situationer då priserna är satta av endast ett företag, vilket är fallet för många offentliga monopol.

Produktiviteten i en verksamhet ökar om mer produceras för en given resursinsats eller genom att resursanvändningen minskar för en given produktion. Ökad produktivitet kan uppnås på flera sätt. De sker dels mer löpande i verksamheten, dels i samband med investeringar där ny teknik kan reducera behovet av andra resurser som t ex personal.

1. Förbättringar genom successiva rationaliseringar.[^16]
2. Investeringar i ny teknik eller införande av nya organisation.
3. Realiserandet av stordriftsfördelar genom att olika nät fusionerar i samma organisation.[^17]

När utvecklingen av produktiviteten mäts är det möjligt att dela upp förändringen i vad som beror på hur avståndet till fronten och hur fronten har ändrats. Fronten bildas av de mest produktiva företagen vid respektive mättillfälle. Se figur 3.

### Effektiviseringskrav i intäktsramen

Om ett företag har en uppmätt potential att minska kostnaderna med exempelvis 20 %, kan kravet sättas utifrån en bedömning av hur mycket som bör kunna realiseras under de fyra åren i den kommande reglerperioden. Om det bedöms att minst hälften av potentialen bör kunna realiseras under fyra år, innebär det en realiseringsfaktor på 50 %. Företaget ska då få en intäktsram som uppgår till 90 % av utgångsnivån. De företag som realiserar mera under reglerperioden får behålla denna del fullt ut. Det är grundtanken med incitamentsreglering.

Vid uppföljningar av hur produktiviteten i elnätsverksamhet utvecklats visar olika studier (se kapital 8) på årliga ökningar av produktiviteten kring 2 %. I den OPEX-modell som redovisas i avsnitt 7.6 ökar produktiviteten med 1,6 % mellan år 2004 och 2012. Dessa ökningar är medelvärden, vilket innebär att det finns företag som både lyckas bättre och sämre. Medianvärdet uppgår till 1,4 % per år vilket innebär att hälften av företagen har lägre utveckling oh den andra halvan av företagen ökat sin produktivitet med mer än 1,4 % per år. Ett effektiviseringskrav på säg 1,4 % per år på OPEX som lagts in för åren mellan år 2004 och 2012 innebär således att hälften fått minskade marginaler och den andra hälften ökade marginaler.

I vissa regleringar av elnätsföretag och andra infrastrukturtjänster har effektiviseringskraven delats upp i två komponenter: en del för de ineffektiva företagen för att komma ifatt de effektiva företagen (effektivitetsändring) och en del för de som är fullt effektiva och därmed är med och bildar fronten. Förändringen i fronten kan ses som de mest effektiva företagens ändring i produktivitet.[^18] Se figur 3.

Argument för att även de idag mest effektiva företagen ska ha ett krav på ökad produktivitet är att den tekniska utvecklingen skapar nya potentialer även för de idag fullt effektiva företagen. Ett sådant krav har sin grund i bedömningar av hur fronten ändrar sig (den tekniska förändring som kan estimeras i branschen).

I figur 3 visas principen för detta. Elnätsföretag A har en potential vid ingången av regleringsperioden som motsvaras av avståndet till fronten vid period 1. Fronten bestäms av ett företag under respektive period (de som ligger på linjerna i figuren). Fronten skiftar ner, vilket innebär möjligheter att producera till lägre kostnad för given produktion under regleringsperioden för att vid ingången till nästa period motsvara läget för period 2. Vid ingången till period 2 har företag A dels realiserat hela den potential som mättes upp inför period 1, dels ökat produktiviteten ytterligare eftersom den ligger nedanför fronten vid period 1.

#### Figur 3 – Effektivitetspotentialer över tid

Principskiss. Visar hur ett elnätsföretag A:s potential mäts som avstånd till effektivitetsfronten vid period 1, och hur fronten skiftar nedåt (lägre kostnad för given produktion) till period 2. Illustrerar uppdelningen av produktivitetsförändring i (a) effektivitetsförändring (avstånd till fronten/upphinnardel) och (b) frontförändring (de mest effektiva företagens egen produktivitetsökning, "teknisk ändring").

Frontförändring som norm för det generella kravet innebär att man bör ha ett tillräckligt långt tidsperspektiv. För att få en mer stabil estimering av det generella effektiviseringskravet bör då en relativt lång panel användas där man enbart gör en estimering av en tidstrend för att få en genomsnittlig förändring över många år.

### Val av modell

För att beskriva en verksamhet som distribution av el måste man göra en abstraktion av verkligheten. All analys av verkligheten bygger på abstraktion. Frågan som måste hanteras är hur detaljerad en modell ska vara för att vara optimal. Här finns ett val mellan en enkel men mindre verklighetstrogen modell och en mer komplicerad modell som bättre avspeglar verkligheten. Det finns många alternativa modeller att välja mellan på en skala från t ex ett partiellt nyckeltal till en modell med många variabler som också kan hantera icke-linjära samband mellan kostnader och produktion. En enkel modell kan uppfattas som transparant – enkel att förstå, men beskriver verkligheten otillfredsställande. Den blir alltför oprecis. Ett enkelt (partiellt) nyckeltal som operativa kostnader per uttag ger en bild som bortser från andra aspekter som nätets kapacitet, ledningsnätets omfattning, överför energi osv. Ett sådant nyckeltal verkar intuitivt lätt att förstå, men bortser då från olika interaktionssamband. Ett sådant nyckeltal fångar inte upp om det finns stordriftsfördelar eller samproduktionsfördelar (eller dito nackdelar). Man brukar säga att en modell ska vara så enkel som möjligt men inte enklare.[^19]

Utmaningen vid måttstockskonkurrens ligger i att formulera en modell som på ett tillräckligt uttömmande kan visa på kostnadssambanden. Generellt räcker det med två till tre variabler för att modellen kan förklara mer än 90 % av kostnadsvariationen i en regressionsanalys och en statistiskt signifikant förklaring till hur kostnaderna varierar med dessa variabler.

En produktionsmodell består dels av en eller flera variabler som representerar resursanvändningen (kostnaderna), dels variabler som representerar produktionen. Produktionen genererar kostnader, t ex nätförluster för överförd energivolym, men det finns även faktorer som inte utgör produkter men som ändå är kostnadsdrivare. Dessa brukar benämnas som miljöfaktorer eller strukturella faktorer. Exempel på sådana är klimat, geografi, geologi, etc. I figur 4 visas principen för en produktionsmodell. Resurser används i verksamheten antingen direkt som fysiska resurser som arbetstid, elenergi, realkapital eller i monetära termer som operativa respektive kapitalkostnader. Produktionen kan representeras av utfört transportarbete (överförd energi), tillhandahållen kapacitet som står till kundernas förfogande och service till kunderna.

#### Figur 4 – Produktionsmodell, princip

Principskiss av en produktionsmodell för ett nätföretag, med tre "sidor":

- **Kostnader (input):** Operativa kostnader, Kapital.
- **Produktion (output):** Transport, Kapacitet, Service.
- **Strukturella faktorer (ramfaktorer):** geografi, geologi, klimat, bebyggelse.

De tre grupperna är oberoende listor (ingen radvis koppling mellan kolumnerna). Nätföretaget omvandlar input (kostnader) till output (produktion) under påverkan av de strukturella faktorerna.

Beräkningstekniskt går det att använda flera variabler på alla tre "sidorna" i modellen. Tillgången på data och antalet observationer (företag) utgör här begränsningar. I en totalkostnadsmodell ska både operativa kostnader och kapitalkostnader ingå (antingen som ett sammanslaget belopp eller som separata variabler).[^20] I en modell som enbart minimerar de operativa påverkbara kostnaderna kan inputvariabeln för kapital ingå som en variabel som inte minimeras vid beräkningen utan endast utgör en restriktion. Beräkningen minimerar de operativa kostnaderna givet nivån på kapital (fysiskt eller monetärt beräknat) och givet den output som verksamheten har. Denna output kan då dels bestå av de tjänster som tillhandahålls (transportarbete, att hålla kapacitet tillgänglig), men också strukturella faktorer som t ex geografiska förhållanden.[^21]

En variabel som överförd elenergi är en naturlig variabel i en modell för elnätsföretag. Den används också i de flesta modeller som mäter effektivitet och produktivitetsutveckling. Det är en variabel som är exogen och som nätföretaget inte kan påverka.[^22] För en effektivitetsmätning med en operativ kostnad som inte innehåller nätförluster är elenergi mindre lämplig eftersom överförd elenergi innebär nätförluster, men då dessa inte är med blir det en skev bild av den operativa effektiviteten. Överförd elenergi är en prestation men ingen kostnadsdrivare i detta fall.

Med hjälp av regressionsanalys kan olika modeller prövas. Det är främst på output och struktursidan som olika variabelkandidater finns att välja på. Generellt finns det stor samvariation mellan variablerna eftersom vi ha en stor spridning i storlek mellan företagen samtidigt som samvariationen är relativt lika. Det gör att förklaringsvariablerna samvarierar i stor utsträckning, vilket innebär att en del blir överflödiga i den meningen att de inte ökar på förklaringsgraden. En variabel som överförd elenergi ger högt signifikant samband, trots att nätförlusterna inte finns med i en modell med enbart påverkbara operativa kostnader. Om kostnaderna för nätförluster finns med på kostnadssidan, kan överförd el ses som en förklaringsfaktor.

Det är fullt möjligt att flera modeller ger ungefär samma genomsnittliga potential i branschen och ungefär samma rangordning mellan företagen vad gäller kostnadseffektiviteten. Det är en fördel om det finns fler modeller som på branschnivå ger ungefär samma utfall.

Om flera modeller ger ungefär samma rangordning innebär det att tillförlitligheten i jämförelsen ökar. Nivån på den genomsnittliga potentialen beror t ex på hur många variabler som ingår i modellen. Vid en DEA mätning av en viss modell blir potentialen högre generellt jämfört med en stokastisk frontanalys (SFA). Detta beroende på att i det senare fallet tas en del av uppmätt ineffektivitet i DEA-mätningen bort som slumpmässigt brus vid en SFA. Det viktiga är då att jämföra rangordningen mellan företagen. Om rangordningen är ungefärligt lika visar det att resultaten är stabila.

Vid både beräkningar med DEA och SFA finns flera antaganden som kan göras. För DEA har antaganden om skalavkastning betydelse för resultaten. För SFA har det betydelse vilken dataform som används, t ex normerad linjär modell eller loglinjär modell eller s.k. translogaritmisk modell. Vidare kan olika antaganden om intercepten i regressionen göras: fixa effekter eller slumpmässiga.[^23] Dessutom behöver antaganden göras om hur slumptermen är statistiskt fördelad. Se avsnitt 5.2.

När det gäller skalantaganden vid DEA innebär ett antagande om konstant skalavkastning (CRS) att alla företag förutsätts kunna uppnå samma produktivitet oberoende av storlek på verksamheten. Med antagande om varierande skalavkastning (VRS) kommer företag på fronten att ha olika produktivitet beroende på att skalvkastningen varierar över verksamhetsnivåerna. Med antagande om NDRS (non-decreasing-returns-to-scale) antas istället att avtagande skalavkastning inte förekommer, men att tilltagande kan förekomma.

I ett långsiktigt regleringsperspektiv är ett antagande om CRS motiverat om regleringspolitiken har som mål att få till stånd en strukturutveckling som ett medel för dynamisk effektivitet. Ett CRS-antagande innebär att måttstockskonkurrensen ökar vid mätningen, eftersom alla företag antas ha samma möjlighet att uppnå den mest produktiva nivån, dvs. effektivitetsfronten. Med ett antagande om varierande skalavkastning (VRS) kommer jämförelsen att begränsas till företag av ungefär samma storlek.

Både de empiriska studier som refereras till och de beräkningar som Ei gjort visar på att det finns stordriftsfördelar inom nätverksamheten, om än inte så stora. Resultaten skiftar mellan olika studier. I de estimeringar som redovisas i föreliggande rapport ger en ökning av verksamhetsnivån med 1 % en ökning med de operativa kostnaderna på ca 0,95 %.

Vid ett VRS-antagande kommer fler av både de mindre och de största företagen att noteras som mer eller fullt effektiva jämfört med antagande om CRS. För de företag som har tilltagande skalavkastning innebär det att verksamhetsnivån bör öka då marginalavkastning är högre än genomsnittligt på insatta resurser. Inom respektive företags distributionsområde är produktionen bestämd exogent av antalet kunder, deras uttag av el och kapacitet respektive av olika miljöfaktorer som geografin. Endast sättet att växa i verksamhetsnivå är genom samgående med andra elnät. Potentiella skalfördelar kan då få möjlighet att realiseras. Ett antagande om CRS innebär en skarpare måttstockskonkurrens jämfört med VRS eller NDRS.

En minimering av enbart påverkbara kostnader (OPEX_1) givet kostnader för kapital (CAPEX) kan visas i figur 5. En minimering kan ske genom en proportionell minskning i båda kostnadsslag till man når fronten, som bildas av de två företag som liknar företag A mest i fråga om resursanvändning och produktion. Den minimeringen ger ett mått AB/AO som effektivitetskvot. En minimering kan också ske genom att minimera enbart OPEX givet kapitalkostnaden. Här sker då enbart en minskning i OPEX givet kapitalkostnaden (och det som producerats). Kvoten AC/AD ger effektivitetskvoten. Istället för att minskningen sker proportionellt mot origa sker den nu vertikalt mot punkten D.

#### Figur 5 – Mått på effektivitet

Principskiss (två kostnadsaxlar: OPEX och CAPEX). Företag A jämförs mot en front bildad av de mest lika företagen. Två minimeringssätt illustreras: (1) proportionell minskning av båda kostnadsslagen mot origo tills fronten nås i punkt B → effektivitetskvot AB/AO; (2) minskning av enbart OPEX (CAPEX hålls konstant) vertikalt till punkt D → effektivitetskvot AC/AD.

Vid de beräkningar som har gjorts visar det sig att mätetalen på effektivitet blir oförändrade eller lägre när ett kostnadsslag som t ex CAPEX läggs in som restriktion jämfört med att det deltar i minimeringen. Trots att det är principiellt motiverat att lägga in kostnadsposter som opåverkbara (restriktioner) i modellen, verkar det av de modeller och data som vi använt, att resultaten inte ger någon större inverkan på effektivitetsfördelningen eller nivån på effektiviteten.

För att undvika att felaktiga eller onormala värden i dataunderlaget influerar kraven kan s.k. supereffektivitetsberäkning göras. En beräkning som innebär att när ett företags effektivitet mäts så jämför man företaget ifråga med övriga företag exklusive företaget ifråga. Om företaget är effektivt kommer de att få mätetal som blir 100 % eller högre. En regel för att exkludera ett företag med höga mätetal har tillämpats i den reglering som sker i Tyskland.[^24] Regeln för att ett företag ska exkluderas från att ingå i effektivitetsfronten har följande formulering:

> Ei(n-i) > q(0,75) + 2,0·[q(0,75) − q(0,25)]
>
> Ei(n-i) = mätetal på effektivitet
> q(0,75) = fjärde kvartilen för alla företag
> q(0,25) = första kvartilen för alla företag

Parametervärdet 2,0 har använts i de beräkningar som gjorts. Ett lägre värde som 1,5 ger att gränsen för exkluderande minskar, vilket innebär att fler företag kommer att exkluderas. Om mätetalet för effektivitet överstiger summan av 3dje kvartilvärdet och två gånger skillnaden mellan 3dje och 1sta kvartilvärdet, utgår företaget från att var med och bilda front för andra företag, dvs. blir inte förebild för företag som inte är fullt effektiva.

Ett sätt att förklara uppkomsten av extrem supereffektivitet är figur 6. Särskilt om ett företag har en ovanlig mix av produkter och/eller resurser kan avståndet mellan företagets position (punkt A) i figuren och dess virtuella motsvarighet på fronten när företaget endast jämförs mot övriga företag, bli stort.

#### Figur 6 – Supereffektivitet

Principskiss (två resursaxlar: Resurs 1, Resurs 2). Jämförelsen sker mot övriga företag (företaget självt exkluderas). Tre företag (A, B, C) ingår. När A jämförs mot de övriga två bildas fronten av den vertikala förlängningen från B (punkt b) och mätetalet blir över 1. Särskilt vid extrem resursmix kan supereffektiviteten bli hög på de horisontella/vertikala delarna av fronten. När B jämförs mot övriga får B kvoten OAC/OB > 1; normkostnaden bildas av AC, vilket innebär att B kan öka sin resursanvändning till punkten AC och fortfarande mätas som helt effektiv.

Jämförelsen sker här mot övriga företagen. I jämförelsen ingår 3 företag. När A jämförs mot övriga två företag kommer fronten för A att bestå av den vertikala förlängningen från B som när fronten vid b och mätetalet kommer att bli över 1. Särskilt om företagen har en extrem mix av resurser kan supereffektiviteten att bli hög, dvs. på de horisontella eller vertikala delarna av fronten. När B jämförs mot övriga kommer B att få kvoten OAC/OB vilket överstiger 1. Normkostnaden bildas av AC vilket innebär att företag B kan öka sin resursanvändning till man når punkten AC och fortfarande mätas upp som helt effektiv. För det effektiva företaget A hamnar referensföretaget klart ovanför företag D. Det är vanligt att företag som är extrema och befinner sig i "utkanten" av rummet blir mätetalen lätt mycket höga när minimeringen träffar vertikala eller horisontella delar av fronten.

Det uppkommer också resultat där företaget är effektivt men det utgör bara förebild för sig själv. Detta beror på att detta företag har en mix av data som avviker från andra företag, vilket gör att det inte går att hitta några företag med ungefär samma mix som är mer produktiva I detta fall karakteriseras företaget som "hypereffektivt".[^25] I dessa fall kan en lösning vara att använda mätetalet på en SFA-beräkning för att få en mer pålitlig bestämning av effektiviseringspotentialen. Det finns ofta ett samband mellan extrem supereffektivitet och att företaget sällan utgör förebild för flera företag än sig själv.

## 5 Data och metoder

### Data

De uppgifter som används kommer från de årsrapporter som elnätsföretagen rapporterar in varje år. I dessa finns både finansiell information (resultaträkningsdata) och produktionsdata (t ex antal kunder och överförda volymer av el) samt anläggningsdata som t ex antal km ledning och kabel uppdelat på olika kategorier.

Dessa data finns samlade i en databas (NEON) och en del av dessa data finns tillgängliga i form av excelfiler på hemsidan för Ei.

För beräkning av produktivitetsutvecklingen över tiden räknas kostnaderna om i reala kostnader via faktorprisindex (FPI) för elnätsföretag. Detta index som SCB tar fram årligen visar prisutvecklingen för resurser som nätföretagen använder i sin verksamhet.

Data över åren 2004-2012 kommer att användas. För perioden 2006-2009 görs en extra analys på de data som elnätsföretagen lämnade in inför den första perioden med intäktsramar. Dessa data skiljer sig något från de årsrapportdata som årligen lämnas in. Skillnaden är för gruppen som helhet mycket liten, men finns för några få företag där skillnaderna kan få betydelse. Det handlar om leasingkostnader där fyra till sex företag har sådana kostnader som utgör mer än 5 % av OPEXp.

### Metoder

Flera metoder kan användas för att följa upp effektivitetsskillnader och produktivitetsutvecklingen. Från enkla nyckeltal som ger partiella mått på skillnader i kostnader, t ex operativ kostnad per ansluten kund (abonnemang), till mer komplexa metoder som bygger på ekonomisk teori och ekonometri, som DEA (Data Envelopment Analysis) och SFA (Stochastic Frontier Analysis).[^26]

De metoder som kommer att användas är regressionsanalys på tvärsnitt, paneldataregressioner, icke-parametriska beräkningar DEA, Malmquistindex och SFA.[^27]

#### 5.2.1 Partiella nyckeltal

Fördelen med partiella nyckeltal är dels att de är lätta att beräkna och dels att de är lätta att förstå. Nackdelen är att de endast ger en partiell bild av verksamheten och därför kan missförstås. Ett företag med många kunder framstår som kostnadseffektivt om de har lägst kostnad per kund. Om detta företag i jämförelse med andra företag har få meter ledning per kund, kommer detta inte att synas i det första nyckeltalet. I termer av kostnad per km ledning kan företaget ifråga vara ett högkostnadsföretag. Det räcker inte med ett nyckeltal för att få en tillräckligt god bild av företagets förmåga att omforma resurser till prestationer.

Partiella nyckeltal kan används som ett sätt att granska data för att hitta extremvärden (som kan vara felaktiga, t ex redovisning av överförd el i kWh istället för MWh). De kan också användas som en rimlighetskontroll gentemot de mer komplexa metoderna där en samtidig beräkning sker av flera faktorer. Variabler som visar sig vara klart signifikanta i en regressionsanalys, som t ex antal kunder och ledningslängden utgör exempel på lämpliga nyckeltal.

#### 5.2.2 Regressionsanalys och paneldataanalys

Ett vanligt sätt att undersöka vilka faktorer som ger upphov till kostnader är att göra en regressionsanalys. I en sådan analys relateras den beroende variabeln (exempelvis operativa kostnader) till en eller flera oberoende variabler som ska förklara variationerna i kostnaderna. Varje enskilt elnätsföretag utgör en observation. Vid en analys kan man få svar på om de oberoende förklaringsvariablerna är signifikanta i statistisk mening och därmed är en rimlig kandidat till att utgör en förklaring. Man får också svar på hur mycket av variationerna i kostnaderna som modellen (de oberoende variablerna) tillsammans kan förklara.

Regressionsanalys kan därmed användas som en första metod för att få fram en eller flera modeller för själva måttstockskonkurrensen (benchmarkingen). Regressionsanalyser kan göras för respektive år som en tvärsnittsanalys. Det är också möjligt att genom en paneldataregression analysera flera års tvärsnittsdata. Fördelen är att fler observationer tillkommer, vilket ökar tillförlitligheten i estimeringarna. En större produktionsmodell kan estimeras jämfört med om endast tvärsnittsdata för ett år i taget används. Ytterligare en fördel är att företagsspecifika faktorer (som det inte finns data över) kan skiljas ut vid estimeringen. För varje företag kan det finnas olika faktorer (som det saknas data över). Skillnaderna kan sammanfattas som en konstant företagsspecifik faktor, t ex en extra problematisk miljö som verksamheten bedrivs i.

I bilaga 1 redovisas metodiken närmare.

#### 5.2.3 DEA - data envelopment analysis

En ofta använd metod för att jämföra effektiviteten i olika verksamheter är Data Envelopment Analysis (DEA).[^28] Den har tillämpats på en mängd olika verksamheter t ex privat näringsverksamhet som banker, offentlig verksamhet som skolor och daghem samt olika naturliga monopol som t ex elnätsdistribution.[^29] Metoden är inte statistisk som regressionsanalys och ger därför inga signifikanstester, utan bygger på optimering med linjär programmering. För varje observation (nätföretag) formuleras ett optimeringsproblem (maximering av produktion givet existerande resursanvändning eller minimering av resursanvändningen givet faktisk produktion) där företaget jämförs mot andra nätföretag.

Med beräkningsmetoden kan kostnadseffektiviteten beräknas för modeller som innehåller flera resurs- och flera produktkategorier. Vid en minimering söker optimeringsprogrammet reducera användningen av resurskategorierna proportionellt tills effektivitetsfronten nås givet den produktion som företaget ifråga haft. Vid en maximering sker istället en proportionell expansion av produktkategorierna till man når fronten, dvs. den linjära kombinationen av effektiva företag som har producerat mera till samma kostnad. Eftersom produktionen av elnätföretagens prestationer på kort sikt är bestämd av antaluttagspunkter och överförd el till kunderna, är det naturligt att beräkna kostnadseffektiviteten genom minimering av kostnader givet det som producerats.

Fördelarna med DEA är följande:

- Kräver ingen prisinformation
- Kräver ingen eller lite av information om teknologin.
- Tillåter svaga antaganden a priori (förväg)
- Kan hantera flera olika inputs och outputs som separata variabler
- Ger som resultat vilka företag som utgör förebilder
- Identifierar vilka företag som är mest effektiva (bäst utförande)
- Relativt försiktig beräkning av potentialen för effektiviseringar
- Resultaten kan användas i benchmarking processer

Nackdelar med metoden är följande:

- Ger inga signifikanstester
- Känslig för extremvärden (felaktiga värden)
- Känslig för olikheter i populationen (heterogenitet)

I bilaga 1 ges en närmare beskrivning av metoden.

#### 5.2.4 SFA – Stochastic Frontier Analysis

Medan en regressionsanalys (OLS) estimerar ett genomsnittligt samband mellan beroende och oberoende variabler, estimerar SFA en produktionsfront (eller kostnadsfront). SFA innebär att vissa observationer hamnar ovanför fronten vid en produktionsfront (och nedanför vid en kostnadsfront) och där avståndet till fronten ses som en slumpterm.

Den stokastiska fronten innebär att den vanliga feltermen (residualen) vid en OLS delas upp i två delar: en slumpterm (vi) och en icke-negativ del (u) som mäter effektiviteten.

Fördelen med SFA är att estimeringen ger signifikanstester på modellen och dess parametrar. Till skillnad från DEA hänförs en del av avståndet till fronten i en ineffektivitetsdel och en "brusdel" (icke-systematiska slumpvariationer), dvs. en del av observationerna kommer att ligga över den estimerade fronten. Till nackdelen med SFA räknas att man måste utgå från en viss funktionell form på sambandet mellan beroende och oberoende variabler. Dessutom måste man göra ett antagande om hur fördelningen ser ut på det statistiska bruset (slumptermen).

Det som är fördelar med SFA motsvaras av det som är nackdelar vid DEA och vice versa enligt punkter ovan. Den stora fördelen är signifikanstester av sambanden. Medan nackdelen är tvånget att specificera ett grundläggande kostnadssamband.

Vid modellantagandet kan man använda flera alternativ. Vanligt förekommande är att göra modellen loglinjär vilket är mer flexibelt jämfört med en traditionell OLS-regression. Den är då linjär i parametrarna, men den tillåter att sambandet mellan beroende och oberoende inte är linjärt. En utveckling av denna ansats är att använda en translogaritmisk modell, som både hanterar olinjära samband och interaktioner mellan de oberoende variablerna. Ett alternativ till detta är att normera variablerna så att en av de oberoende variablerna används som nämnare, t ex kostnad/uttagskund mot ledningsländ per uttagskund etc.

I bilaga 1 ges en närmare beskrivning av metoden.

## 6 Kostnadssamband

För att hitta en lämplig modell för beräkning av kostnadseffektivitet är en analys av sambandet mellan kostnader och olika potentiella kostnadsdrivare (produkter) centralt. Kostnaderna har också olika grad av påverkbarhet sett i ett tidsperspektiv. På lång sikt är alla kostnader påverkbara. Kapitalkostnader kan påverkas genom de årliga investeringar som görs men är sedan opåverkbara.

Till opåverkbara kostnadsdrivare kan räknas olika faktorer i omgivningen som väder, klimat, geologi, bebyggelse naturtyper, odlingsmiljö, (jordbruk, skogsbruk). Sådana faktorer skiljer sig åt mellan företagen men är tämligen konstanta över tiden. Genom teknikutveckling kan dock inverkan av sådana yttre faktorer reduceras eller försvinna helt.

Att pröva olika modeller där olika potentiella kostnadsdrivare ingår blir ett första steg i analysen.

### Modeller

Från teknisk synpunkt finns kunskap om vad som genererar kostnader i nätverksamheten. Detta är en given utgångspunkt. I en modell måste man med nödvändighet begränsa antalet förklaringsvariabler. En orsak till det är att många variabler är mycket starkt korrelerade med varandra dvs. om en variabel ökar med 10 % ökar också en korrelerad variabel med säg 10 %. Problem med s.k. multikollinearitet uppstår. Om två variabler är perfekt korrelerade med varandra blir den ena som förklaringsfaktor överflödig.

Erfarenheterna visar att det räcker med endast några få variabler för att få förklaringsgrader på modellen på över 90 % (justerat R²-värde).[^30] I många studier av effektivitet och produktivitetsutveckling ingår överförd el som en vanligt förekommande förklaringsvariabel. Den kan enskilt förklara så mycket som 90 % av kostnadsvariationerna vid en tvärsnittsanalys. Det gäller även vid en modell med OPEX_1 (dvs. påverkbara kostnader) där nätförlustkostnaden inte ingår. Överförd el är av sakliga skäl inte en lämplig kandidat som förklaringsfaktor eftersom den kostnad som överförd el driver är just nätförlusterna. Överförd el är exempel på en variabel som är mycket väl korrelerad med andra variabler som antal kunder och ledningslängd.

### Resultat – estimering av kostnadssamband

Ett antal regressionsanalyser på årliga tvärsnittsdata samt även poolade data och paneldata har gjorts.

#### 6.2.1 Årliga tvärsnitt

Tidigare analyser av olika produktionsmodeller har visat att sambandet mellan påverkbara operativa kostnader (OPEX_1) till mycket stor del kan förklaras av enbart antal kunder och ledningslängd. Ytterligare en variabel som kan ge lite ytterligare förklaring till variationerna är installerad transformatorkapacitet (TRAFO).

Vid en analys där ledningslängden delades upp i luftledning respektive jordkabel samt mellan låg- och högspänning visar det sig att det är luftledning som bäst kan förklara variationerna i OPEX_1. Detta är naturligt då underhållskostnaderna för jordkabel rimligen bör vara betydligt lägre än för luftledning. Vid regressionsanalysen är signifikansen för luftledning är klart högst av de olika ledningskategorierna. I ett tvärsnittsperspektiv är således variabeln luftledning intressant som en tydlig förklaringsfaktor för de operativa kostnaderna särskilt underhållskostnaderna.

Vid en modell med operativa kostnader inklusive kostnad för nätförluster (OPEX_2) och där överförd el används som en förklaringsfaktor utgör längden på lågspänningsnätet en tydligt signifikant variabel. Vid en regression med nätförluster räknat i MWh och med överförd el uppdelad i låg- och högspänning är båda mycket klart signifikanta och där överförd el förklarar 86 % av variationerna i nätförluster. Det är också ett rimligt resultat eftersom man som tumregel har bedömt att tomgångsförlusterna i nätet uppgår till ca 20 % (att hålla transformatorerna strömsatta). Volymen lågspänningsel står enligt denna estimering för drygt 90 % av de lokala nätförlusterna.

I en translog-modell med ledningslängd, TRAFO och antal uttagskunder som förklaringsvariabler är både ledningslängd och antal kunder mycket klart signifikanta, medan TRAFO inte klarar 10 %-nivån (år 2011, R²=97 %, N=160 företag). Modellen uppvisar vissa skalfördelar där en volymökning på 1 % ger en kostnadsökning på 0,96 %). Parametervärden: 0,31 för ledning, 0,16 för TRAFO och 0,49 för kunder.

Eftersom modellen är translogaritmisk blir effekten av en volymökning olika beroende på dels storlek på verksamheten, dels på mixen av de tre förklaringsfaktorerna. I Tabell 1 redovisas hur de genomsnittliga parametervärdena ser ut för de 16 företagen som har högst kundtäthet, för tio företag med genomsnittlig kundtäthet och för 16 företag med lägst kundtäthet. Tabellen visar tydligt att ledningslängden som förklaringsfaktor ökar när kundtätheten minskar. För kundvariabeln gäller att den har klart högre vikt i tätortsnäten (0,75 jämfört mot 0,27 för näten med lägst kundtäthet). Parametervärdet för kunder blir så högt att det resulterar i negativt tecken för TRAFO. Dessa resultat visar att det är svårt att få fram normvärden som ska vara enhetliga för alla företag.

#### Tabell 1 – Olika parametervärden för olika kundtäthet

| Företagsgrupp | Ledning | TRAFO | Uttagskunder | Skalekonomi |
|---|---|---|---|---|
| 16 företag med högst kundtäthet | 0,22 | −0,04 | 0,75 | 0,94 |
| 10 företag med genomsnittlig kundtäthet | 0,31 | 0,15 | 0,50 | 0,96 |
| 16 företag med lägst kundtäthet | 0,39 | 0,33 | 0,27 | 0,98 |

Skattningen av skalfördelar visar att det är lite lättare att få ner kostnaderna i tätorter.

De operativa kostnaderna uppstår till stor del för underhållet av det nät som finns. Kapitalkostnaderna beror av nätets storlek, utformning och ålder. I en modell ingår nätet som en förklaringsfaktor tillsammans med antal uttagskunder. Beståndsvariabeln återanskaffningsvärdet (NUAK) räknades om till en årlig kapitalkostnad för att få en koppling mellan OPEX och CAPEX. I denna modell med två förklaringsfaktorer (translog) är båda variablerna starkt signifikanta. Parametervärdet estimerades till 0,5492 resp. 0,4100 för nätkapital respektive kund (År 2011, N=160 företag, R²=97 %, Skalelasticitet: 0,96.)

I en modell med de fyra ledningskategorierna som separata variabler, TRAFO och antal kunder är det luftledning högspänning och antal kunder som är signifikanta (parametervärde 0,10 för luftledning hög och 0,75 för kunder (År 2005, N=182, R²= 93 %). Luftledning signifikant medan jordkabel inte är signifikant. TRAFO/MVA signifikant på 5 %-nivån. Uttagsvariabeln mycket signifikant och med stor effekt (0,68 % vid 1 % ökning i uttagen givet övrig variablers nivå). Förklaringsnivån: R²= 0,95.

## 7 Analys av nätverksamheten

### Det empiriska underlaget

För analyserna används data över nätverksamheten för åren 2004-2012. Det innebär att 9 år av nätverksamhet kan analyseras.[^31] Totalt innebär det nästan 1500 observationer då 165 företag kan följas under 9 år. Särskilda analyser gjordes över de fyra år som låg till underlag för de nu pågående intäktsramarna.[^32] Data är hämtade från årsrapporterna som innehåller dels kostnadsdata i form av resultaträkning och balansräkning, dels en särskild rapport med olika produktionsuppgifter.

### Modeller

Jämfört med för 20 år sedan har antalet studier av effektivitet och produktivitetsutveckling ökat betydligt. Det finns idag relativt många studier gjorda i olika länder av nätverksamhet men trots det råder ingen konsensus om vilken modell över nätverksamhet som är den "rätta" modellen. Variabler som i vissa modeller ses som en produkt (output) är i andra en resurs (input). I vissa modeller är det enbart de operativa kostnaderna som utgör input, medan i andra modeller är det totalkostnaderna. I vissa modeller ingår särskilda ramfaktorer, som är variabler som inte ses som påverkbara, t ex faktorer, som geografi, geologi, klimat etc.

Antalet variabler varierar också betydligt. En faktor som bestämmer storleken på modellen i termer av inputs och outputs är antalet företag som jämförs och hur många år som data finns tillgängliga för.

För att undersöka sambandens styrka mellan resursvariabler och produktionsvariabler kan olika statistiska test användas. Både parametriska test som regressionsanalys och olika icke-parametriska rangordningstest som mediantest är lämpliga för detta. Här använder vi den regressionsanalys som även används för produktivitetsberäkningen. Endast variabler som är statistiskt signifikanta tas med i modellen. De faktorer som ska ingå i modellen bör ha ett naturlig saklogisk skäl för att ingå.

Ett antal kriterier kan ställas upp som ledning vid valet av modell för att undersöka kostnadssamband och produktivitetsutvecklingen:

- Variabeln ska vara en kostnadsdrivare, det vill säga positivt påverka kostnaderna vid ökad produktion.
- En kostnadsdrivare, som t ex antal uttagsabonnemang, kan genom en regressionsskattning testas för sin signifikans.
- Successivt kan man pröva olika modeller. Variabeln nätkunder kan delas upp i olika kategorier (hög- resp. lågspänning). Modellen kan då utökas från att bara har nätkunder som förklaringsfaktor till att ha hög- respektive lågspänningsabonnemang som förklaringsfaktorer.
- En uppdelning av en aggregerad variabel som kostnader, överförd el, antalet uttagspunkter eller ledningslängder görs om det kan visas att variationen i denna variabel har en statistisk signifikans.
- En ny variabel förs in om denna dels är motiverad av at det finns ett kostnadssamband, dels har stor inverkan på kostnaderna, det vill säga har en signifikant inverkan på variationen i beroende variabeln.

### Modell (luftledning, transformatorer och uttagspunkter)

Olika modellalternativ har prövats med utgångspunkt från modeller i andra studier. Det finns idag relativt många studier i flera länder över eldistribution. Ei har även gjort uppföljningar av kostnadseffektivitet och produktionsutveckling.[^33] I analyser av data för åren 2004-2012 har olika modellvarianter prövats. Utgångspunkten är att en variabel bör ha inverkan på kostnaderna. Efter en genomgång årsvis av olika modeller med fokus på en hitta en liten modell fokuserad på de operativa kostnaderna.

Denna modell har sedan närmare analyserats av de båda konsulterna.[^34] De använde sig av paneldataregressioner för att studera sambandet mellan förklaringsfaktorer under olika antaganden. Paneldataregressionerna ger genom det stora antalet observationer möjligheter att undersöka både årsvisa effekter (som stormar) och företagsspecifika (permanenta) förhållanden som genererar kostnader, t ex geografiska förhållanden som leder till högre kostnader relativt andra företag. Paneldataregressionerna undersöker de genomsnittliga kostnadssambanden. Vidare har också en SFA gjorts med olika antaganden.

Grundmodellen, som konsulterna arbetat med, består av operativa kostnader som beroende variabel vars variation som förklaras av tre oberoende variabler: antal uttagsabonnemang (nätkunder), installerad transformatorkapacitet (kVa) och längden på luftledningarna. Denna modell visade sig vara signifikant både för varje enskilt år och vid panelregressionerna.

Resultaten visar att även andra varianter på förklaringsvariabler ger signifikans, men även att variabler som bör vara kostnadsdrivande inte är signifikanta beroende på högt internt samband (multikollinearitet). En variabel som ofta används i effektivitetsmodeller är överförd el (transportarbetet). Den bör inte ha någon kostnadsdrivande inverkan på de påverkbara operativa kostnaderna då nätförluster inte ingår i kostnadsposten (beroende variabeln).

#### Tabell 2 – Operativ kostnad mot luftledning, jordledning, TRAFO och antal uttag år 2006

Regressionsstatistik (År 2006, beroende variabel OPEX_1): Multipel-R = 0,973071933; R-kvadrat = 0,946868988; Justerad R-kvadrat = 0,945654564 (95 %); Standardfel = 0,313710389; Observationer = 180.

| Variabel | Koefficienter | t-kvot | p-värde |
|---|---|---|---|
| Konstant | 6,23947E-16 | 2,66843E-14 | 1 |
| Luft | 0,070084729 | 4,56538485 | 9,36678E-06 |
| Jord | −0,067895002 | −0,891364615 | 0,373957498 |
| MVA nätstationer | 0,226922692 | 2,277900809 | 0,023941836 |
| Antal uttagsabonnenter | 0,682533145 | 7,464858057 | 3,76813E-12 |
| Summa parameter | 0,911645564 | | |

En regression med total ledningslängd visar hög signifikans. När denna variabel delas upp i kategorierna luft- och jordledning, blir jordledning inte signifikant. Den estimerade parametern för uttag visar att en ökning av uttag med en procent i genomsnitt ökar de operativa kostnaderna med 0,68 procent. Summeringen av estimaten visar på vissa stordriftsfördelar (positiv skalekonomi) med ett värde på 0,91 vilket innebär att en ökning av verksamheten i form av de ingående variablerna med en procent ger en kostnadsökning med 0,91 %.

I en modell där man försöker fånga icke-linjära kostnadssamband och kostnadsinteraktioner (translogaritmisk skattning), är ledning och uttag de variabler som är signifikanta. I estimeringen vars resultat återges i Tabell 3 är det uttag och ledning som är signifikant (gulmarkerade). Av övriga variabler är uttag 2 svagt signifikant (klarar 10 %-nivån) och parametervärdet indikerar att kostnaderna ökar med ökade uttagsvolymer, dvs. marginalkostnaden för att ansluta ytterligare kunder ökar successivt, dvs. att det inte finns några skalfördelar i verksamheten, se Tabell 3.

Parametervärdena är estimerade för medelföretaget, vilket gör att det går att avläsa dessa som gällande för ett genomsnittligt företag. Det innebär att för företag som avviker från medel (litet eller stort), eller med en avvikande mix av de ingående variablerna, kommer den marginella kostnaden att skilja sig åt. För nät med hög kundtäthet blir marginalkostnaden för uttag högre jämfört med nät med låg kundtäthet.

I estimeringen av modellen (Tabell 3) utgör den linjära komponenten 0,48 men beräknat på nät med hög kundtäthet (som också är relativt stora nät med många uttag/kunder) blir marginalkostnaden 0,75 när interaktioner och verksamhetsnivåer påverkar marginalkostnaden.

#### Tabell 3 – Estimering av translog modell år 2011

Regressionsstatistik (År 2011): Multipel-R = 0,986371051; R-kvadrat = 0,97292785; Justerad R-kvadrat = 0,971303521 (97 %); Standardfel = 0,234420003; Observationer = 160. (Gulmarkerade/signifikanta för medelföretaget: ledning, uttag. Rödmarkerade/ej signifikanta i källan.)

| Variabel | Koefficienter | t-kvot | p-värde |
|---|---|---|---|
| Konstant | −0,016505706 | −0,617817312 | 0,537632624 |
| ledning | 0,317638563 | 6,41840876 | 1,70833E-09 |
| Kva | 0,165647473 | 1,556903629 | 0,121600746 |
| uttag | 0,480093959 | 5,45066533 | 2,0164E-07 |
| ledning2 | 0,062199475 | 0,324106232 | 0,746309101 |
| Kva2 | 0,441517591 | 0,96189536 | 0,33765021 |
| uttag2 | 0,778186345 | 1,830114616 | 0,06921787 |
| ledning*trafo | 0,214654752 | 0,95908116 | 0,339061209 |
| ledning*abonnent | −0,278309323 | −1,599812227 | 0,111744396 |
| trafo*abonnent | −0,585361438 | −1,434880643 | 0,153402831 |

Ett alternativ till att avbilda nätet med ledningslängd och installerad transformatorkapacitet är att beräkna en kapitalkostnad (CAPEX) med kapitalbasen som utgångspunkt. I estimeringen i Tabell 4 ingår en CAPEX-variabel beräknat utifrån återanskaffningsvärdet (NUAK), dvs. någon åldersjustering finns inte med. Detta gör att skattningen sannolikt inte blir rättvisande då ett nät som är äldre med högre underhållskostnader (OPEX) i beräkningen inte blir kompenserade med lägre CAPEX i det här fallet.

Att ha med en kapitalkostnad, beräknat med hänsyn till ålder (bruksvärdet), innebär att det finns en principiell koppling mellan ett äldre nät (med högre underhållskostnad) men lägre kapitalkostnad och ett yngre nät med högre kapitalkostnad och lägre underhållskostnader.

#### Tabell 4 – Translogaritmiska skattning av modell med två oberoende variabler år 2011

Regressionsstatistik (År 2011, translog; beroende variabel OPEX_1; oberoende: uttag, CAPEX): Multiple R = 0,97838027; R Square = 0,957227952; Adjusted R Square = 0,955839249 (96 %); Standard Error = 0,27616717; Observations = 160. (Gulmarkerade/signifikanta: uttag, CAPEX, CAPEX*CAPEX/2.)

| Variabel | Coefficients | t Stat | P-value |
|---|---|---|---|
| Intercept | 0,020386265 | 0,684384879 | 0,494760801 |
| uttag | 0,759373049 | 17,71927428 | 5,30763E-39 |
| CAPEX | 0,159300635 | 3,628783014 | 0,000386868 |
| uttag*uttag/2 | −0,003084182 | −0,167975386 | 0,866823037 |
| CAPEX*CAPEX/2 | 0,083747932 | 3,082683166 | 0,002431384 |
| uttag*CAPEX | −0,027647757 | −1,592603605 | 0,113299649 |

De gulmarkerade estimaten är signifikanta. För medelföretaget anger den att en ökning av kapitalkostnader med 1 procent ger en ökning av operativa kostnader med 0,16 procent. Den totala marginaleffekten (där övriga estimat ingår) för uttag blir för medelföretaget 0,68 resp. 0,22 för CAPEX, se Tabell 5. Det blir således lägre för uttag och högre för CAPEX när interaktion och olinjära samband ingår. I Figur 7 är marginaleffekterna inlagd (med blått för uttag och orange för CAPEX). Av figuren verkar det inte finns något tydligt mönster m a p kundtäthet. Marginaleffekterna varierar dock en del mellan företagen och jämför man de 10 % av företagen med högst resp. lägst kundtäthet med genomsnittsvärdet för alla företag, finns det ändå skillnader.

#### Tabell 5 – Marginaleffekter för nät med olika kundtäthet

| Företagsgrupp | Marginaleffekt uttag | Marginaleffekt CAPEX |
|---|---|---|
| Låg kundtäthet, 16 nät | 0,62 | 0,30 |
| Medelvärde, 160 nät | 0,68 | 0,22 |
| Högst kundtäthet, 16 nät | 0,72 | 0,19 |

Skillnaden för uttagen mellan nät med låg respektive hög kundtäthet är 0,10 för uttag resp. 0,11 för CAPEX. Nät med hög kundtäthet tycks således ha en högre kostnad per kund på marginalen jämfört med glesbygdsnät. Medan motsatsen gäller för kapitalet. Mer kapital per kund med hög andel luftledning ger höga underhållskostnader relativt sett.

#### Figur 7 – Marginaleffekter för uttag och CAPEX (blå=uttag och röd=CAPEX) för resp. nätföretag

Diagram (spridning), "Marginaleffekt per företag mot kundtäthet – translog uttags- och CAPEX-modell år 2011". Y-axel: marginaleffekt 0 till 1. X-axel: kundtäthet 0 till 350 (meter/uttag). Två serier: Serie1 (uttag, blå) och Serie2 (CAPEX, röd). Inget tydligt mönster mot kundtäthet framträder.

Frågan är hur faktorn kundtäthet ska modelleras för att fånga upp den kostnadsdrivande effekten? Det naturliga är att både ha med ledningsländ och antal uttag som produkter då de implicit bör fånga upp täthetsfaktorn. Frågan är dock om det inte behövs en särskild variabel för detta och ett sätt är att lägga in en kvotvariabel (meter/uttag) som en sådan extra restriktion för att mer rättvist jämföra nät i tätort relativt landsbygd.

Generellt visar regressionsanalyserna (även inkluderande panelregressionerna och SFA på paneldata) att:

- Flera olika modeller ger hög förklaringsgrad och signifikanser, t ex OPEX_1 mot överförd el (lågspänning)
- Svårt att hitta en tydlig bästa modell
- Luftledning är signifikant (påverkar underhållskostnaderna), men ger negativa resultat på produktivitetsutveckling då luftledningar har minskat i volym över åren
- Uttag är den mest signifikanta variabeln i alla modeller (där den ingår)

### DEA-resultat på grundmodellen

Resultaten visar på stora potentialer, särskilt vid antagande om konstant skalavkastning (CRS), dvs. när särskild hänsyn till verksamhetens nivå inte tas. För de fyra åren 2006-2009 beräknas medeleffektiviteten till 68 %, dvs. en potential på drygt 30 % för medelföretaget. Resultaten för varje företag är beräknat för de fyra åren både vid CRS- och VRS-antagande. Av Figur 8 framgår att det företrädesvis är de mindre företagen som har största potentialerna.

#### Figur 8 – Medeleffektivitet åren 2006-2009 D4-modell OPEX

Diagram (spridning), "Medeleffektivitet 2006-2009: medel av CRS och VRS". Y-axel: medeleffektivitet 0,0 till 1,0. X-axel: marknadsandel 0,0 till 1,0. Visar att de mindre företagen (låg marknadsandel) har störst spridning och de största potentialerna.

Resultat: översikt över de fyra åren 2006-2009:

- Med antagande om konstant skalavkastning blir potentialen ca 30 %, exklusive extremvärden.
- De minsta företagen får antingen höga eller mycket låga potentialer beroende på skalantagande.
- Få förebildsföretag vid konstant skalavkastning och liten modell
- Lägst potential (flest fullt effektiva) vid antagande om varierande skalavkastning och med fler kostnadsdrivare.

### Panelresultaten på grundmodellen

De två konsulterna gjorde sitt arbete parallellt. Dels har beräkningar gjorts med genomsnittliga samband (panelregressioner), dels med SFA på den valda grundmodellen.[^35] Dessutom har även DEA beräkningar med Malmquistindex gjorts för att visa på produktivitetsutvecklingen mellan 2004-2012. Resultaten visar generellt att för en stokastisk modell fungerade loglinjär modell med fixa effekter bäst även om det förekommer lite problem med identifiering vilket troligen beror på att förklaringsvariablerna har för liten variation över tiden. Random effect (RE)-modellen fungerar mindre väl och kunde förkastas. Loglinjär och translog ger likartade resultat.

När DEA och SFA tillämpats på samma material (grundmodellen) är skillnaden i effektivitet stor. I både loglinjär och translog med fixa effekter beräknas effektiviteten till 6 % som medelvärde, medan motsvarande för DEA ligger på 27 %. Denna skillnad indikerar att alternativa modeller bör övervägas.

### Produktivitetsutveckling D4(1+4) OPEX-modell

I den modell som innehåll luftledningar som en kostnadsdrivare visade panelen för åren 2004-2012 en negativ utveckling. Både vid tillämpning av parametrisk (SFA) som icke-parametrisk ansats (DEA). Detta beror på de omfattande investeringar som gjorts för att gå över från luftledningar till jordkabel.[^36] Därför prövas en modell där alla ledningar ingår i modellen. Om man ser på utvecklingen av de ingående variablerna så minskar kostnaderna realt med 7,4 % (indexerat med faktorprisindex för elnätsföretag). Antal uttag ökade med 2,7 %, installerade transformatorkapacitet med 12 % och ledningslängden ökade med 8,2 %. Om dessa volymer vägs samman med parametervärden från en loglinjär regressionsmodell (vikterna 0,66; 0,17 resp. 0,09) ger detta en volymökning på 12,3 %. Det ger sammantaget en produktivitetsökning på 1,6 % per år för branschen.

Med DEA-beräkningar på samma data där resultaten räknas fram som ett s.k. Malmquistindex, blir den årliga genomsnittliga förändringen samma resultat: 1,6 % per år. Spridningen kring detta medelvärde är mycket hög. Från minus 54 % till plus 146 %.[^37] Även om man jämför första och tredje kvartilvärdena så är spridningen stor. Från minus 5,1 % till plus 23,5 %.

Vägt med antalet uttag blir utvecklingen lite högre: 2,0 % per år. Även en loglinjär modell i en SFA-beräkning ger samma resultat som DEA: 1,6 % per år.

Dessa resultat ligger på ungefär samma nivå som många andra studier över produktivitetsutvecklingen. I tabell 15 avsnitt 8.1 redovisas utvecklingen av totalfaktorproduktiviteten för 20 olika studier som omfattar tiden så långt tillbaka som tidigt 70-tal till en bit in på 2000-talet. Medelvärdet för dessa studier är 2,7 % ökning per år.

I en tidigare beräkning med data för åren 2000-2011 med samma modell där utvecklingen analyserades före varje enskilt år beräknades medel för utvecklingen över åren till 1,8 %. Mätt direkt mellan 2000 och 2011 beräknades utvecklingen till 1,6 %. Det som kännetecknar utvecklingen i denna modell är att utvecklingen av produktiviteten varierar avsevärt mellan åren. Från - 4,8 % till + 8,5 %. Variationen i produkterna är relativt liten, så det är variationerna i kostnaderna som förklarar skillnaderna i utvecklingen. Resultaten visar tydligt att jämförelser av enskilda år ger alltför stor osäkerhet kring på beräkning av effektivitetsfördelningen och utvecklingen av produktiviteten. Detta har också noterats av flera regleringsmyndigheter i andra länder. För att bestämma fronten för jämförelsen används genomsnittdata över flera år.

### Val av modell

Den grundmodell som undersökts var fokuserad på att fånga kostnadssambandet mellan operativa kostnader och de mest tydliga kostnadsdrivarna. Problemet med denna modell är att den endast skär ut en del av verksamheten. Kostnadsposter som nätförluster, kostnad för överliggande nät och kapitalkostnader lämnas utanför. En reglering med en sådan inriktning riskerar (särskilt på längre sikt) att få skevheter i resursmixen. I valet mellan att underhålla ett existerande äldre nät och investera i nytt, kan valet lätt leda till onödigt tidig förnyelse av nätet. Resursallokeringen riskerar att bli felaktig i förhållande till verkliga priser på använda resurser.

Det ideala på sikt är att ha en reglering där måttstockskonkurrensen bygger på alla verksamhetens kostnader och att dessa relateras till den produktion som nätet utför. Det innebär att sambandet mellan verksamhetens kostnader och utförda tjänster bör ingå i modellen, där tjänsterna är sådant som kunden värderar positivt: att vara ansluten med möjlighet att ta ut viss effekt när kunden så önskar, att få leverans av en valfri volym av elenergi och att inte få avbrott i leveransen.

Det är inte enbart verksamhetens produkter som genererar kostnader, utan även faktorer som företagen inte producerar påverkar kostnaderna, såsom geografi, geologi och klimat. Sådana faktorer bör också kunna ingå i modellen för jämförelsen.

För att få hög tillförlitlighet i kraven krävs en noggrann granskning av ingående variabler, dvs. dataunderlaget. Eftersom de metoder som finns tillgängliga har lite olika egenskaper, är det också av betydelse för tillförlitligheten att fler metoder används. Ei har här valt DEA och SFA för att öka säkerheter i beräkningen av potentialerna. Ett sätt att mer direkt fånga upp kostnadsskillnader som beror av kundtätheten kan en kvotvariabel som antal meter/uttag i området användas. Glesbygd innebär betydligt mer ledning per uttag (men även andra nätkomponenter). Genom att ha en sådan variabel kommer hänsyn till kundtätheten att fångas upp helt eller delvis. I en modell med anal uttag och ledningslängd som separata variabler fångas kundtätheten upp indirekt. Frågan är om den gör det i tillräcklig hög utsträckning om sambandet inte är linjärt.

Två nya alternativa modeller formuleras. OPEX-modellen minimerar den operativa kostnaden (påverkbara) relativt produktionen av fyra produkter (antal uttag, max effektuttag mot överliggande nät, samt överförd elenergi uppdelat på låg- resp. högspänningsel) samt att kapitalkostnader resp. övriga operativa kostnader ingår som restriktioner – inte variabler som ska minimeras. Beteckningen för modellen är D7(1+2+4), där 7 är antalet variabler, 2 de två kostnadsposter som inte minimeras men som fungerar som variabler för att jämföra nät med ungefär liknande kapitalkostnad resp. övriga operativa kostnader. TOTEX-modellen har samma variabler och mäter den mer långsiktiga effektiviseringspotentialen. I denna modell D7(3+4) minimeras de tre kostnadsposterna proportionellt relativt de fyra produkterna. I denna modell minimeras alla kostnader fast uppdelade i tre separata poster.

#### Figur 9 – Principen för minimering i DEA för delminimering och totalminimering

Principskiss (axlar: OPEX vertikalt, CAPEX horisontellt). Företag A jämförs mot fronten.

- **TOTEX:** minimering av båda posterna proportionellt mot origo tills fronten nås (punkt B). Effektivitet = AB/AO.
- **OPEX:** minimering av OPEX givet CAPEX (vertikal minskning till punkt C/D). Effektivitet = Acc/Ad (AC/AD).

I figur 9 kan en minimering av kostnader ske givet produktion och där båda kostnaderna minskas proportionellt tills minimeringen når fronten (B) och där kvoten AB/AO ger ett mått på kostnadseffektiviteten. En minimering kan också ske genom att man håller kostnaden för kapital konstant. Minskningen sker då vertikalt till fronten nås (C) och måttet på kostnadseffektivitet blir AC/AD.

### Utökad modell

Grundmodellen med OPEX och få kostnadsdrivare (de mest signifikanta) ger som resultat relativt låga effektivitetstal, särskilt om DEA-resultaten jämförs med SFA-resultaten från konsulternas arbete. Att använda modellen över tiden visade på en tydlig produktivitetsnedgång beroende på att luftledningar minskat och kabel ökat. En utökad modell prövas därför med motivering i följande:

- Tydligt samband mellan operativ kostnad och uttag
- Kapitalkostnad har samband med uttag
- Nätförluster och överliggande nät med samband till dels max effekt mot överliggande och överförd el, särskilt lågspänningsel
- Kapitalkostnad (real linjär) har samband mot OPEX, dvs. äldre nät med lägre CAPEX ger högre OPEX i form av underhåll och reparationer
- Uttagstäthet som en extra variabel för att fånga in dimensionen land-stad, vilket innebär att nät med ungefär samma uttagstäthet kommer att jämföras i större utsträckning genom att de är mer lika

### Modell – OPEX D7 (1+2+4)

Denna modell har prövats på år 2011. Valet av 2011 beror på att det finns data över kapitalbasen i form av återanskaffningsvärden (NUAK). Från denna bas har en årliga kapitalkostnad beräknats med en ränta (5,2 %) och 40 års avskrivningstid. Omräkningen görs för att få ungefär samma nivå på beloppen eftersom kapitalbasen är så mycket högre än de operativa kostnaderna. Beräkningarna kommer att troligen att underskatta inverkan av CAPEX eftersom den inte är åldersberäknad. Data över en åldersberäknad kapitalbas saknas för närvarande. Först i samband med ansökningarna för ny intäktsram i mars 2015 kommer den sådan att finnas tillgänglig för analys.

I regressionen som redovisas i Tabell 6 har de operativa kostnaderna ställts mot de fyra produkterna samt CAPEX-variabeln för år 2011. Den visar hög signifikans och inverkan på uttagsvariabeln. Överförd el och CAPEX är inte signifikanta. Det är naturligt för överförd el då nätförlusterna inte ingår i kostnaderna. För CAPEX-variabeln är förklaringen den att den bygger på NUAK utan åldersbestämning. Med en åldersbestämning får man ett bruksvärde som ger en kapitalbas som bättre stämmer med kostnadsvariabeln för CAPEX.

#### Tabell 6 – Regression operativ kostnad år 2011 med 5 oberoende variabler

Regressionsstatistik (År 2011, OPEX_1 mot: kunder, max effekt ÖN, El_låg, El_hög, CAPEX; CAPEX beräknad 40 år, 5,2 % och 1/2-g): Multiple R = 0,977989747; R Square = 0,956463946; Adjusted R Square = 0,955050438 (96 %); Standard Error = 0,278622741; Observations = 160.

| Variabel | Coefficients | t Stat | P-value |
|---|---|---|---|
| Intercept | 2,198577004 | 5,332947218 | 3,38764E-07 |
| uttagspunkter | 0,702942123 | 12,28856885 | 1,27164E-24 |
| max effekt | 0,169800792 | 2,415199538 | 0,016898104 |
| el låg | 0,010198721 | 0,302346383 | 0,762795988 |
| el hög | −0,008258383 | −0,8681792 | 0,386647147 |
| CAPEX | 0,041168448 | 1,235551013 | 0,218506994 |
| summa | 0,9158517 | | |

Endast uttagspunkter och max effekt signifikanta; max effekt klarar 5 % medan uttagspunkter har mycket högt t-värde; el hög har t o m negativt tecken.

I Tabell 7 redovisas centralvärden och spridning för OPEX-modellen givet konstant resp. varierande skalavkastning (CRS resp. VRS). Medelvärdet visar på en genomsnittlig effektiviseringspotential på 36 % vid CRS och 30 % vid VRS. Antalet fullt effektiva företag vid VRS blir stor (med kvartil 4 på 100 %, dvs. ¼ av företagen eller 46 st).

#### Tabell 7 – OPEX-modell D7(1+2+4) år 2011

| D7(1+2+4) | CRS | VRS |
|---|---|---|
| Min | 19,0 % | 26,0 % |
| Max | 100,0 % | 100,0 % |
| Medel | 63,9 % | 70,1 % |
| Median | 58,0 % | 64,5 % |
| Q75 | 84,5 % | 100,0 % |
| Q25 | 47,0 % | 50,0 % |

Den beräknade effektiviseringspotentialen ligger i genomsnitt på drygt 30 %. Spridningen är stor med ett antal nät med låga mätetal och relativt många företag med full eller nästan full kostnadseffektivitet. Antalet fullt effektiva företag vid VRS är 46 st och vid CRS 31 st. Medianvärdena ligger generellt under medelvärdena, vilket visar att på profilen på fördelningen är utdragen vid de lägre mätetalen.

Det verkar som att en OPEX-modell med två kostnadsrestriktioner för CAPEX och s.k. opåverkbara OPEX ger i stort sett samma resultat både vad gäller rangordning och beräknade effektiviseringspotentialer med en OPEX-modell där övriga kostnader inte beaktas. Den OPEX-modell D6(1+5) som avskärmar övriga kostnader ger en medeleffektivitet på 75,7 % år 2009 medan modellen då övriga kostnader ingår (D8(1+2+5) ger en medeleffektivitet på 77,5 %.

### Varför totalkostnader (TOTEX) och konstant skalavkastning (CRS)?

Att enbart mäta (minimera) påverkbar OPEX enligt Ei:s definition, innebär att det kan ske en ökning i de andra kostnaderna (utan att effektiviteteten inte påverkas eftersom de inte ingår i minimeringen), dvs. en substitution mellan kostnadsslag som motiveras av en regel och inte efter vad som är en optimal kombination av olika resurser (givet faktiska priser). Denna ökning beror på regleringen och inte på realekonomiska förhållanden. En TOTEX-minimering är det ideala då alla kostnader ställs mot prestationerna (produktion och yttre ramvillkor) för att undvika s.k. suboptimering. För att få en mer rättvisande jämförelser av företag som har olika andelar av de olika kostnadsposterna bör alla kostnader ingå. TOTEX används i Norge av Norges vassdrags- og energidirektorat (NVE)[^38] och TOTEX-beräkningar blir mer stabila över åren jämfört med OPEXp.

Att använda CRS som norm innebär en jämförelsekonkurrens alla mot alla oberoende av storlek. Det bakomliggande antagande är att produktionen kännetecknas av konstant skalavkastning. Vid både regressionsanalys och mätning av skaleffektivitet i DEA, visar resultaten att det att det finns vissa stordriftsfördelar (en procents ökning av produktion ger ökningar i OPEX på ca 0,95 procent är ett vanligt resultat).

Om dagens struktur på nätföretagen anses given och inte ska ändras är det mer motiverat att använda VRS (varierande skalavkastning) eller NDRS (icke-avtagande skalavkastning) som norm. Ett litet företag kommer då att få högre effektivitet jämfört med större. Om denna struktur av olika skäl inte ska betraktas som given, är det mer motiverat att använda CRS som norm.

**Aggregering av kostnaderna?** En fråga är om TOTEX ska ingå i minimeringen som en summerad post eller om det ska vara tre delposter. I ett regleringsperspektiv är en aggregering att föredra då det ger full frihet för företagen att kombinera posterna, medan i ett företagsledningsperspektiv får företagen mer värdefull information med tre uppdelade poster. De kan genom simuleringar testa vilken post som ger störst utslag när det gäller förbättringar. Företag med udda mix av de tre posterna kommer att framstå som mer effektiva jämfört med om det endast en kostnadspost ingår i jämförelsen.

En aggregering till en enda post innebär implicit ett antagande att det är lätt att byta kostnadsslag, vilket kan vara ett rimligt antagande på lång sikt då företagen då kan välja teknik vid investeringar. Vid uppdelning i tre poster antages att proportionerna är fixa (när man räknar), dvs. minimeringen sker proportionellt lika mycket i % av respektive kostnadspost.

Med ett långsiktigt perspektiv är en aggregering till fördel som regleringsmodell. Frågan är om vårt perspektiv på 4-8 år kan betraktas som långt?

Ett ytterligare motiv för en uppdelning i tre poster är att beräkningen ger information om vilka poster det är mest angeläget att minska för att "komma bättre ut" – bli effektivare relativt övriga företag.

### Modell – TOTEX D7 (3+4)

Skillnaden mot föregående modell är att minimeringen sker på totalkostnader uppdelade i tre poster och där de minskas proportionellt, se Tabell 8.

#### Tabell 8 – TOTEX-modell D7(3+4) år 2011

| D7(3+4) | CRS | VRS |
|---|---|---|
| Min | 38,0 % | 39,0 % |
| Max | 100,0 % | 100,0 % |
| Medel | 78,8 % | 83,0 % |
| Median | 78,0 % | 83,0 % |
| Q75 | 94,0 % | 100,0 % |
| Q25 | 68,0 % | 72,0 % |

### Resultat D7-modellerna – översikt

I Tabell 9 visas en översikt av resultaten. Kostnadseffektiviteten är lägst för OPEX-modellen med CRS och högst vid VRS i TOTEX-modellen. Ett medel på de fyra medelvärdena anger en genomsnittlig potential på 26 % för de fyra modellerna. Effektiviseringspotentialen i TOTEX är lägre räknat i procent, men i kronor blir det högre om procenten appliceras på totalkostnaderna. Det är dock lite förvånande att OPEX-modellen ger högre effektiviseringspotentialer vid OPEX jämfört med TOTEX. I OPEX-modellen minimeras endast påverkbar OPEX, medan de två övriga kostnadsposterna endast ingår som restriktioner för att göra jämförelsen mer rättvisande, t ex mycket kapital per kund i glesbygd. Antalet nät som "konkurrerar med varandra" bör bli lägre och därmed bör mätetalen på effektivitet bli högre. TOTEX-mätningen ska ju tolkas som potentialen på lång sikt när det är möjligt att göra större ändringar i kapitalbasen, minska fysiska nätförluster respektive kostnaden mot överliggande nät.

#### Tabell 9 – Översikt OPEX- och TOTEX-modell år 2011

(Källans rubrik anger "år 2001"; avser år 2011.)

| | OPEX CRS | TOTEX CRS | OPEX VRS | TOTEX VRS |
|---|---|---|---|---|
| Min | 19,0 % | 38,0 % | 26,0 % | 39,0 % |
| Max | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| Medel | 63,9 % | 78,8 % | 70,1 % | 83,0 % |
| Median | 58,0 % | 78,0 % | 64,5 % | 83,0 % |
| Q75 | 84,5 % | 94,0 % | 100,0 % | 100,0 % |
| Q25 | 47,0 % | 68,0 % | 50,0 % | 72,0 % |

I Figur 10 visas hur näten placerar sig i OPEX resp. TOTEX vid CRS. I figuren syns inte att många företag finns vid 100 %. Mätetalen för TOTEX ligger alla över OPEX. Effekten av att ha med två kostnadsvariabler (mer på kort sikt opåverkbara kostnader) som inte minimeras i modellen ger i stort sett samma resultat som grundmodellen. Korrelationen uppgår till 0,88. Skillnaden mellan de två modellerna är större för de lägre mätetalen på effektivitet.

Ett sätt att fånga upp kostnader som beror på låg kundtäthet är att lägga in en särskild täthetsvariabel. En modell där kundtätheten läggs in som en direkt kvotvariabel (meter per uttag) som ytterligare en restriktion i modellen som inte minimeras. Det innebär att variablerna CAPEX och operativa opåverkbara kompletteras med ytterligare en restriktion: kundtäthet (meter/uttagspunkt).

Företag med mätetal på effektivitet på över 80 % i TOTEX-modellen får mätetal på effektivitet som är mindre än 40 % i OPEX-modellen. Skillnaderna i OPEX mellan företagen för given produktion är större än skillnaderna i TOTEX-kostnaderna. Det förklaras sannolikt av att OPEX-posten varierar betydligt över åren och då i ett mönster som inte är lika för företagen. Vissa år har ett företag en större underhållsinsats som inte är med nästa år, medan ett annat företag gör sina särskilda underhållsinsatser detta år. Detta leder till stor variation i OPEX. Till dessa reala förhållanden kan även läggas att skilda redovisningsprinciper och hur redovisningen fördelar kostnader mellan investering och underhåll leder till att denna variation i OPEX, både mellan företagen och över åren i samma företag stör effektivitetsberäkningen. Ett sätt att reducera denna störning är dels att använda data över flera år och ta medel för dessa år som ingångsdata vid beräkningen. Ett annat sätt är att räkna på TOTEX-modellen då det finns en koppling mellan underhållskostnader och kapitalkostnader, särskilt om kapitalkostnaderna beräknas med hänsyn till åldern på respektive anläggning.

#### Figur 10 – Kostnadseffektivitet i OPEX resp. TOTEX vid konstant skalavkastning (CRS) år 2011

Diagram (spridning), "D7 TOTEX 3+4 OPEXsubvektor – TOTEX år 2011". Vertikal axel: TOTEX-modell med tre separata kostnadsvariabler och fyra kostnadsdrivare (0 till 120 %). Horisontell axel: OPEX-modell med två kostnadsposter som restriktioner (0 till 120 %). Korrelation: 0,88. Mätetalen för TOTEX ligger genomgående över motsvarande OPEX-värden.

### Behövs en extra täthetsvariabel?

Ett implicit sätt att fånga upp kundtätheten och de skillnader i kostnader som detta ger upphov till är att kostnadsdrivarna (produkterna) antal kunder och ledningslängd ingår i modellen. De gjorda analyserna tyder dock på att de högre kostnaderna vid låg kundtäthet inte fångas upp tillräckligt med att ha med dessa två produkter i modellen. Det finns flera sätt att hantera detta. Ett är att dela in företagen i grupper och göra delanalyser, dvs. stadsnät jämförs mot andra stadsnät och landsbygd med andra landsbygd. Nackdelen är att det då blir mindre konkurrens i varje enskild grupp även om de är inom varje grupp är mer lika med avseende på kundtäthet. Frågan uppstår då i hur många grupper som företagen ska delas upp i och var gränserna ska gå.

Ett enklare förfarande är att lägga till en särskild täthetsvariabel. Antingen direkt genom att låta kundtätheten ingå som en variabel, eller genom att använd någon volymvariabel över verksamheten som är starkt korrelerad till kundtätheten. Två sådana kandidater är längden på luftledningar respektive antalet nätstationer. Andelen luftledningar av total ledningslängd är hög i landsbygds- och glesbygdsnät. Antalet små nätstationer är också högt i sådana nät. Alla tre varianter kommer att undersökas.

Kvotvariabeln meter per uttagspunkt har lagts in i D7-modellerna och blir därmed en D8-modell. Mätetalen för kostnadseffektivitet i D7-variblerna har relaterats till denna kundtäthetsvariabel i en enkel regression. Båda dessa regressioner visar ett signifikant samband som indikerar att kundtäthet påverkar mätetalen för effektivitet. I tabell x och y redovisas dessa. Regressionerna förklarar 26 % resp. 35 % av variationen i mätetalen med täthetsvariabeln. I OPEX-modellen anger resultaten att en 10 % lägre kundtäthet innebär 2,3 % enheter lägre kostnadseffektivitet. För TOTEX-modellen estimeras motsvarande värde till 1,8 % enheter.

#### Tabell 10 – OPEX-modell (CRS), resultat mot kundtäthet år 2011

Modell: D7(1+2+4) = f(meter/uttag). Förklarar kundtäthet variationen i effektivitet? Adjusted R Square = 0,261938451 (26 %).

| Post | Värde | Kommentar |
|---|---|---|
| Intercept (Coefficient) | 0,86834 | t Stat 25,4121 |
| meter/uttag (Coefficient) | −0,00215 | t Stat −7,5782 |
| medel skattad | 0,6389 | |
| min | 0,8197 | högst täthet |
| max | 0,1553 | lägst täthet |
| linjärt | 0,6160 | 10 % lägre kundtäthet från medel |
| förändring | −0,0229 | 10 % lägre kundtäthet ger 2,3 %-enheter lägre effektivitet |

#### Tabell 11 – TOTEX-modell (CRS), resultat mot kundtäthet år 2011

Modell: D7(3+4) = f(meter/uttag), TOTEX. Förklarar kundtäthet variationen i effektivitet? Adjusted R Square = 0,35395502 (35 %).

| Post | Värde | Kommentar |
|---|---|---|
| Intercept (Coefficient) | 0,96733 | t Stat 44,84021 |
| meter/uttag (Coefficient) | −0,00168 | t Stat −9,38685 |
| medel skattad | 0,7879 | |
| min | 0,9293 | högst täthet |
| max | 0,4097 | lägst täthet |
| linjärt | 0,7700 | 10 % lägre kundtäthet från medel |
| förändring | −0,0179 | 10 % lägre kundtäthet ger 1,8 %-enheter lägre effektivitet |

Skillnaden i genomsnittlig kostnadseffektivitet mellan D7- och D8-modellen är liten. Effektiviteten ökar med endast 1,1 procentenhet (från 63,9 % till 65,0 %). Skillnaden i resultat tycks inte heller variera mellan företag av olika kundtäthet. I Tabell 11 [Tabell 12] har skillnaden i modellernas resultat jämförts för olika täthetsgrupper av företag. För kvartilen av nät med högst kundtäthet är skillnaden mellan modellerna 1,9 procentenheter i genomsnitt. För kvartilen med lägst kundtäthet var skillnaden 0,4 procentenheter. Det verkar av Tabell 11 [Tabell 12] som att det inte finns något mönster i skillnaderna. Det finns inget signifikant samband mellan skillnaden i effektivitet mellan modellerna och kundtätheten. Det tyder på att kvotvariabeln inte verkar fungera som en kompensation för låg kundtäthet.

Ett alternativ är att låta täthetsvariabeln ingå som en produkt, dvs. på outputsidan av modellen. Luftledning har visat sig vara starkt signifikant mot OPEX-kostnaden. Det är en variabel som minskat i andel, men för en del företag med mycket distribution på landsbygden är andelen fortfarande hög. Den kan också förväntas vara hög även fortsättningsvis. Därför prövas ytterligare en modell där de fyra produktvariablerna kompletteras med luftledningslängden som då ses som en enskilda separat prestation.

#### Tabell 12 – Skillnad mellan modellerna D7 och D8 (CRS) i olika täthetsintervaller år 2011

| Täthetsmått | Täthet (meter/uttag) | %-enheter skillnad mellan D8 och D7 | Medel för nät |
|---|---|---|---|
| Kvartil 1 | 63 | 1,9 % | 1–25 % |
| Median | 94 | 0,7 % | 25–50 % |
| | | 1,6 % | 50–75 % |
| Kvartil 3 | 139 | 0,4 % | 75–100 % |

### D8-modeller

I Tabell 13 redovisas resultaten från år 2011 då även luftledning ingår som en produkt för att särskilt ta hänsyn till täthetsfaktorn. Effektiviteten ökar markant när kvotvariabeln för kundtäthet ersätts med luftledning som produkt. Medelvärdet på kostnadseffektivitet för de fyra modellerna blir 82,2 % dvs. en genomsnittlig potential på knappt 18 %. TOTEX-modellerna ger som tidigare högre effektivitet. Ökningen i effektivitet vid CRS jämfört med VRS blir relativt blygsam (2,6 resp. 2,3 procentenheter). Antalet fullt effektiva företag ökar från 48 till 56 vilket innebär att antalet effektiva nät ligger på drygt 1/3.

#### Tabell 13 – D8-modeller år 2011

| | OPEX D8(1+2+5) CRS | OPEX D8(1+2+5) VRS | TOTEX D8(3+5) CRS | TOTEX D8(3+5) VRS | Medel |
|---|---|---|---|---|---|
| Min | 36,0 % | 38,0 % | 47,0 % | 64,0 % | 52,0 % |
| Medel | 76,2 % | 78,8 % | 85,8 % | 88,1 % | 82,2 % |
| Antal 100 % | 48 | 56 | 50 | 56 | |
| Andel | 30,0 % | 35,0 % | 31,3 % | 35,0 % | |

Den genomsnittliga nivån på kostnadseffektiviteten vid TOTEX-modellen ligger ca 10 procentenheter högre jämfört med OPEX. Antalet fullt effektiva företag blir relativt högt med drygt en tredjedel fullt effektiva vid VRS.

I Tabell 14 redovisas resultat för både OPEX- och TOTEX-modeller med luftledning respektive nätstationer som täthetsvariabel. Den redovisar också alternativet då kostnaderna aggregerats till en post (D6(1+5) TOTEX respektive OPEX-modell utan övriga kostnader (som restriktioner).

#### Tabell 14 – Översikt av olika modeller för år 2009

(CRS-modeller. Täthetsvariabel anges per kolumn: luftledning eller stationer; "aggregerad" = D6(1+5) med kostnaderna aggregerade till en post; "bara OPEX" = OPEX-modell utan övriga kostnader.)

| År 2009 | TOTEX D8(3+5) luftledning | TOTEX D6(1+5) stationer (aggregerad) | OPEX D8(1+2+5) luftledning | OPEX stationer | OPEX D6(1+5) stationer (bara OPEX) |
|---|---|---|---|---|---|
| Min | 46 % | 54 % | 28 % | 15 % | 28 % |
| Max | 100 % | 100 % | 100 % | 100 % | 100 % |
| Medel | 84 % | 90 % | 75 % | 78 % | 76 % |
| Median | 85 % | 93 % | 74 % | 77 % | 76 % |
| Q75 | 100 % | 100 % | 85 % | 100 % | 86 % |
| Q25 | 74 % | 82 % | 64 % | 63 % | 65 % |
| Antal 100 % | 47 | 52 | 12 | 40 | 16 |
| Andel | 31 % | 34 % | 7 % | 26 % | 10 % |

I den modell där bara påverkbara OPEX-kostnader ingår är medeleffektiviteten 76 % och den ökar endast till 78 % när de två övriga kostnadsposterna ingår som restriktioner. När det gäller täthetskompensationen ger stationer som täthetsvariabel en högre effektivitet (90 %) i medel jämfört med luftledning (84 %). Det är då främst nätföretag med många stationer jämfört med övriga variabler som gynnas i en sådan modell. I en enkel regression där mätetalen på effektivitet i D8(3+5) relateras till täthetsvariabeln förklarar variationen i täthet (meter/uttag) förklara endast 1,7 % av variationen i mätetal. I figur 11 visas detta. Sambandet är svagt men signifikant och indikerar att stationer som täthetsvariabel inte kan förklara täthetsskillnader fullt ut. Om det vore så borde sambandet inte varit signifikant (5 %-nivån). Jämfört med luftledning förklarar stationsvariabeln mer av skillnaderna i kundtäthet. Stationer är bättre som täthetsvariabel jämfört med luftledningar eller en direkt kvotvariabel (meter/uttag).

#### Figur 11 – Stationer som täthetsvariabel i modellen

Diagram (spridning med trendlinje), "Effektivitet D8(3+5) TOTEX mot täthet (meter/uttag) år 2009". Y-axel: effektivitet 0 till 120 %. X-axel: täthet 0 till 400 (meter/uttag). Trendlinje: y = −0,0003x + 0,9277. Svagt men signifikant negativt samband.

Analysen av en särskild täthetsfaktor för att kompensera för högre kostnader visar att antalet nätstationer är mest lämpad. Det är ingen större skillnad mellan luftledning och stationer, men ändå är sambandet mellan OPEX-kostnader och nätstationer starkare än mot luftledningslängden. I figur 12 visas fördelningen av nätföretagens kostnadseffektivitet för en modell med åtta variabler (med totalkostnaderna som tre separata resursvariabler och med stationer som särskild kundtäthetsvariabel). Statistiken redovisas i Tabell 14. Medelvärdet på effektiviteten ligger på 90 %. Antalet fullt effektiva företag uppgår till 52, vilket utgör 1/3 av hela populationen i branschen. Det kan jämföras med OPEX-modellen med enbart OPEX påverkbart som resurs och stationer som täthetsvariabel. Medeleffektiviteten uppgår till 76 % och endast 16 företag är fullt effektiva.

#### Figur 12 – Kostnadseffektivitet i DEA D8(3+5) år 2009

Diagram. Visar fördelningen av nätföretagens kostnadseffektivitet i D8(3+5)-modellen (tre separata kostnadsvariabler + stationer som täthetsvariabel) för år 2009. Medeleffektivitet 90 %; 52 företag (1/3 av populationen) är fullt effektiva.

Det blir problematiskt om många fullt effektiva företag inte utgör förebild för andra företag. Det är då osäkert om dessa företag är så produktiva som mätningen gör gällande. I avsnitt 7.17 beskrivs detta närmare.

### Jämförelse DEA och SFA i en modell

En beräkning har gjorts med DEA och SFA i en TOTEX-beräkning för år 2009. I figur 13 och 14 redovisas resultaten. Totalkostnaderna är aggregerade till en post för att underlätta jämförelsen av resultaten. Medeleffektivitet är 75 % och vägt med uttagen 80 %. Det vägda värdet är således högre.

#### Figur 13 – Kostnadseffektivitet DEA D6(1+5) TOTEX år 2009

Diagram. Fördelning av kostnadseffektivitet beräknad med DEA i D6(1+5) TOTEX-modellen (aggregerade totalkostnader), år 2009. Medeleffektivitet 75 %; vägt med uttagen 80 %.

#### Figur 14 – Kostnadseffektivitet SFA D6(1+5) år 2009

Diagram. Fördelning av kostnadseffektivitet beräknad med SFA i D6(1+5)-modellen, år 2009. Medeleffektivitet 79 %; vägt med uttagen 79 %.

Medeleffektiviteten i SFA-beräkningen blir 79 % och vägt med uttagen 79 %. Vilket innebär att det vägda värdet är lägre. De större företagen har lägre effektivitet i SFA-beräkningen jämför med DEA. De minsta företagen får lägre mätetal på effektiviteten jämfört med SFA. Här verkar det som de olika metoderna ger olika resultat både vad avser nivå och rangordning. En förklaring kan vara att funktionsformen för SFA-beräkningen är felaktig (loglinjär modell).

#### Figur 15 – DEA och SFA resultat D6(1+5) TOTEX år 2009

Diagram (jämförelse). Visar per företag mätetalen från DEA respektive SFA i D6(1+5) TOTEX-modellen, år 2009. Flera företag med höga mätetal i DEA hamnar lågt i SFA.

Av figur 14 framgår att flera företag med höga mätetal i DEA hamnar lågt i SFA. Den relativt låga korrelationen framgår av Figur 15. Korrelationen är endast 0,55 (streckad linje).

#### Figur 16 – Korrelation mellan beräkningarna DEA SFA

Diagram (spridning). DEA-mätetal mot SFA-mätetal per företag, år 2009. Korrelationen är 0,55 (streckad regressionslinje).

### Användningen av SFA för fastställande av kraven

Metoder för effektivitetsjämförelser och mätning av produktivitetsutveckling som DEA och SFA är komplementära genom att DEA är ett kraftfullt verktyg för jämförelser när dataunderlaget är verifierbart, medan SFA har fördelar när risken för datafel är stor och/eller slumpmässiga avvikelser har stor inverkan.

En möjlig användning av SFA är som ett kompletterande verktyg vid hypereffektivitet, dvs. när enskilda företag i en DEA-beräkning får ett mätetal som visar full effektivitet, men där företaget inte utgör förebild för några företag som inte är fullt effektiva. Orsaken är att företaget ifråga är starkt avvikande från övriga företag. Detta beror på att detta företag har en mix av data som avviker från andra företag, vilket gör att det inte går att hitta några företag med ungefär samma mix som är mer produktiva. I detta fall karakteriseras företaget som "hypereffektivt". I dessa fall kan en lösning vara att använda mätetalet på en SFA-beräkning för att få en mer pålitlig bestämning av effektiviseringspotentialen. Vid effektivitetsberäkningar med DEA får man också kunskap om vilka andra företag som utgör förebilder och med vilken vikt. Dessa sammanvägda förebildsföretag bilder det virtuella effektiva "tvillingföretaget" till företaget i fråga. För de effektiva företagen redovisas också antal gånger som företaget utgör förebild för andra företag. Ett företag som är utgör förebild många gånger får ett stort inflytande på kostnadsnormen (fronten) och om detta företag har felaktiga värden påverkar det resultaten för många företag negativt. Därför finns det skäl att särskilt granska dataunderlaget för de företag som får hög mätetal på supereffektivitet och är förebild många gånger.

Det uppkommer också resultat där ett företag är effektivt, men det bara utgör förebild för sig själv. Detta beror på att detta företag har en uppsättning av data som avviker från andra företag, vilket gör att det inte går att hitta några företag med ungefär samma uppsättning som är mer produktiva. Det innebär att det inte går att hitta ett eller flera "tvillingföretag" som har ungefär samma produktionsprofil. I detta fall karakteriseras företaget som "hypereffektivt". I både dessa fall kan en lösning vara att använda mätetalet på en SFA-beräkning för att få en mer pålitlig bestämning av effektiviseringspotentialen. Genomsnittligt ligger mätetalen vid en SFA-beräkning högre jämfört med DEA-beräkningen, beroende på att eftersom en del av residualen i en regression fångas upp som slump, dvs. en del av avståndet till fronten räknas som slump. Därför riskerar SFA-skattningen att bli alltför försiktigt särskilt om data är verifierade och har liten slumpvariation, vilket är fallet vid nätverksamhet där flera av kostnadsdrivarna inte varierar särskilt mycket över åren.

Vid de fall ett företag är effektivt, men inte utgör en förebild för andra företag, kan mätetalet för en SFA för motsvarande modell gälla som detta företags potential. Exempel på detta är en DEA-beräkning för D8(3+5)-modellen för år 2009 jämfört med SFA-beräkning D6(1+5) där kostnaderna är aggregerade. Antalet hypereffektiva företag uppgick till 14 i DEA-beräkningen. Skillnaden i mätetal mellan DEA och SFA för dessa företag uppgick till 22 % med variation från 4 % till hela 51 %. Av de 14 hypereffektiva företagen enligt mätningen är fem små (färre än 2000 kunder). Det företag med störst skillnad (51 %) mellan DEA och SFA uppvisar också en supereffektivitet på hela 231 %, vilket gör att detta företag exkluderades från deltagande i frontbestämningen.

Om DEA-mätetalen för dessa 14 företag ersätts med mätetalen för SFA minskar medeleffektiviteten från 90 % till 88 %. Med en realiseringsfaktor på 50 % och ett minsta krav på 1 % per år ger det ett krav på minskade intäkter med 6,3 % av påverkbar OPEX för nästa regleringsperiod räknat för branschen som helhet.[^39]

## 8 Studier av effektivitet och produktivitetsutveckling

Det har under årens lopp gjorts flera studier av effektivitet och produktivitetsutveckling inom elnätsverksamhet. Vissa av dessa studier avser svenska förhållanden.

Sammantaget visar de olika studierna att det successivt sker förbättringar i produktiviteten över tiden, fast i olika takt, beroende på efterfrågeutveckling och kapacitetsutbyggnad. Kostnaderna varierar också över åren även till följd av yttre orsaker som t ex stormar som orsakar avbrott och som kräver omedelbar reparation. Mellan enskilda år kan det förekomma en negativ utveckling av produktiviteten, t ex med yttre faktorer som extrema stormar. Men även att t ex överförd el minskar under enskilda år. Kännetecknande för elnätsverksamhet är att efterfrågesidan (prestationerna) och de yttre omvärldsfaktorerna är till största delen opåverkbara (exogena).

Kostnader i verksamheten beror dels på den fysiska resursanvändningen, dels priset på dessa resurser. Möjligheterna att påverka kostnaderna beror på karaktären på resursen i fråga och vilka kontraktstider som gäller. Tidsperspektivet har därför betydelse då vissa kostnader kan påverkas kortsiktigt, medan andra kräver långsiktiga åtgärder. De frågor som ställts i de studier som gjorts har handlat om förekomsten av stordriftsfördelar (economies of scale), samproduktionsfördelar (economies of scope), hur kundtätheten påverkar kostnaderna, hur fusioner av företag påverkar effektivitet och produktivitetsutveckling.

### Analyser av elnätsföretagens produktivitetsutveckling

Det har gjorts relativt många studier av produktionseffektiviteten inom eldistribution under de senaste 20 åren, dvs. tvärsnittsstudier. Däremot är antalet studier som undersöker utvecklingen av produktiviteten över tiden relativt få. Två tidiga studier är Hjalmarsson och Veiderpass (1992) samt Veiderpass (1993). I dessa studier beräknades utvecklingen för åren 1970-1986 i en modell med åtta variabler (fyra resurser och fyra prestationer).[^40]

Resultaten i dessa studier visar på en stadig produktivitetsutveckling med i genomsnitt en årlig ökning med ca 5 %. Förklaringen är främst en successivt ökad distribution av el. I den andra studien från 1993, redovisas utförligare resultat och analyser. I huvudsak konstateras en successivt ökad produktivitet genom ökad eldistribution och att företag med övervägande landsbygdsdistribution ökar produktiviteten mer än företag som är verksamma i tätorter. Detta tolkas som en effekt av strukturrationaliseringar, som varit mer frekventa i företag med distribution på landsbygden.

I en studie av norska elnätsföretag för perioden 1983-89 ökade produktiviteten med i genomsnitt nästan 2 % per år (Försund och Kittelsen 1998). I denna modell ingick fyra resurser och tre prestationer. Resurserna utgjordes av arbetsinsats (timmar), nätförluster (MWh), material respektive kapitalkostnader (kr). Ökningen i produktivitet kunde nästan helt förklaras av skift i produktionsfronten, d v s att de mest produktiva företagen förbättrat möjligheterna inom branschen att producera till lägre kostnader.

I en studie från 2004 har Veiderpass utökat uppföljningen från de tidigare studierna (Veiderpass 2004). Undersökningen använder data fram till år 2001. Avsaknaden av uppgifter om personalanvändningen gör att modellens resurser endast består av de tre realkapitalvariablerna ledningslängd, uppdelat i låg och högspänning, samt total transformatorkapacitet. Produktiviteten för perioden 1970-2001 var mer eller mindre konstant enligt denna modell. I de större företagen syns en klart mer positiv utveckling.[^41] De stora företagen hade en genomsnittlig årlig ökning mellan åren 1996 – 2001 på 11,4 % medan de mindre företagen hade en minskning med 5,5 %.

Hjalmarsson och Kumbhakar (1998) undersökte utvecklingen av arbetsproduktiviteten i den svenska eldistributionen under perioden 1979 - 1990. De fann att ökningarna i arbetsproduktiviteten avtar över tiden. Från 3,5 % år 1970 till 1,7 % år 1990. En förklaring till den nedåtgående trenden är utvecklingen av volymerna av distribuerad el.

Produktivitetsutvecklingen i den norska eldistributionen har undersökts för åren 1996 – 2003. Det innebär att utvecklingen följts under olika regleringsregimer eftersom regleringen ändrades år 1997 från en avkastnings- till en intäktstaksreglering.[^42] År 1998 infördes även företagsspecifika beting på effektiviseringar på mellan 0 % och 3 % av intäkterna, förutom ett generellt krav på alla företag på 1,5 % av intäkterna.

Den modell som används i denna uppföljning av eldistributionen i Norge består av fem prestationer (överförd el, antal abonnemang, ledningslängd högspänning, ledningslängd lågspänning och förväntade leveransavbrott).[^43] De resurser som ingår i modellen består av fem variabler (personalinsats, material och tjänster, nätförluster, kapital och faktiska leveransavbrott).[^44] Det gör att modellen totalt har tio variabler eller dimensioner. Ledningslängderna och förväntade leveransavbrott ingår som ramfaktorer, d v s faktorer som nätföretagen inte kan påverka (miljövariabler). Mellan år 1996 och 2003 ökade produktiviteten med i genomsnitt 8,0 %, vilket innebär en årlig ökning med 1,1 %.[^45]

Statens energimyndighet har följt upp produktivitetsutvecklingen i två rapporter: "Elnätsföretagens kostnadseffektivitet och produktivitetsutveckling – jämförelser av nätföretagens distribution av el år 2002 samt utveckling 2000 – 2002" respektive "Elnätsföretagens kostnadseffektivitet och produktivitetsutveckling – en uppföljning av verksamheten 2003".

Resultaten för år 2000 – 2001 visar en genomsnittlig ökning av produktiviteten med drygt 6 %, både som en följd av minskade driftkostnader och ett ökat utnyttjande av näten. Produktiviteten ökade i genomsnitt med 3,3 % mellan år 2001 och 2002. Jämfört med utvecklingen tidigare år är det en halvering av ökningstakten. Förklaringen till detta är de högre elpriserna som minskade elanvändningen under år 2002.[^46]

Resultaten för år 2002 – 2003 visar en genomsnittlig ökning av produktiviteten med 3 %. Denna genomsnittliga förändring kan helt hänföras till att effektivitetsfronten skiftat, d v s den ökade produktiviteten har skett genom att de bästa företagen, som bestämmer effektivitetsfronten har blivit mer produktiva.

Ei publicerade den senaste uppföljningen av produktivitetsutvecklingen i en rapport år 2008 då perioden mellan 2001 – 2006 undersöktes.[^47] Mellan år 2001 och 2006 ökade produktiviteten i branschen med 3,6 % per år. Beräkningarna bygger på utvecklingen av de kortsiktigt påverkbara kostnaderna (drift- och underhåll) i förhållande till vad elnätsföretagen presterar i form av antal uttagspunkter (kunder), överförd el med mera. Denna ökning kan i huvudsak hänföras till att effektivitetsfronten, som bildas av de mest produktiva företagen, har expanderat, vilket innebär att branschen generellt förbättrat möjligheterna att producera tjänsterna till lägre kostnaderna. En tydlig tendens är att de företag som är relativt sett mest ineffektiva i utgångsläget (år 2001), ökar sin produktivitet relativt sett mera. Deras effektivitetsförändring är högre än de företag som i utgångsläget är förhållandevis kostnadseffektiva. Denna sk. upphinnareffekt är vanligt förekommande i olika branscher.

Uppföljningen av produktivitetsutvecklingen i rapporten baseras på de uppgifter som elnätsföretagen rapporterat till Ei. Beräkningarna har gjorts med hjälp av DEA-metoden och med användning av ett Malmquistindex (se bilaga 1). Modellen för beräkningen har kortsiktigt påverkbara kostnader som resursvariabel och sex produkter (överförd el uppdelat på hög och lågspänning, antal kunder också uppdelat på hög- respektive lågspänning, maximalt effektuttag mot överliggande nät samt total ledningslängd).

Ytterligare ett antal studier har gjorts över andra länders elnätsverksamhet. I Tabell 15 redovisas resultaten i olika länder vid olika perioder. Totalfaktorproduktivitetsförändringen (TFP) per år visar en spridning från -3,7 till 10,8. Medelvärdet uppgår till 2,7 % per år. Med de två extrema resultaten exkluderade blir medelvärdet: 2,6 % per år.

#### Tabell 15 – Totalfaktorproduktivitetsförändring i olika studier av elnätsverksamhet

| Nr | Land | Period | Studie | TFP procent per år |
|---|---|---|---|---|
| 1 | England/Wales | 1971-1993 | Weyman-Jones/Burnes, 1994 | 2,8 |
| 2 | " | 1990-1998 | Tilley/Weyman-Jones, 1999 | 6,3 |
| 3 | " | 1990-1997 | London Economics, 1999 | 3,5 |
| 4 | " | 1985-1997 | Hattroi/Jamasb/Pollit | 2,5 |
| 5 | " | 1985-1989 | " | −3,7 |
| 6 | " | 1990-1994 | " | 0,9 |
| 7 | " | 1995-1997 | " | 10,8 |
| 8 | Australien | 1981-1994 | London Economics, 1994 | 3,6 |
| 9 | Norge | 1983-1989 | Försund/Kittelsen, 1998 | 1,9 |
| 10 | " | 1994-1998 | ECON/Bowits et al | 2,8 |
| 11 | " | 1995-1998 | NVE, 2001 | 2,5 |
| 12 | Kanada, Ontario | 1993-1997 | OEB, 1999 | 2,1 |
| 13 | Nya Zeeland | 1994-1997 | London Economics, 1999 | 1,4 |
| 14 | Spanien | 1987-97 | Arocena/Contin/Huerta, 2002 | 2,9 |
| 15 | USA | 1994-1996 | London Economics, 1999 | 0,7 |
| 16 | " | 1972-1994 | Makholm, 2003 | 1,9 |
| 17 | " | 1984-1994 | Makholm, 2003 | 2,1 |
| 18 | Nord-Irland | 1971-1994 | Competion Commision, 2002 | 3,1 |
| 19 | Holland | 2001-2003 | Haffner | 3,2 |
| 20 | " | 2004-2006 | " | 2,8 |
| | | | **Medel** | **2,7** |

Källa: Hanse et al. 2005, Energy-Control Kommission 2005, Hafner 2005.

Sammantaget visar dessa undersökningar av produktivitetsutvecklingen att det successivt sker förbättringar i produktiviteten, fast i olika takt beroende på efterfrågeutveckling och kapacitetsutbyggnad. Resultaten visar på förbättringar oavsett val av modell och data. Ökningarna varierar dock över tiden.

### Produktivitetsutveckling i andra branscher

#### 8.2.1 Produktiviteten i det svenska näringslivet

Statistiska centralbyrån (SCB) publicerar data över näringslivets produktivitetsförändring över tiden. Det produktivitetsmått som används är arbetsproduktivitet vilket anger relationen mellan produktionsvolym och insatsen av arbetskraft. Produktionen mäts i termer av förädlingsvärde och arbetskraftsinsatsen i timmar eller årsverken. Anledningen till att SCB använder det måttet är sannolikt att för det första är det relativt enkelt att ta fram och för det andra inkluderas den viktigaste förklarande variabeln för ett lands produktivitet, nämligen insatsen av arbetskraft. Svagheten med att använda arbetsproduktivitet som mått är att det endast tar hänsyn till insatsen av arbetskraft. Måttet tar således inte hänsyn till ett ökat eller minskat utnyttjande av andra produktionsfaktorer som realkapital. Enligt SCB har arbetsproduktiviteten varit i genomsnitt 2,6 procent under perioden 1981-2007.

Eftersom den analys av produktivitetsutvecklingen som Ei gör i föreliggande rapport omfattar de kortsiktigt påverkbara kostnaderna och dessa utgör 40-50 % av de totala kostnaderna, kan man ändå göra en koppling jämförelsemässigt mellan arbetsproduktivitet och de resultat som Ei kommer fram till. Detta därför att huvuddelen av de operativa kostnaderna är kostnader för arbetsinsatser (personalkostnader och köpta tjänster).

#### Figur 17 – Näringslivets produktivitetsutveckling 1981–2013

Diagram (linjediagram). Förädlingsvärde till baspris/arbetade timmar, ENS 1995. Procentuell förändring från föregående år, åren 1981–2013 (x-axel 1981–2011, y-axel ungefär −8 till +8 %). Tre serier: Förädlingsvärde, Arbetade timmar, Produktivitet. Källa: SCB, data t.o.m. 2013.

Riksbanken använder SCB:s mått men kompletterar dessa med egna beräkningar. I skriften Den "nya ekonomin" och svensk produktivitet på 2000-talet framhåller Riksbanken svårigheten med att veta om produktivitetsförändringar är en effekt av det vanliga konjunkturmönstret eller om den beror på mer långvariga, strukturella faktorer.[^48]

#### 8.2.2 Historisk produktivitetsutveckling

Vissa branscher, som producerar t ex kapitalintensiva varor har haft en produktivitetsutveckling med i genomsnitt 3,1 % per år mellan 1970 - 94. Dessa branscher har högre värden än elnätsverksamheten, medan andra, som t ex branscher som producerar arbetsintensiva varor, har haft en produktivitetsutveckling med i genomsnitt 1,3 % per år.

Elnätsverksamhet räknas som en typisk kapitalintensiv verksamhet, vilket innebär att jämförelsen bör ske relativt andra kapitalintensiva branscher.

Näringslivet som helhet har ökat sin totalfaktorproduktivitet med i genomsnitt 1,2 % per år under perioden 1970-95. Tillverkningsindustrins utveckling varierar med konjunkturcyklerna. Med ett genomsnitt på 2,8 % per år under perioden 1965-95 visar detta att konkurrensutsättning ger en högre takt i förbättringarna. El, gas, värme och vatten (SNI 400) har under perioden 1970-94 i genomsnitt ökat produktiviteten med 1,5 % per år.

#### Tabell 16 – Utvecklingen av totalfaktorproduktiviteten 1970-95, procent per år

| Bransch (period) | TFP procent per år |
|---|---|
| Näringslivet (1970-95) | 1,2 % |
| Tillverkningsindustri, SNI 300 (1965-95) | 2,8 % |
| El, gas, värme och vatten (SNI 400) (1970-94) | 1,5 % |
| Kapitalintensiva varor (1970-94) | 3,1 % |
| Arbetsintensiva varor (1970-94) | 1,3 % |
| Skyddade varor (1970-94) | 1,3 % |
| Samfärdsel etc. (SNI 700) (1970-94) | 2,9 % |
| Byggnadsindustri (SNI 500) (1970-94) | 1,8 % |
| Kemisk industri (SNI 350) (1970-94) | 1,9 % |

I Tabell 17 redovisas utvecklingen för vissa branscher enligt den s k WIDE-modellen.[^49]

#### Tabell 17 – Produktivitetsutveckling i olika branschen enligt WIDE-modellen åren 1964 - 1989

| Bransch | Totalfaktorproduktivitet | Teknisk förändring |
|---|---|---|
| Massa- och papper (SNI 341) | 2,46 | 2,04 |
| Jord- och stenindustri (SNI 360) | 2,11 | 2,18 |
| Järn- och stålindustri (SNI 370) | 3,26 | 2,60 |
| Verkstadsindustri (SNI 380) | 3,50 | 3,05 |

Källa: "Kapitalbildning, kapitalutnyttjande och produktivitet", expertrapport nr 3 till produktivitetsdelegationen 1991.

#### 8.2.3 Prognoser på utvecklingen – framtida produktivitetsutveckling

Konjunkturinstitutet har i långtidsutredningen LU 2008 för perioden 2005 – 2015 gjort bedömningar över den framtida produktivitetsutvecklingen. Den genomsnittliga årliga förändringen i arbetsproduktiviteten för näringslivet som helhet bedöms uppgå till 2,66 % för perioden 2006-2020.[^50] Det är lägre än utvecklingen under perioden 1997-2005 då arbetsproduktiviteten ökade med 3,32 %. Totalfaktorproduktiviteten (TFP) bedöms öka med 1,6 % för perioden 2006-2020 i jämförelse med perioden 1997-2005 då TFP ökade med 2,0 % per år.

## 9 Effektiviseringskrav i regleringar av elnät

För att få en relation till de krav som ska ställas på effektiviseringar i nästa periods reglering av intäktsramarna är det av intresse att jämföra vilka krav som ställts i andra länders regleringar av elnäten. Särskilt relationen mellan beräknade effektiviseringspotentialer och de krav som ställs. En fråga som en reglerare ställs inför är bedömningen av hur lång tid det tar innan uppmätta effektiviseringspotentialer rimligen har realiserats. Ytterligare en fråga är hur mycket av effektivisering som ska få behållas av företagen respektive komma kunderna till del.

Reglering av elnätstariffer med hjälp av effektiviseringskrav har funnits i drygt 20 år. Nivån på den X-faktor som de olika reglerarna beslutat om under olika perioder varierar en del. En orsak till skillnaderna är naturligtvis bedömningen av hur stora effektiviseringspotentialer som finns i företagen. En annan var bedömningar över hur stora marginaler (monopolräntor) som företagen har. I flera länder var elnätsverksamheten en offentligt ägd verksamhet kombinerat med en avkastningsreglering. Det bedömdes därför i flera länders omregleringar att det fanns stora potentialer för framtida kostnadsminskningar. I tabell 18 och 19 visas de krav som ställts i ett antal regleringar. För distributionsverksamhet ligger medelvärdet för det generella kravet på omkring 2,5 %.[^51] Därutöver finns det företagsspecifika krav i vissa regleringar. För Finland gäller för innevarande period (2008-2001) ett generellt krav på 2,06 % och ett företagsspecifikt krav på mellan 0,05 % och 2,57 %. Medelvärdet för det företagsspecifika kravet är 0,62 %. Det innebär således ett totalt krav på branschen på 2,7 %.

Vissa regleringar sätter kravet på de löpande kostnaderna (OPEX), medan de flesta har satt kravet på totalkostnaderna (TOTEX) eller intäkterna (se bilaga 2). Eftersom de löpande kostnaderna uppgår till ca hälften av de totala kostnaderna ger en enkel sammanvägning att det generella kravet är i nivån 3,5 % om kravet för regleringar med TOTEX eller intäkter dubblas.

#### Tabell 18 – X-faktorer i olika regleringar för distribution

| Land | Regleringsperiod | Generellt krav | Företagsspecifikt krav (Min) | (Maxi) | (Medel) | Basen för X-faktorn |
|---|---|---|---|---|---|---|
| Danmark | 2008 | 0 | 4 | | 1,6 | OPEX |
| | 2000-2003 | 3,0 | | | | OPEX |
| Finland | 2008-2011 | 2,06 | 0,05 | 2,57 | 0,62 | OPEX |
| Tyskland | 2009- | 1,25 | 0 | 3,90 | 0,79 | TOTEX |
| Holland[^52] | 2000-2003 | 3,3 | | | | |
| Norge | 1997 | 1,5 | | | | TOTEX |
| | 1998-2002 | 1,5 | 0 | 3,0 | | TOTEX |
| | 2002-2006 | 1,5 | 0 | 5,2 | | TOTEX |
| | 2007-2012 | | | | | TOTEX |
| Tjeckien | 2005-2009 | 2,085 | | | | OPEX |
| UK | 1990-1994 | 0 | | | | TOTEX |
| | Momentant 1995/1996 | 25 | | | | TOTEX |
| | 1995-1999 | 3 | | | | TOTEX |
| | Momentant 1999/2000 | 15 | | | | TOTEX |
| | 2000-2004 | 3 | | | | TOTEX |
| | 2005-2009 | 0 | | | | TOTEX |
| | 2010- | 5,6 | | | | TOTEX |

Källa: dokument från de olika reglerarnas hemsidor samt liten e-postenkät.

För transmission redovisas X-faktorer i tabell 19. Medelvärdet ligger på 1,3 % medan medianvärdet ligger 1,8 % då flera länder inte har något effektiviseringskrav.

#### Tabell 19 – X-faktorer för transmission i olika regleringar

| Land | X-faktor | Basen för X | Omräknat per år |
|---|---|---|---|
| Austria | 2,5 | TOTEX | 2,5 |
| Czech Republic | 10 % for period (5 years) | TOTEX | 2 |
| Denmark | 0 % | | 0 |
| Estonia | 7,5 - 4,5 % for period (3 years) | | 2 |
| Finland | 0 % | OPEX | 0 |
| France | 3 % for period | | 3 |
| Germany | 0 % | | 0 |
| Hungary | 1,8 - 2,2 | TOTEX | 2 |
| Iceland | 1-2 % for period | | 1,5 |
| Ireland | 0 | | 0 |
| Italy | 2,30 % | | 2,3 |
| Lithuania | half of CPI | | |
| Luxembourg | 0 % | | 0 |
| Netherlands | 7,2 % for period (4 years) | TOTEX | 1,8 |
| Norway | 1,5-2,8 % | TOTEX | 2 |
| Poland | 0 % | | 0 |
| Portugal | 3,50 % | OPEX | 3,5 |
| Slovakia | 0 % | | 0 |
| Slovenia | 9,05 % for period (5 years) | OPEX | 1,8 |
| Spain | 0,6 % | | 0,6 |
| Sweden | 0 % | | 0 |
| UK | 2 % | Total revenue | 2 |

Källa: Report on TSO regulatory Models in Europe (CEER).

Nivån på X visar sammantaget att den vanligen ligger omkring 2,5 % (och att kravet är högre om man tar hänsyn till att de flesta av kraven ligger på intäkterna (totalkostnaderna), vilket innebär större belopp räknat i absoluta termer (kronor). För transmissionsnivån ligger kraven lägre.

## 10 Metodik för effektiviseringskraven

Med metodik avses här kedjan från val av metod för beräkning av effektiviseringspotentialer till de krav som slutligen kommer att fastställas i beslutet om intäktsram. Metodiken innefattar flera steg: val av beräkningsmetod, val av modell över nätverksamheten, val av data för beräkningarna, val av fastprisindex vid beräkningar över tiden, övervägande kring möjligheterna att realisera de estimerade potentialerna till ökad produktivitet, övervägande om generellt respektive företagsspecifikt krav samt gränser för maximala och minimala krav.

### Metodiken i sammanfattning

Utgångspunkten för bestämningen av kraven på effektiviseringar är att kunna fastställa vilka potentialer för effektiviseringar som finns och att företag med större potentialer får ett större krav på effektiviseringar. Syftet med metodiken som helhet är att rimliga krav ska ställas på företagen. Flera åtgärder vidtas för att minska risken att orealistiskt höga krav ska åsättas företagen.

- **Val av metod:** för beräkning av företagens kostnadseffektivitet kommer DEA-metoden att användas. För vidimering av resultaten kommer även SFA-metoden att användas, särskilt när det gäller företag som blir fullt effektiva i DEA-beräkningen, men som inte utgör förebilder för andra företag.
- Vid beräkningen med DEA kommer antagandet om konstant skalavkastning (CRS) att gälla för att skapa ett incitament för samgående i syfte att realisera stordriftsfördelar.
- **Val av modell:** en totalkostnadsberäkning (TOTEX) med tre separata kostnadsposter och fem kostnadsdrivare (produkter).[^53]
- **Data** för beräkningen utgörs av genomsnittsvärden på verksamheten under åren 2010-2013 för att få fram en stabil bestämning av kostnadseffektiviteten. Kostnaderna för åren 2010-2012 räknas om i 2014 års priser med hjälp av Statistiska centralbyråns faktorprisindex (FPI).
- Vid bestämningen av effektivitetsfronten, dvs normen för jämförelsen, kommer extrema mätetal på effektivitet som betydligt överstiger 100 % att (av försiktighetsskäl) exkluderas från att ingå i frontbestämningen före den slutliga beräkningen av potentialerna.
- En transformering sker av de beräknade potentialerna genom en realiseringsfaktor. Denna faktor bestäms utifrån antagande om hur stor andel av respektive kostnadspost som förväntas vara möjliga att påverka under reglerperioden av den uppmätta potentialen. Mätetalet på kostnadseffektivitet multipliceras med realiseringsfaktorn och appliceras på de löpande påverkbara kostnaderna.
- Ett generellt minsta krav bestäms med samma överväganden som gjordes inför den första reglerperioden. Den var baserad på historik över utvecklingen av produktiviteten i eldistribution, samt av hur produktiviteten utvecklas inom branscher på konkurrensmarknader. Detta krav sätts till 1 % per år av de operativt påverkbara kostnaderna. Detta innebär att även de effektivaste företagen får ett effektiviseringskrav och därmed krav på kontinuerliga produktivitetsförbättringar.

### Val av metod

Ei väljer att använda DEA som metod för att beräkna respektive nätföretags kostnadseffektivitet. Den alternativa metoden SFA används som ett kompletterande verktyg för att vidimera resultaten från DEA. Vidimeringen avser främst att undersöka om rangordningen mellan företagen är ungefär lika. Resultaten från SFA-beräkning kan även användas för de företag som noteras som hypereffektiva, dvs att de är fullt effektiva enligt mätningen, men endast utgör förebild för sig själv. Detta förekommer om företaget har en stor avvikelse vad gäller storlek och/eller mix av kostnader eller produkter, t ex enbart distribuerar stora volymer högspänningsel och ha få kunder.

Båda metoderna har sina styrkor och svagheter. Valet av DEA som huvudmetod motiveras främst av att den uppfattas som enklare och därmed lättare att kommunicera. Företagen kan själva använda metoden för att göra simuleringar på det egna företagets effektivitet vid olika ändringar i kostnader och även hur ändringar i verksamheten med avseende på kunder, uttagsmönster och överförd el. Vid beräkningar med DEA får man information om s k skuggvärden, vilket kan användas i deras egna rationaliseringsarbeten. Särskilt om man har en modell med separata kostnadsvariabler. Man får också informationen om vilka företag som utgör förebilder.

En fördel med DEA är att man inte behöver specificera funktionsformen. Nackdelen är att ingen slumpavvikelse tillåts. Denna nackdel kan delvis hanteras genom att låta extremvärden (supereffektivitet över en viss fastställd nivå exkluderas från att ingå i fronten, dvs att utgöra förebild (norm) för andra företag.

SFA kan användas som paneldataverktyg för att undersöka signifikanta variabler och produktivitetstrenden. Man kan även använda s k dummyvariabler för respektive år för att fånga upp särskilda år, som t ex då extrema stormar inträffat. SFA har fördel att ge statistiska signifikanstest på sambanden i modellen. Den hanterar osäkerhet genom att dela upp residualen i regressionen i en effektivitets och slumpterm. Det gör att i allmänhet kommer en SFA-beräkning att ge högre effektivitet jämfört med DEA. Nackdelen med SFA är att man måste göra ett antagande om funktionsformen på samband mellan kostnad och produktion. Detta kan ge s k specifikationsfel.

### Val av modell

En utgångspunkt vid beräkningarna då olika modeller prövas som kandidater för val av modell för att fastlägga kraven har varit de operativa kostnader som fastlagts som påverkbara under reglerperioden. Att enbart jämföra påverkbara operativa kostnader (OPEXp) innebär att effektivitetsjämförelsen enbart "skär" ut en del av verksamheten. Kopplingar till andra kostnadsposter beaktas inte. Eftersom företagens val av teknik i olika delar av verksamheten innebär vissa fixa relationer mellan påverkbara OPEX och icke-påverkbara OPEX respektive kapitalkostnader, riskerar en modell som enbart undersöker effektiviteten genom att endast se påverkbar OPEX som minimeringsvariabel att ge felaktig beräkning.

Till detta kan även läggas att frågan om påverkbarhet inte kan ha karaktär av antingen eller. Möjligheterna att påverka kostnaderna är inte binärt (noll – ett). Även de kostnader som regleringen har definierat som opåverkbara kan påverkas under en reglerperiod på fyra år. Takten är dock olika. För de operativa kostnaderna har realiseringstakten i flera regleringar satts till två perioder (8 år).[^54] För kapitalkostnaderna kan tiden för en periods rationalisering sättas till 4/40 om avskrivningstiden är 40 år. För operativa kostnader som inte idag ses som påverkbara kan tiden sättas till 16 år, dvs dubbelt jämfört med de påverkbara kostnaderna. Med en realiseringstid på 8 år innebär det att realiseringsfaktorn blir 0,5. Denna multipliceras med potentialen i procent och åsätts enbart de operativt påverkbara kostnaderna. Om företaget kan rationalisera i högre takt och även rationalisera övriga kostnadsposter, t ex i samband med investeringar, får företaget behålla dessa effektiviseringar.

Flera olika varianter av produktionsmodeller har prövats. Med hjälp av regressionsanalys har sambanden mellan olika "produkter" kostnadsdrivare och kostnad undersökts. I fokus har legat sambandet mot operativt påverkbara kostnader (OPEXp). Övriga operativa kostnader har i den föreliggande regleringen betraktats som opåverkbar och fullt möjlig för företagen att föra vidare till kunderna till 100 procent. Vissa av dessa opåverkbara kostnader är påverkbara på kort sikt, t ex upphandlingen av el till de nätförluster som uppstår. Även de fysiska nätförlusterna kan delvis påverkas på kortare sikt genom dels jämnare belastning i nätet, dels genom investeringar i högre kapacitet och ny teknik. Kostnaderna mot överliggande nät kan även påverkas genom att få ner de högsta effektuttagen under året.

Den modell som visade hög signifikans undersöktes mer i detalj. Den bestod av OPEXp och antal kunder (uttag), installerad transformatorkapacitet och luftledningslängd. Den ger som resultat relativt låga effektivitetstal och sett över åren ger den en negativ produktivitetsutveckling (som helt består av s k negativ teknisk förändring). Detta beror på att längden på luftledningar minskat över åren 2004-2012 p g a ökad kablifiering.

Flera olika alternativ till denna modell har prövats. Den modell som Ei föreslår består av följande variabler:

- **Totalkostnader (TOTEX) uppdelat på tre poster:** OPEXp, OPEXo och CAPEX

Dessa kostnader jämförs mot följande kostnadsdrivare (produkter):

- **Antal uttag (kunder), antal nätstationer, maximalt effektuttag mot överliggande nät, överförd lågspänningsel och överförd högspänningsel.**

För maximalt effektuttag har Ei valt att välja högsta värdet av variablerna "abonnerad effekt mot överliggande nät" och "uttagen effekt mot överliggande nät" enligt årsrapporten.

Denna D8(3+5) modell ger högre effektivitetstal jämfört med en modell som består av enbart OPEXp eller en modell där även OPEXo och CAPEX ingår, fast då endast som restriktioner, och inte som variabler som minimeras som OPEXp. Principiellt är det motiverat att ha med kostnadsrestriktioner för de kostnader som inte kan påverkas. Det innebär att OPEX-modell D8(1+2+5) att föredra, men dels ger den inte någon större skillnad mot en OPEX-modell där OPEXo och CAPEX inte ingår, dels ger den upphov till att flera företag inte får något mätetal på effektivitet (beräkningsprogrammet hittar ingen lösning på optimeringsproblemet) samt att det blir högre värden på s k icke-proportionell potential (s k slack). Se figur 8 i avsnitt 4.5.

Från teoretisk synpunkt är en TOTEX-modell att föredra eftersom regleringen då inte lägger sig i hur företagen väljer teknik och rationaliseringsinsatser. Den ger en beräkning på den långsiktiga potentialen, vilket i de beräkningar som gjorts ger ett klart lägre krav jämfört med de OPEX-modeller som undersökts. I andra länders regleringar av elnäten dominerar TOTEX som kostnad jämfört med OPEX.[^55] Att enbart välja ut en grupp av kostnader som påverkbara och jämföra kostnadseffektiviteten innebär att endast en del av verksamheten granskas. Det innebär risk för suboptimering både på kort och lång sikt. Både genom sätten att redovisa kostnader (underhåll eller investeringar) och genom att val av teknik kommer att påverkas vid investeringar. Incitament för att ersätta operativa kostnader med kapitalkostnader öka då effektivitetskrav inte läggs på dessa kostnader.

I den kommande regleringen av intäktsramarna kommer särskilda incitament för att minska nätförlusterna och för att reducera kostnaden mot överliggande nät att införas. Det innebär att dessa kostnader betraktas som påverkbara. Detta motiverar att även inkludera dessa kostnader i den generella jämförelsen av kostnadseffektiviteten. Företag som tidigare gjort insatser för att minska nätförlusterna och fått ner dessa jämfört med andra företag kommer att få en fördel av detta vid effektivitetsjämförelsen. Men de företag som har relativt låga nätförluster för given överföring kommer att ha svårare att få belöning i det särskilda incitamentet. För incitamentet som införs för att öka kapacitetsutnyttjandet i nätet kommer detta incitament att förstärkas om företagen är medvetna om att en totalkostnadsberäkning kommer att ske inför den tredje reglerperioden. En totalkostnadsmodell innebär därför en förstärkning av de särskilda incitamenten för nätförluster och nätutnyttjande.

De empiriska analyserna och de principiella övervägandena talar således för att använda TOTEX som ingående värde i effektivitetsberäkningarna.

### Val av data

För att öka säkerheten i fastställande av kraven kommer beräkningarna att utgå från medelvärdet för de fyra åren 2010-2013. Skälet till detta är att kostnaderna för dessa används som utgångspunkt för att beräkna den intäktsram som företagen ansöker om. Vidare kommer den kapitalbas som företagen rapporterar in att användas för att beräkna en kapitalkostnad. Motivet till att kostnaderna för fyra års verksamhet används är att minska risken att extrema händelser ett enskilt år ska få för stort genomslag på utfallet av mätningen. Det innebär att en del slumpmässiga avvikelser enskilda år jämnas ut.[^56]

Kapitalkostnaderna (CAPEX) kan antingen grundas på den beräkningen företagen gör för basen år 2014, eller att Ei gör beräkningar över basen för åren 2010-2013 genom att räkna baklänges över investeringar och utrangeringar och sedan ta ett medelvärde för de fyra årens kapitalbestånd. Att räkna fram en kapitalkostnad per år ger en något högre precision jämfört med att enbart använda kapitalbasen för år 2014. Ei har dock valt att enbart använda kapitalbasen för 2014 eftersom det krävs relativt mycket manuellt arbete att göra en kapitalbasberäkning för respektive år. Risken är att fel uppstår vid en sådan manuell beräkning.

För bedömning av produktivitetsutvecklingen räknar Ei dels med DEA och s k Malmquistindex, dels med panelregressioner för åren 2004-2013. För vidimering gör Ei också jämförelser med utvecklingen i konkurrensutsatta branscher (se kapital 8). Kunskap om utvecklingen utgör grund för fastläggning av det generella minimikravet för företagen.

### Från potential till krav

Transformationen från beräknade potentialer till krav i intäktsramen på effektiviseringar görs genom en kalibrering där kvoten mellan antalsmedel och vägt medel för branschen ger en kalibreringsfaktor. Detta innebär i praktiken en uppräkning av effektivitetstalen då effektiviteten är högre för de större företagen. Motivet är att koppla kraven till kunderna. Det krav som formuleras ska motsvara den kundvägda genomsnittliga nivån i branschen.

Vid en beräkning där den det är den långsiktiga potentialen för effektiviseringar som beräknas måste denna potential översättas till ett krav för de fyra åren i regleringsperioden. Även de kostnader som regleringen har definierat som opåverkbara kan påverkas under en regleringsperiod på fyra år. Takten är dock olika för olika kostnader, beroende på kontraktslängder och användningstid. Kostnader för t ex nätförluster kan dels påverkas via den upphandling som sker, dels via ett jämnare utnyttjande av nätet, dels via investeringar i ledningar med större kapacitet. Möjligheterna att påverka nätförlusterna har därmed olika tidsutdräkter. Även kapitalkostnaderna kan påverkas. Främst genom de årliga investeringarna. Med en avskrivningstid på 40 år innebär det att 1/10 av anläggningarna byts ut varje år. För de operativa kostnaderna har realiseringstakten i flera regleringar satts till två perioder (8 respektive 10 år), t ex Finland och Tyskland.

Enligt föreskrifterna (EIFS 2015:2) definieras de operativa kostnaderna i påverkbara respektive icke-påverkbara. Vid beräkningen av intäktsramarna har kravet på effektiviseringar applicerats på enbart de påverkbara löpande kostnaderna.

Kravet på effektiviseringar kommer därför att åsättas kostnadsposten "löpande påverkbara kostnader". Det innebär naturligtvis inte en uppmaning till ett enbart försöka minska dessa kostnader. Eftersom mätning sker i TOTEX-termer och om sådan sker inför den tredje regleringsperioden ger kostnadsminskningar på övriga poster positivt bidrag till utfallet på jämförelsen. Genom att TOTEX-modellen innehåller tre separata poster får företagen information om "skuggvärden" på respektive post, dvs vilken post man bör prioritera i rationaliseringsarbetet.

Kravet på effektiviseringar räknat i procent bestäms som mätetalet på kostnadseffektivitet från beräkningen i TOTEX-modellen multipliceras med en realiseringsfaktor som sätts till 50 %, dvs hälften av den beräknade potentialen bör genomsnittligt kunna realiseras under perioden. De företag som realiserar mera får behålla denna del fullt ut.

Dessutom läggs en restriktion in på nivån på det maximala kravet för att företag som t ex har en mycket ogynnsam verksamhetsmiljö till skillnad från sina "tvillingföretag". Det kan gälla några få företag som avviker betydligt i effektivitet jämfört med övriga och där kontroll av data ändå inte har visat att resultaten beror på fel i dataunderlaget.

### Försiktighetsfilter

För att minimera risken att de enskilda kraven på effektiviseringar blir alltför höga innefattar den valda metodiken ett antal åtgärder. Om ett företag rapporterat in felaktiga värden som ger företagen en hög effektivitet, kommer andra företag att få lägre effektivitet än om företaget med felaktiga värden inte ingår i fronten.[^57]

Det första filtret är DEA-metoden i sig själv. Jämför med t ex en norm som bygger på fasta värden (normkostnader), beräknas effektiviteten i DEA med hjälp av vikter som bestäms vid själva beräkningen och därvid bestäms vikterna så att givet övriga företag får så hög effektivitet som möjligt. Har t ex ett företag en relativt stor distribution av högspänningsel, kommer vikten för denna produkt att bli relativt hög jämfört med övriga produkter i modellen.

Det andra filtret är att de data som används vid beräkningarna utgörs av medelvärdet för modellens data för de fyra åren 2010-2013 för respektive företag. Därigenom undviks att avvikelser i enstaka år får stort genomslag, t ex en storm eller ovanligt höga underhållsinsatser. Företagen lämnar in i sin ansökan för intäktsramar sina kostnader för dessa år. De data som lämnas in kommer också att granskas särskilt.[^58]

Det tredje filtret är att leta upp extrema resultat på effektivitet. Det kan göras med DEA genom att för det företag som effektiviteten mäts för så görs jämförelsen endast mot övriga företag – inte mot sig själv. Om ett företag är mer produktivt än det näst mest produktiva företaget (för ungefär samma produktion), kommer mätetalet på effektivitet att överstiga 1,0 eller 100 %. Ett kriterium för att exkludera ett sådant företag från att vara med och bilda effektivitetsfronten är följande:

> Ei > q(75) + 2,0·[q(75) − q(25)]
>
> Ei (n-i) = mätetal på effektivitet
> q(0,75) = fjärde kvartilen för alla företag
> q(0,25) = första kvartilen för alla företag

Mätetalet på effektivitet som överstiger summan av kvartil 3 värdet och skillnaden mellan tredje och första kvartilen vägt med 2.[^59] Genom att ändra på faktorn utanför klammern kan strängheten i kriteriet varieras.

Ett fjärde filter är slutligen att sätta ett krav på de (fåtal) företag som uppvisar ett starkt avvikande resultat. Kriteriet är här att avståndet till nästa företag i effektivitet är större än en viss faktor.

Genom dessa filter har sannolikheten för alltför hög krav ska utgå reducerats avsevärt. En försiktighetsprincip ligger bakom dessa filter. Samtidigt reduceras risken för att vissa företag ska få alltför låga krav genom att de som noteras som fullt effektiva i DEA-beräkningen, men inte utgör förebild för andra företag får sin potential beräknad med en SFA-beräkning.

### Översikt över metodiken

I tabell 20 nedan visas valen i översikt.

#### Tabell 20 – Översikten över metodiken för effektiviseringskrav

| Steg | Val |
|---|---|
| Metod | DEA (CRS) primärt och SFA (loglinjär) som stöd. För företag som mäts som fullt effektiva i DEA-beräkningen men inte utgör förebild, ersätts mätetalet med mätetal från SFA-beräkning. |
| Modell | Totalkostnader (TOTEX) uppdelat i tre separata poster: två för de operativa kostnaderna (OPEX påverkbart, OPEX opåverkbart) samt kapitalkostnader (CAPEX). |
| Data | Medelvärden på modellens data för de fyra åren 2010-2013 för de ansökningar som företagen lämnar in till förslag på intäktsram, samt årsrapportdata från företagen. |
| Index | Fastprisberäkning med SCBs faktorprisindex (FPI) i 2013 års prisnivå. |
| Extremvärden | Exkluderande av företag med s k supereffektivitet över viss nivå. Återkoppling till företagen. Om ingen ändring i data så exkluderas sådana företag från fronten (normen). |
| Från beräknade potentialer till krav | 1. Realiseringsfaktor: 50 % av mätetalet på effektivitet i TOTEX-modellen (D8(3+5)) applicerat på påverkbar OPEX. 2. Ett minsta krav på 1 procent per år på påverkbara löpande kostnader åsätts alla företag. Det utgör det generella kravet. 3. En begränsning sätts på det maximala kravet ett företag kan få. |

För ett företag med 100 i påverkbar löpande kostnad innebär det att under de fyra åren ska företagen intäktsramen för dessa kostnader minska med minst 3,94 % genom det generella kravet på 1 % per år. Om ett företag har en uppmätt potential på t ex 10 %, blir effektiviseringskravet 5 % (med realiseringsfaktorn 0,5). Det företagsspecifika kravet blir då 5. Eftersom 5 är större än 3,94 blir det slutliga kravet 5 i minskad ram för perioden.

### Metodiken för regionnätsföretagen och stamnätet

För region- och stamnät är möjligheterna att tillämpa måttstockskonkurrens mycket mer begränsade. Principen för måttstockskonkurrens bygger på att det finns tillräckligt många företag i branschen som går att jämföra. För de lokala elnätsverksamheterna uppfylls detta mer än väl genom de ca 170 nätföretag som finns i landet. På regionnätsnivån finns endast ett fåtal nätföretag med regionnätsverksamhet, för närvarande finns 8 regionnätsområden samt ett stamnätsföretag (Svenska kraftnät).

Eftersom den metodik för effektivitetsjämförelser som avses tillämpas för lokalnätsföretagen, är baserad på existensen av många företag kan inte samma metodik appliceras på regionnäten och stamnätet. Detta innebär att kraven på effektiviseringar måste fastställas på annat sätt. Resultaten av effektivitetsmätningarna av lokalnätsföretagen kan dock komma att utgöra del av beslutsunderlag för effektivitetskrav för regionnätsföretagen och stamnätet.

För reglerperioden 2012-2015 gällde ett årligt krav på 1 % av påverkbara kostnader för samtliga elnätsföretag. Denna princip kommer även fortsatt att gälla som ett minsta krav på effektiviseringar. Därutöver avser Ei att ställa även individuella krav på både regionnäts- och stamnätsföretag. Det kravet kan fastställas enligt flera alternativ. Antingen som det genomsnittliga kravet för lokalnätsföretagen eller effektivitetskravet för en grupp av företag i ungefär samma storleksnivå. Ett tredje alternativ är att medelkravet för de företag som har lokalnätsdistribution appliceras även på regionnätet, t ex att medelkravet för Vattenfalls två lokalnätsområden gäller som krav för Vattenfalls regionnät.

## Referenser

Armstrong, Cowan and Vickers, "Regulatory Reform – Economic Analysis and British Experience", 1994. The MIT Press.

Bogetoft and Otto, "Benchmarking with DEA, SFA and R", Sringer 2011.

Coelli, T. (2000) Some Scattered Thoughts on Performance Measurement for Regulation of A Natural Monopoly Network Industry, Working Paper, Centre for Efficiency and Productivity Analysis, University of New England, Australia.

Coelli, T., D.S.Prasada Rao, och G. Battese (1998) An Introduction to Efficiency and Productivity Analysis, Kluwer Academic Publishers.

Coelli, T, Estache, A och Perelman, S, (2003) "A Primer on Efficiency Measurement for Utilities and Transport Regulators", WBI Development Studies.

Coelli, T ((1996), "A Guide to FRONTIERS Version 4.1", CEPA, No 7/96.

Cooper, W.W., L.M.Seiford, och K.Tone (2000) Data Envelopment Analysis, Kluwer Academic Publishers.

Edvardsen, Försund, Hansen, Kittelsen och Neurater "Productivity and regulatory reform of Norwegian Electricity Distribution Utilities" 2005 working paper. Forthcoming in Coelli and Lawrence (2006), "Performance measurement and regulation of network utilities" Edward Elgar Publishing.

Ek Göran, "Mätning av produktivitet vid fusioner av elnätsföretag", PM 2007-01-25, 2007.

Energimyndigheten (2004) Elnätföretagens kostnadseffektivitet och produktivitetsutveckling – jämförelser av nätföretagens distribution av el år 2002 samt utvecklingen 2000-2002, ER 10:2004.

Ei (2005): Elnätföretagens kostnadseffektivitet och produktivitetsutveckling – en uppföljning av verksamheten 2003.

Førsund, F. R. och Kittelsen, S. A. C. (1998) "Productivity Developments of Norwegian Electricity Distribution Utilities, Resource and Energy Economics, 20(3), pp. 207-224.

Genberg M (1992), "The Horndal effect: productivity growth without capital investment at Horndalsverken between 1927 and 1952", Uppsala.

Hjalmarsson, L. och Veiderpass, A. (1992a) "Productivity in Swedish Electricity Retail Distribution", Scandinavian Journal of Economics 94, Supplement.

Hjalmarsson, L. och Veiderpass, A. (1992b) "Efficiency and Ownership in Swedish Electricity Retail Distribution". Journal of Productivity Analysis 3.

Hjalmarsson, L. och Kumbhakar, S. C. (1998). "Relative Performance of Public and Private Ownership under Yardstick Competition: Swedish electricity retail distribution, 1970-1990". European Economic Review.

Joskow, P (2007), "Incentive regulation in theory and practice: electricity distribution and transmission networks", working paper MIT and NBER.

Nillesen, P och Pollitt, M (2007), "The 2001-03 electricity distribution price control review in the Netherlands: regulatory process and consumer welfare", Journal of Regulatory Economics 31.

Kennedy, P, (2008), "A Guide to Econometrics", Blackwell Publishing.

Kittelsen, S. A. C. (1994) "Effektivitet og Regulering i Norsk Elektrisitetsdistribusjon", SNF-rapport 3/94, SNF, Oslo.

Långtidsutredningen 2008, SOU 2008:14, Huvudbetänkande.

Långtidsutredningen 2008, SOU 2008:14, bilaga 6.

Veiderpass, A. (1992) Swedish Retail Electricity Distribution: A Non-parametric Approach to Efficiency and Productivity Change, Ekonomiska studier nr 43, Nationalekonomiska institutionen, Göteborgs universitet.

Veiderpass, A (2004) Avreglerad elförsörjning. Ökad konkurrens och ökad effektivitet?, Göteborgs universitet. Rapport 1.

Veiderpass, A (2004) Avreglerad elförsörjning. Ökad konkurrens och ökad effektivitet?, Göteborgs universitet. Rapport 2.

Statistiska centralbyrån (webbreferenser, se ursprungsdokumentet). Sveriges riksbank (webbreferenser, se ursprungsdokumentet).

## Bilaga 1 Metoder

### 1 Tvärsnitt och paneldata

För varje år rapporterar elnätsföretagen in uppgifter över kostnader och produktion. Dessa uppgifter ger för varje år tvärsnittsdata som kan analyseras. Sambandet mellan kostnader och produktion kan studeras med t ex regressionsanalys.

Om flera tvärsnitt läggs samman får man en panel. Det innebär att varje enskilt företags utveckling kan studeras över tiden i relation till övriga företag. Panelen medger undersökningar som kombinerar tvärsnitts- och tidsserieanalyser.

### 2 Cobb-Douglas och translog

En modell med de variabler som visar sig vara mest signifikanta vid en analys av varje enskilt år används vid panelskattningen.[^60] Förutom kostnadsdrivarna läggs även in en tidstrend som variabel. Med t ex tre oberoende variabler blir det fyra parametervärden som ska skattas. Modellen beräknas som både en Cobb-Douglas loglinjär funktion och en translogaritmisk funktion. Vid en Cobb-Douglas loglinjär funktion är exponenterna (de skattade parametrarna) konstanta över hela produktionsintervallet (verksamhetsnivåerna på företagen). Om summan av exponenterna är under 1,0 vid en kostnadsfunktion visar det att en ökning av verksamhetsnivån (produktionen med 1 %) ger kostnadsökningar som är mindre än 1 %. Vidare förutsätter denna modell att substitutionselasticiteterna mellan prestationerna är konstant och ett.

Den translogaritmiska modellen är en generalisering av Cobb-Douglas modellen och flexibel i den mening att de antaganden som ligger i Cobb-Douglasmodellen inte behöver gälla. Skalavkastningen kan exempelvis variera över storleken på verksamheten. Vidare tar den translogaritmiska modellen hänsyn till interaktioner mellan förklaringsvariablerna i modellen.

- Generellt: C = C(Q, W) där Q är produktion och W faktorpriser
- Translogaritmisk funktion (flexibel) vid 2 oberoende variabler:
  1. Q1, Q2 (2 parametrar)
  2. Q1·Q1·0,5; Q2·Q2·0,5 (andra ordningen)
  3. Q1·Q2 (interaktionsvariabel)

Den translogaritmiska modellen möjliggör större flexibilitet genom färre antaganden om produktionssambanden, men den innebär också betydligt fler parametrar att estimera, vilket är problematiskt om antalet observationer är litet. Med tre kostnadsdrivare och en tidsvariabel (för att skatta produktivitetsutvecklingen) blir antalet parametrar totalt 14.

Med de skattade parametrarna går det att dels beräkna den tekniska utvecklingen (technical change, TC) och förändringen i skaleffektivitet (scale efficiency change). Men då modellen inte använder sig av en frontansats som t ex stokastisk kostnadsfront (SFA), så kan vi inte beräkna förändringen i teknisk effektivitet (technical efficiency change, TEC).

Teknisk förändring visar hur kostnadsfunktionen förändras över tiden, dvs hur den skiftar upp eller ner. En positiv utvecklingen visar att företagen kan producera samma saker med lägre kostnader för en given volym. Förändringen i skaleffektivitet ger ett mått på kostnadsfördelen av en förändrad volym, t ex som en följd av en sammanslagning av företag. Om det finns skalfördelar ger en utökning av verksamheten volymmässigt lägre kostnader per producerad enhet, dvs att styckkostnaden minskar.

En Cobb-Douglas modell med kostnader som beroende variabel och två produkter som förklaringsfaktorer för volymerna (nivån på verksamheten) och en trend för att förklara produktivitetsutvecklingen får följande generella utryck i sin grundform respektive i loglinjär form:

> C = A · Q1^α1 · Q2^α2 · t^α3
>
> lnC = lnA + α1·lnQ1 + α2·lnQ2 + α3·t

Parametervärdena α visar hur mycket kostnaderna ökar på marginalen vid en volymökning. Den tredje parametern α3 visar den tekniska förändringen – den årliga procentuella förändringen i kostnaderna.

Vid en translogaritmisk modell blir den linjära formen följande:

> lnC = lnA + α1·lnQ1 + α2·lnQ2 + α3·lnQ1·lnQ2 + 0,5·[α4·lnQ1·lnQ1 + α5·lnQ2·lnQ2] + α6·t + α7·t² + α8·lnQ1·t + α9·lnQ2·t

Den tekniska förändringen beräknas som partialderivatan med avseende på t vilket blir:

> TC = α6 + 2·α7·t + α8·lnQ1 + α9·lnQ2

Detta värde ändras med olika värden på t och volymvariablerna Q1 och Q2. Om α7 är negativ minskar TC över tiden och tvärtom om α7 är positiv.

### 3 DEA och Malmquistindex

I studien används i huvudsak den icke-parametriska metoden Data Envelopment Analysis (DEA). Med beräkningsmetoden DEA kan kostnadseffektiviteten beräknas för modeller som innehåller flera resurs- och flera produktkategorier. Eftersom produktionen av elnätföretagens prestationer på kort sikt är bestämd av antal uttagspunkter och överförd el till kunderna, är det naturligt att beräkna kostnadseffektiviteten genom minimering av kostnader givet det som producerats. Uppgiften för ett elnätföretag är att producera de efterfrågande tjänsterna till så låg kostnad som möjligt eftersom de inte kan bestämma över efterfrågan på deras tjänster. Vid en minimering söker optimeringsprogrammet vid beräkningen att reducera användningen av resurskategorierna proportionellt tills effektivitetsfronten nås givet den produktion som företaget har presterat.

Den ansats som används bygger på att varje företag jämförs mellan åren som deltagare i en panel, d v s det är två tvärsnitt av företag för respektive år som jämförs. I figur 18 visas principen för detta i två dimensioner med kostnaderna på den vertikala axeln och produktionen på den horisontella axeln.

Ett sätt att mäta produktivitetsutveckling för ett visst företag är att jämföra resursanvändning och produktion för två perioder (år) mot den front som finns för den första perioden (året). Denna front bildas av de mest produktiva företagen under denna period.

Produktivitetsutvecklingen för de två perioderna kan även relateras till den front som bildas av de mest produktiva företagen period 2 (år 2).

Slutligen kan utvecklingen för ett företag jämföras mot båda fronterna. Då detta görs går det att få kunskap om hur fronten förändras över tiden.

#### Figur 18 – Produktivitetsmätning med Malmquistindex

Principskiss. Axlar: kostnad (vertikalt), produktion (horisontellt). Två kostnadsfronter ritas: Front år 1 och Front år 2. Två observationer av samma företag (O1 = år 1, O2 = år 2) mäts mot båda fronterna, vilket ger fyra effektivitetsmått: E11, E12, E21, E22 (första indexet = front, andra indexet = observationens år). Uppdelningen i effektivitetsförändring och frontförändring (teknisk förändring) bygger på dessa fyra mått.

Först mäts avståndet till den front som de mest produktiva företagen bildar för år 1 för utfallet av kostnad och produktion för observation (företag) O1 för år 1. Det motsvarar en normal tvärsnittsmätning där kostnadseffektiviteten beräknas genom att kostnad och produktion för företag O1 jämförs med alla observationer för detta år. Det ger effektivitetsmåtten E11 där det första indexet anger den front som mätningen görs mot och det andra indexet anger vilken observation (företag) mätningen görs för.

I den andra mätningen jämförs kostnad och produktion för företag O1 relativt alla observationer (företag) för år 2. De mest produktiva observationerna år 2 bildar den kostnadsfront som utgör normen för att mäta kostnadseffektiviteten mot. Den mätningen ger effektivitetsmåttet E21. För observation O2, d v s samma företag som tidigare fast med utfallet för kostnader och produktion år 2 kan på samma sätt två mätningar göras. Dels mot kostnadsfronten för år 2, dels mot kostnadsfronten för år 1. Dessa mätningar ger effektivitetsmåtten E22 respektive E12.

Det index vi använder för att mäta produktivitetsförändringen kallas för Malmquistindex.[^61] Det kan ske genom att utgångsårets kostnadsfront utgör bas för jämförelsen.[^62]

> M1 = E12/E11

Det första indexet anger vilken front som mätningen sker mot och det andra indexet anger perioden för den observation (företag) som undersöks.

- E12 = Företagets verksamhet år 2 jämfört mot alla företags verksamhet år 1.
- E11 = Företagets verksamhet år 1 jämfört mot alla företags verksamhet år 1.

Produktivitetsförändringar kan även beräknas med slutperioden som bas:

> M2 = E22/E21

- E22 = Företagets verksamhet år 2 mot alla företags verksamhet år 2.
- E21 = Företagets verksamhet år 1 mot alla företags verksamhet år 2.

Resultaten (M1 och M2) kan skilja sig åt beroende på om mätningen görs mot utgångsårets respektive slutårets front. Det beror på i vilken utsträckning som mixen av de ingående volymerna ändras. Om t ex volymen av en produkt ökar starkt, medan volymen av någon annan minskar (allt annat är lika), kan de två fronterna korsa varandra. Mätt mot den ena fronten kommer vi att registrera en produktivitetsökning, medan en mätning mot den andra visar en produktivitetsminskning.

Ett sätt att slippa välja vilken front som mätningen ska göras mot är att helt enkelt använda båda som norm. Denna mätning blir då en kompromiss mellan de två övriga. Här mäts produktivitetsutvecklingen som det geometriska medelvärdet av de två Malmquistindex som presenterats ovan:

> M = √(M1·M2)

För att mäta enligt detta sätt krävs fyra beräkningar för varje företag. En mätning mot två fronter ger möjlighet att dela upp förändringen i två komponenter: förändring relativt fronten (effektivitetsförändring) respektive skift i fronten, dvs avståndet mellan de två fronterna (teknisk förändring). Detta har också kommit att bli den vanliga definitionen på ett Malmquistindex.

Den frontförändringen mäts som skillnaden mellan fronterna vid de volymer av produkter och resurser som företaget har för respektive år. Frontförändringen beräknas som ett geometriskt medelvärde av skillnaden mellan fronterna vid respektive år.

Uppdelningen i två komponenter ser ut enligt följande:

> M = (E22/E11) · [ (E11/E21)·(E12/E22) ]^(1/2)

Kvoten utanför kvadratroten mäter förändringen relativt fronten, medan kvadratroten av uttrycket inom klamrarna mäter frontförändringen. Avståndet mellan fronterna mäts således dels för utfallet av verksamheten både år 1 och år 2. Medelvärdet av dessa två avstånd ger måttet på hur fronten har skiftat mellan åren. Detta innebär att mer information om vad produktivitetsutvecklingen beror på kan utvinnas av de produktionsuppgifter som finns.

### 4 Stokastiska produktionsfronter (SFA)

Medan en regressionsanalys (OLS) estimerar ett genomsnittligt samband mellan beroende och oberoende variabler, estimerar SFA en produktionsfront (eller kostnadsfront). Men till skillnad från en "corrected ordinary least square, COLS), tillåter SFA att vissa observationer hamnar ovanför fronten vid en produktionsfront (och nedanför vid en kostnadsfront). Vid en COLS-estimering flyttar man det genomsnittliga sambandet uppåt tills alla observationer är på eller nedanför fronten.

Den stokastiska fronten innebär att den vanliga feltermen (residualen) vid en OLS-estimering delas upp i två delar: en slumpterm (vi), som kan vara både positiv och negativ, och en icke-negativ del (u) som mäter effektiviteten. En loglinjär modell med en produkt ger följande formulering för en kostnadsfunktion:

> lnKi = β0 + β1·lnQi + vi + ui,  i = 1,2,3,…,N

Slumptermen vi mäter slumpavvikelser som påverkar värdet på beroende variabeln tillsammans med den kombinerade effekten av ospecificerade variabler, dvs förklaringsfaktorer som inte ingår i modellen. Slumptermen är oberoende av förklaringsvariablerna och normalfördelad med medelvärde noll och en konstant varians oberoende av värdena på effektivitetsdelen (ui), som är fördelad enligt en exponentiell eller halvnormal slumpfördelning.

Principen för en SFA visas i figur 19. Produktionen (Q) på den horisontella axeln och kostnaden (K) på den vertikala axeln. Observationerna är markerade med punkter, dvs varje företag kombination av producerad volym och kostnad.

#### Figur 19 – Den stokastiska produktionsfunktionen

Principskiss. Axlar: produktion Q (horisontellt), kostnad K (vertikalt). Kostnadsfronten K(Q) ritas; observationerna ligger spridda runt fronten. Avvikelsen från fronten delas upp i en slumpterm (v) och en ineffektivitetsdel (u).

Den stokastiska formen är parametrisk till skillnad från DEA och kräver därför att formen (funktionen) specificeras, t ex Cobb-Douglas och att man måste göra antaganden om den slumpmässiga fördelningen av brusdelen och ineffektiviteten i residualen. Huvudkritiken mot SFA är att antaganden om fördelningen av ineffektivitetsdelen måste göras. Det gör att man dels kan göra en felaktig specificering av sambanden, dels att fördelningen av ineffektivitetsfördelning riskerar blir felaktig.

## Bilaga 2 Modeller av elnätsverksamhet

### 1 Valet av modell

För att undersöka sambandens styrka mellan resursvariabler och produktionsvariabler kan olika statistiska test användas. Både parametriska test som regressionsanalys och olika icke-parametriska rangordningstest som mediantest är lämpliga för detta. Här använder vi den regressionsanalys som även används för produktivitetsberäkningen. Endast variabler som är statistiskt signifikanta tas med. De faktorer som ska ingå i modellen bör ha ett naturligt saklogiskt skäl för att ingå.

Ett antal kriterier kan ställas upp som ledning vid valet av modell för att undersöka kostnadssamband och produktivitetsutvecklingen:

- Variabeln (faktorn) ska vara en kostnadsdrivare, det vill säga positivt påverka kostnaderna vid ökad produktion.
- En kostnadsdrivare, som t ex antal uttagsabonnemang, kan genom en regressionsskattning testas för sin signifikans. Har variabeln en signifikant samvariation med variationerna i kostnader?
- Successivt kan man pröva olika modeller. Variabeln kunder kan delas upp i olika kategorier. Modellen kan då utökas från att bara har kunder som förklaringsfaktor till att ha hög- respektive lågspänningsabonnemang som förklaringsfaktorer.
- En uppdelning av en aggregerad variabel som kostnader, överförd el, antalet uttagspunkter eller ledningslängder görs om det kan visas att variationen i denna variabel har en statistisk signifikans.
- En ny variabel förs in om denna dels är motiverad av at det finns ett kostnadssamband, dels har stor inverkan på kostnaderna, det vill säga har en signifikant inverkan på variationen i beroende variabeln.

### 2 Modeller som använts vid effektivitets- och produktivitetsmätningar

I Tabell 21 redovisas ett antal olika studier över produktionseffektivitet som gjorts på elnätsverksamhet.

Variabelförkortningar:

- OPEX = Kortsiktig kostnad (operating expenditure)
- CAPEX = kapitalkostnader (capital expenditure)

#### Tabell 21 – Översikt av modeller som använts i uppföljningar av effektivitet och produktivitet

(Varje modell beskrivs med tre kolumner: insatsfaktorer, produktion och ramfaktorer. Listorna i varje cell är oberoende.)

| Modell | Insatsfaktorer | Produktion | Ramfaktorer |
|---|---|---|---|
| Dte1, DTe (2000)[^63] | OpEx[^64] | Levererad elkraft; Antal kunder | |
| Dte2, DTe (2000) | OpEx | Levererad elkraft; Antal kunder LSP[^65]; Antal kunder HSP[^66] | |
| Dte3, DTe (2000) | OpEx | Levererad elkraft; Antal kunder LSP; Antal kunder HSP; Nätverkslängd[^67][^68]; Antal nätstationer[^69] | |
| Dte4, DTe (2000) | OpEx | Levererad elkraft; Antal kunder LSP; Antal kunder HSP; Nätverkslängd; Antal nätstationer; Ledningslängd per kund | |
| Dte4, DTe (2000) | Totalkostnad[^70] | Levererad elkraft; Antal kunder | |
| SamNordiska modellen | Driftskostnader; Arbetsinsats (kh); Kapital (fysiskt); Nätförluster (GWh) | Levererad elkraft; Antal kunder; Nätverkslängd | |
| STEM 1-a testmodel[^71] | Driftskostnader; Kapitalkostnader[^72] | Antal kunder; Leverad HSP[^73]; Levererad LSP[^74] | Ledningslängd per kund; Installerad transformatoreffekt per kund |
| NUTEK 1993[^75] | Arbetsinsats (kh); Nätverkslängd HSP; Nätverkslängd LSP; Transformatorkapacitet (MVA) | Levererad HSP; Levererad LSP; Antal kunder HSP; Antal kunder LSP; Anläggningarnas utnyttjningstid; Toppbelastning (MW) | |
| Hjalmarsson and Veiderpass (1992) | Arbetsinsats (kh); Nätverkslängd HSP; Nätverkslängd LSP; Transformatorkapacitet (MVA) | Levererad HSP; Levererad LSP; Antal kunder HSP; Antal kunder LSP | |
| Hougaard (1994) (Fyra olika modellkombinationer) | Arbetsinsats (årsverk); Driftkostnad (ex personal); Total driftskostnad; Nätförluster; Kapital | Nätverkslängd; Levererad elkraft; Antal kunder | |
| Kittelsen (1994) | Arbetsinsats (kh); Energiförluster (MWh); Nätstationer; Ledningar (kkr); Varor och tjänster | Levererad elkraft; Antal kunder | Nätverkslängd |
| Kittelsen – alt. Modeller | Arbetsinsats (kh); Energiförluster (MWh); Nätstationer; Ledningar (kkr); Varor och tjänster | Maximal effekt (kW); Leverans till elverk och elintensiv industri; Leverans till annan näringsverksamhet; Leverans övrigt | Avståndsindikator[^76]; Korrosionsindex[^77]; Klimatindex |
| Nätavdelningens modell, Ek (1998) | Kostnad – drift resp. total (Én i alt) | Levererad HSP; Levererad LSP; Antal kunder HSP; Antal kunder LSP | Nätverkslängd LSP; Nätverkslängd HSP; Transformatorkapacitet (MVA) |
| NVE's modell | Arbetsinsats (kh); Nätförluster; Kapital (kkr) (ledn. og transf.); Varor och tjänster | Antal kunder; Levererad elkraft | Nätverkslängd |
| Sydkrafts modell | Nätverkslängd LSP; Nätverkslängd HSP; Nätstationer (MVA); Nätförluster (GWh); Kostnader för drift och underhåll + för mätning och rapportering | Levererad HSP; Levererad LSP; Antal kunder HSP; Antal kunder LSP | Antal meter ledning LSP per kund LSP |
| STEM huvudmodell i etapp 1 (bil 2, s. 7) | Driftkostnader; Kapital | Antal kunder; Levererad HSP; Levererad LSP | Ledningslängd per kund; Installerad transformatoreffekt per kund |
| Roos and Färe (Etapp 1) | Nätverkslängd LSP; Nätverkslängd HSP; Nätstationer (MVA); Nätförluster (GWh); Underhåll och driftkostnader (underhåll av kapitalet plus administration, avläsning, mätning mm) | Levererad HSP; Levererad LSP (ev. uppdelad på typkunder) (baserat på alternativ och på elanvändning) | Befolkningstäthet; Antal kunder |
| ELTA (Finnish Model) (Workshop 22.5.200) | Antal årsanställda; Nätverkslängd LSP; Nätstationer (kVA) | Levererad elkraft; Antal kunder; Väglängd | |
| HKKK (Helsinki School of Economics and Business Administration) proposal for potential I and O | Driftskostnader; Investeringar | Viktad (LSP/HSP) elkraftsleverans; Kvalitet: medelavbrottstid över tre år | Snödjup (genomsnitt); Skog (% skog); Viktat antal kunder (HSP/LSP); Kundtäthet (viktad nätverkslängd); Ändring i viktad elkonsumtion |
| Nätnyttomod. (STEM) | Kostnadsmått | Nätlängd LSP[^78]; Nätlängd HSP; Effekt | |
| Weyman-Johnes (1985) | Antal årsanställda | Antal kunder | Nätverkslängd; Transformatorkapacitet (MVA); Lev. elkraft; Max effekt; Kundtäthet; Andel industrikunder |

Effektivitetskrav på eldistribution i olika länders regleringar 2014. I tabell 22 redovisas svar på frågor ställda till olika länders regleringsmyndigheter om hur deras regleringar är utformade. Här redovisas svar på frågan om X-faktorn avser enbart OPEX, CAPEX eller både.

#### Tabell 22 – Effektivitetskrav i olika länders regleringar

| Land | Är en X-faktor applicerad på CAPEX? | Är en X-faktor applicerade på OPEX? |
|---|---|---|
| Österrike | Ja, företagsspecifika baserade på benchmarking och generell produktivitetsökning | Ja, företagsspecifika baserade på benchmarking och generell produktivitetsökning |
| Belgien | Nej | Ja, förhandlingar |
| Tjeckien | Nej | Ja, X-faktor på 2 % årligen |
| Tyskland | Ja | Ja |
| Danmark | Ja | Ja |
| Estland | Nej | Ja |
| Spanien | Ja | Ja |
| Finland | Nej | Ja |
| Storbritannien | Ja | Ja |
| Grekland | Nej | Nej |
| Ungern | Ja | Ja |
| Irland | Ja | Inget svar |
| Island | Nej | Nej |
| Italien | Nej | Ja |
| Lettland | Nej | Nej |
| Litauen | Nej | Ja |
| Norge | Ja | Ja |
| Polen | Nej | Ja |
| Portugal | Ja | Ja |
| Slovenien | Nej | Ja |
| Sverige | Nej | Ja |
| Nederländerna | Ja | Ja |

Källa: Ref. C13-IRB-16-03 CEER Internal Report on Investment Conditions in European Countries.

Översikten visar att av 22 svar så hade 10 länder, dvs nästan hälften karv på CAPEX och för OPEX ar det endast 3 som svarat nej (samt ett utan svar). Krav på enbart OPEX har 9 länder, dvs nej på CAPEX och ja på OPEX. Majoriteten av länderna har krav på både OPEX och CAPEX, dvs TOTEX.

## Noter

[^1]: DEA (Data Envelopment Analysis). SFA (Stochastic Frontier Analysis).

[^2]: Detta innebär att de totala kostnaderna för att producera de efterfrågande tjänsterna på en marknad (t ex ett geografiskt avgränsat distributionsområde) är lägre än den totala kombinerade kostnaden om två eller flera företag producerar samma kvantitet inom området.

[^3]: I texten används även operativ kostnad som synonym till löpande kostnad.

[^4]: Se avsnitt 8.

[^5]: Ett företag som är på fronten under en period kan pga. produktivitetsnedgång hamna innanför fronten i nästa period.

[^6]: EMV, källa från Finland här.

[^7]: Källa BundesNetzAgentur (Bnetz). http://www.bundesnetzagentur.de/cln_1431/DE/Sachgebiete/ElektrizitaetundGas/Unternehmen_Institutionen/Netzentgelte/netzentgelte-node.html

[^8]: Källa Tyskland. 60 % effektivitetsnivå utgör begränsning för kravet.

[^9]: David Bjurhall Fortum, Göran Hansson Värnamo Energi, Runde Nilsson EON, Anders Pettersson Svensk Energi och Göran Sörell Sundsvalls Energi.

[^10]: Per Agrell Sumicscid och Jörgen Hellström Umeå universitet.

[^11]: "Rationella nätkoncessioner för område – kriterier för 'lämplig enhet'", NUTEK-rapport 1997-11-04.

[^12]: En pristaksreglering är motiverad i verksamheter där det reglerade företagen kan påverka försäljningsvolymen och idealt sätta pris lika med marginalkostnad för att få allokativ effektivitet.

[^13]: För elnätsföretagen är den producerade volymen av tjänster i termer av antalet kunder, överförd el och uttagen effekt till övervägande del exogent bestämd till skillnad från t ex regleringen av telekomföretagen.

[^14]: Joskow P, "Incentive Regulation in Theory and Practice: electricity distribution and transmission networks", 2007 working paper.

[^15]: En produkt kan vara en tjänst inte enbart ett fysiskt föremål. Det förutsätter att det går att definiera produkten/tjänsten och mäta den och att även resursanvändningen tydligt kan definieras och mätas.

[^16]: Även benämnda Horndalseffekten efter ett stålverk i Västmanland där det inte gjordes några investeringar men där produktiviteten ändå höjdes successivt.

[^17]: Ett alternativ till företagsfusioner är att företag samarbetar kring olika funktioner som t ex inköp.

[^18]: Frontens förändring brukar benämnas som teknisk ändring.

[^19]: Russel Bertrand: "Although this may seem as a paradox, all science is dominated by the idea of approximation".

[^20]: Det senare ger mera information till respektive företag eftersom man kan få kunskap om vilken kostnadspost som ökar effektiviteten mest.

[^21]: En resurs som t ex luftledningar (km) eller antal stationer kan placeras som en output för att kompensera för distribution i glesbygd som ger högre kostnader per kund och överförd el. Men även ses som en restriktion på inputsidan.

[^22]: En liten påverkan via tariffen. Om man tillämpar en energibaserad tariff (öre/kWh) som är hög innebär det en högre kostnad för kunden. Men denna marginella kostnad är låg i förhållande till elpriset och elskatten.

[^23]: Fixed effect vs random effects.

[^24]: http://www.sumicsid.com/ och Bundesnetzagentur § 12 ARegV (Verordnung über die Anreizregulierung der Energieversorgungsnetze).

[^25]: Bogetoft and Otto, "Benchmarking with DEA, SFA and R", Springer 2011.

[^26]: Det finns andra varianter som "Corrected ordinary least square" COLS som används i England eller att man som i Norge använder en kombination av DEA och därefter en regression där olika miljövariabler ingår och som korrigerar mätetalen på effektivitet. I Finland används en metod, StoNED, som både är icke-parametrisk och stokastisk.

[^27]: En relativt ny översikt av både DEA och SFA ges i Bogetoft och Otto, Benchmarking with DEA, SFA and R, Springer 2011.

[^28]: En länk till en internetsite är: http://www.deazone.com/

[^29]: En forskningstidskrift som Journal of Productivity Analysis redovisar många sådana analyser. http://link.springer.com/journal/11123

[^30]: Se de olika modeller som används inom olika regleringar och studier (Bilaga 2).

[^31]: Ett motiv för att inte gå längre tillbaka i tiden är att kvaliteten på data var sämre under de första åren av insamling.

[^32]: Kostnaderna skiljer sig marginellt generellt sett men för vissa företag mera från årsrapportdata pga. leasing och andra flyttningar mellan operativa kostnader och kapitalkostnader.

[^33]: Tre Ei-rapporter (URL:er i ursprungsdokumentet): Elnätforetagens produktivitetsutveckling 2001_2006; EI_R2008_15; EI_R2010_11.

[^34]: Per Agrell respektive Jörgen Hellström.

[^35]: Konsulternas resultat finns tillgängliga på Ei:s hemsida.

[^36]: Det paradoxala resultatet att en investering i "ny" teknik (jordkabel) ger en tillbakagång i teknisk förändring (technological change).

[^37]: I det senare fallet leasades anläggningarna och kom då med som operativ kostnad år 2004, medan detta inte är fallet år 2012, vilket innebär att denna stora ändring troligen helt förklaras av en redovisningsmässig effekt.

[^38]: http://www.nve.no/no/Kraftmarked/Regulering-av-nettselskapene/Om-beregning-av-inntektsrammer/

[^39]: Räknat som antalsmedel blir det 7,3 % på OPEX och 4,4 % räknat på TOTEX.

[^40]: Resurserna är arbetade timmar (timmar), lågspänningsledningar (km), högspänningsledningar (km) och total transformatorkapacitet (kVA). Prestationerna är låg- respektive högspänningsel (MWh) och antal hög- respektive lågspänningsabonnemang.

[^41]: Modellen hade som resurser: ledningslängd i km uppdelat på hög- respektive lågspänning samt total transformatorkapacitet. Prestationerna utgjordes av volymen överför el uppdelat på hög- respektive lågspänning och antalet abonnemang också uppdelat i hög- respektive lågspänning.

[^42]: Från början en självkostnadsreglering som utvecklades till en avkastningsreglering.

[^43]: Överförd el i GWh, ledningslängder i km och förväntade avbrott i kronor.

[^44]: Personal i årsarbetskrafter, material och tjänster i kronor, kapital i kronor (bokförda värden) och faktiska leveransavbrott i kronor.

[^45]: För det genomsnittliga företaget ökade produktiviteten med 15,4 % under de sju åren vilket innebär en årlig ökning med 2,1 %.

[^46]: Den totala elkonsumtionen minskade i Sverige med 1,2 % mellan 2001 och 2002 (Källa: The Electricity Market 2003, Energimyndigheten).

[^47]: Elnätföretagens produktivitetsutveckling 2001 – 2006, Energimarknadsinspektionen 2008.

[^48]: Eftersom anställning och avsked är förknippat med kostnader som avgångsersättning, inlärningsperioder m.m. tenderar företag att i lågkonjunktur behålla till synes omotiverat mycket personal. Personalen används då mindre intensivt och produktiviteten sjunker följaktligen. När sedan konjunkturen vänder kan samma personal användas mer intensivt varpå produktiviteten ökar.

[^49]: Hjalmarsson och Walfridson, "Den fysiska kapitalbildningens betydelse för produktiviteten i svensk tillverkningsindustri", Ekonomisk debatt 1/92.

[^50]: Bilaga 6 till LU 2008, tabell 3.5 sid 106.

[^51]: Exklusive England är medelvärdet 2,0 och med ett vägt medel för de fyra perioderna i England med 4 % genomsnittligt krav blir det 2,5 %.

[^52]: För Holland krävde den holländske regleraren (DTe) år 2000 för perioden 2001-2003 25 % minskning i intäkterna. Kraven reviderades fyra gånger och slutligen fastställdes kravet till 10 % för de tre åren. Se Nillesen och Pollit, Journal of Regulatory Economics, 2007.

[^53]: Benämnd som D8-modell: D8(3+5).

[^54]: I Finland har 8 år satts som en realiseringstid för de operativa kostnaderna.

[^55]: Se bilaga 2 med bland annat aktuell information från CEER.

[^56]: Ett sådant förfaringssätt används t ex i den norska regleringen av elnätsföretagen, där fronten bildas av de fem senaste årens verksamhet.

[^57]: Företaget som får en så hög supereffektivitet att det precis ligger under gränsen för att exkluderas från fronten kommer dock att påverka andra företag.

[^58]: I dessa kostnader kan det finnas vissa avvikelser jämfört med de årsrapportdata som årligen rapporteras in till Ei. Det gäller främst leasingkostnader.

[^59]: Ett sådant exkluderingskriterium används i Tyskland vid bestämningen av mätetalen för effektivitet.

[^60]: Dvs. varje enskilt år har undersökts separat vad gäller vilka variabler som är mest signifikanta.

[^61]: Detta index har fördelen framför andra att det varken förutsätter kostnadsminimering som beteendeantagande eller att företagen är effektiva i sin produktion.

[^62]: Begreppen period och år används växelvis för att både visa att metodiken inte är begränsad till enbart årliga jämförelser samtidigt som det oftast handlar om jämförelser mellan årliga verksamhetsperioder.

[^63]: Netherlands Electricity Regulatory Service.

[^64]: OpEx (Operating Expenditure) = Rörliga kostnader = Material + tjänster + personal + övr. kostnader.

[^65]: LSP = lågspänning.

[^66]: HSP = högspänning.

[^67]: Substitutvariabel för kundernas geografiska spridning.

[^68]: En tolkning är att linjenätet är givet på kort sikt och att resurseffektiviteten mäter hur effektivt operatören driver den existerande kapitalapparaten. Linjelängd är dock inte en produktion som skall maximeras. Den viktigaste produktionen är leveranskvalitet, överförd energimängd till uttagsabonnent samt installation av tillräcklig transformatoreffekt för att möta toppbelastning.

[^69]: Substitut for nätverkskomplexitet.

[^70]: Totalkostnad = OpEx + avskrivning på materiella tillgångar.

[^71]: Den model som är utgångspunkt för etapp 2.

[^72]: Realkapitalkostnadsannuitet. Driftkostnaderna hämtas från resultaträkningen och kapitalkostnaderna beräknas som en årlig annuitet utifrån återanskaffningskostnaderna med viss bestämd avskrivningstid (eg 30 år med realränta på 4 %). Återanskaffningskostnaderna (NUAK) beräknas med hjälp av EBR-katalogen och företagens anläggningsregister.

[^73]: MWh (exkl. nätförluster).

[^74]: MWh (exkl. nätförluster).

[^75]: Variabler som hade en signifikant inverkan på produktionsresultatet.

[^76]: Restid i minuter till kommuncentret.

[^77]: från 1,0 till 4,0.

[^78]: Beräknad utifrån GIS-data för uttagspunkter med särskild algoritm.
