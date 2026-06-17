# Övergången till ett tvåsidigt effektiviseringskrav

*Status: Denna not återger vår tolkning av den föreslagna mekaniken, given den information
som Energimarknadsinspektionen har offentliggjort fram till juni 2026. Den beskriver inte en
fastställd modellspecifikation. De konkreta parametervärdena är våra arbetsantaganden, och de
magnituder som följer av dem är betingade på dessa antaganden.*

## Syfte

Syftet med denna not är att förklara den föreslagna övergången från dagens enkelsidiga
effektiviseringskrav till ett tvåsidigt krav, och att göra det på ett sätt som skiljer
mellan vad Energimarknadsinspektionen har signalerat och vad som är våra arbetsantaganden.
Läsaren antas känna till DEA-skattningen och dagens kravmetod. Vi beskriver mekaniken. De
magnituder som anges är betingade på en arbetsspecifikation som redovisas uttryckligen i ett
eget avsnitt, eftersom Energimarknadsinspektionen ännu inte har publicerat parametervärdena.

## Dagens mekanik som referenspunkt

I dagens modell mäts varje bolags effektivitet mot fronten, alltså mot det mest effektiva
bolaget (E = 1). Potentialen definieras som avståndet till fronten, 1 − E_i, vilket alltid
är icke-negativt. Potentialen trunkeras till intervallet [0,1624, 0,30], skalas med en
kundandel på 0,50 och en realiseringsfaktor 4/8 (potentialen ska realiseras över 8 år men
kravet sätts per fyraårig tillsynsperiod), och annualiseras. Hela kedjan kan skrivas

> årligt krav = (1 + clip(1 − E_i, 0,1624, 0,30) × 0,50 × 4/8)^(1/4) − 1

Två egenskaper är avgörande för förståelsen av förändringen. För det första är
referenspunkten fronten, och potentialen därför alltid icke-negativ, vilket innebär att
samtliga bolag får ett avdrag. För det andra ger golvet i trunkeringen (0,1624,
baklängesräknat till exakt 1 procent per år) att även frontbolaget får ett avdrag på minst
1 procent per år. Detta golv fungerar i praktiken som ett generellt effektiviseringskrav som
läggs på alla bolag.

## Den principiella förändringen

Energimarknadsinspektionen avser att ändra två saker. Referenspunkten flyttas från fronten
till tredje kvartilen, alltså till effektivitetsnivån vid den 75:e percentilen (E75),
beräknad exklusive outliers. Och tecknet kan bli negativt: gapet mäts mot E75 i stället för
mot fronten, och kan vara positivt eller negativt.

Det signerade gapet definieras som E75 − E_i. Ett bolag under E75 är mindre effektivt än
tröskeln och får ett positivt krav, alltså ett avdrag. Ett bolag exakt vid E75 får ett
nollkrav, vilket motsvarar full kostnadstäckning. Ett bolag över E75 får ett negativt krav,
alltså ett tillägg på intäktsramen. Eftersom tröskeln ligger vid den 75:e percentilen är det
per definition den översta fjärdedelen av bolagen som får full kostnadstäckning eller mer.
Valet av tredje kvartilen som referens är lånat från den brittiska regleringen (Ofgems
RIIO-ED2).

Tröskeln E75 är rörlig och relativ. Den räknas om varje tillsynsperiod ur den aktuella
tvärsnittsfördelningen av effektivitetspoäng, vilket innebär att tröskeln höjs automatiskt
när branschen som helhet blir effektivare. Det är denna självkalibrering som ersätter dagens
golv. I och med att golvet och det fasta outlierkravet tas bort får den översta fjärdedelen
inte längre något automatiskt avdrag, och det finns därmed inget separat generellt
effektiviseringskrav i den nya modellen.

## Beräkningskedjan är oförändrad

Omvandlingen från gap till årligt krav är i allt väsentligt densamma som i dagens modell.
Det signerade gapet kapas till ett intervall, skalas med kundandelen och realiseringsfaktorn,
och annualiseras över tillsynsperioden:

> gap = E75 − E_i
>
> årligt krav = (1 + clip(gap, −cap, +cap) × sharing × tillsynsperiod/realiseringstid)^(1/tillsynsperiod) − 1

Det enda som har ändrats är alltså definitionen av gapet och att tecknet kan bli negativt.
Skalningen, kapningen och annualiseringen behåller sin form från den tidigare metoden. Detta
gör att den nya och den gamla metoden kan jämföras steg för steg, och att skillnaden i utfall
kan hänföras enbart till referensbytet och teckenbytet.

## En strukturell egenskap: tvåsidigheten är skev

Att kravet är tvåsidigt innebär inte att belöningar och avdrag är symmetriska i storlek.
Effektivitetspoängen är per definition kapad vid 1,0, och tröskeln E75 ligger nära toppen, i
vår tvärsnittsdata på 0,93. Det mest effektiva bolaget kan därför ligga som mest omkring 0,07
effektivitetsenheter över tröskeln, medan ett ineffektivt bolag kan ligga betydligt längre
under den. Belöningssidan är alltså strukturellt begränsad oavsett var taket sätts, medan
avdragssidan kan bli stor. Under arbetsspecifikationen nedan blir den största belöningen
omkring −0,43 procent per år och det största avdraget +1,82 procent per år. Ett symmetriskt
tak på det signerade gapet binder i praktiken bara på avdragssidan. Denna skevhet är en
strukturell följd av att effektiviteten är kapad vid fronten och tröskeln ligger nära den;
den är inte ett resultat av en asymmetriskt vald parameter.

## Arbetsspecifikation

Följande parametervärden är inte publicerade av Energimarknadsinspektionen. Vi har låst dem
som arbetsantaganden, valda för att spegla dagens beräkningskedja och för att förankra
mekaniken numeriskt mot den nuvarande metoden. Vi bedömer dem som rimliga, men samtliga
magnituder i denna not är betingade på dem.

1. **Kundandel (sharing): 0,50**, som i dagens modell.
2. **Realiseringstid 8 år, tillsynsperiod 4 år**, alltså en realiseringsfaktor 4/8.
   Realiseringstiden på 8 år är bekräftad av Energimarknadsinspektionen; tillsynsperiodens
   längd följer regleringen.
3. **Tak på det signerade gapet: 0,30, symmetriskt.** Värdet är valt så att det största
   avdraget blir +1,82 procent per år, samma tak som i dagens metod. Takets nivå är
   uttryckligen en av Energimarknadsinspektionens öppna frågor.
4. **Funktionsform: linjär i det kardinala gapet E75 − E_i.** Energimarknadsinspektionens
   material fastställer inte funktionsformen. Vi bedömer den kardinala formen som rimlig,
   eftersom effektivitetspoängen klustrar nära toppen och en rangbaserad magnitud därför
   skulle förstora försumbara skillnader mellan i praktiken likvärdiga bolag.
5. **Golv och fast outlierkrav: borttagna.** Full kostnadstäckning vid tredje kvartilen
   ersätter dagens golv. Outliers, som kapas till E_i = 1,0 liksom alla frontbolag, får samma
   tillägg som övriga bolag på fronten; de utesluts endast ur den percentil som sätter
   tröskeln.

Symmetrin mellan belöning och avdrag, kundandelens existens i ny form, samt hanteringen av
golv och outliers är alla ospecificerade i Energimarknadsinspektionens material. Våra val
ovan bör därför läsas som arbetshypoteser tills modellspecifikationen publiceras.

## Sammanfattning

1. Referenspunkten flyttas från fronten (E = 1) till tredje kvartilen (E75, rörlig och
   relativ), och gapet E75 − E_i blir signerat.
2. Bolag under tröskeln får avdrag, bolag vid tröskeln full kostnadstäckning, bolag över
   tröskeln tillägg. Den översta fjärdedelen får full täckning eller mer.
3. Dagens golv och fasta outlierkrav tas bort. Golvet fungerade i praktiken som ett generellt
   effektiviseringskrav; i den nya modellen finns inget sådant.
4. Beräkningskedjan (skalning, kapning, annualisering) är oförändrad. Endast gapdefinitionen
   och tecknet har ändrats.
5. Tvåsidigheten är strukturellt skev: belöningar är små per konstruktion, avdrag kan nå
   dagens tak.
6. Parametervärdena är våra arbetsantaganden, inte Energimarknadsinspektionens beslut.
   Magnituderna är betingade på dem, och takets nivå är en öppen regleringsfråga.
