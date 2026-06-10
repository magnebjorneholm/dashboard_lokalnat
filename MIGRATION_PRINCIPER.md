# Migrationsprinciper — att inte translitterera Streamlit

> Konceptuell vägledning inför en eventuell migration av Regumetrica från
> Streamlit till **React (med Python-API) + Next.js + Tailwind CSS**.
>
> Syftet är att namnge och undvika den vanligaste arkitektoniska fällan:
> att översätta *implementationen* istället för *avsikten*.

---

## Kärnproblemet

Vid en migration mellan radikalt olika ramverk är frestelsen att tänka:

> ❌ **"Streamlit ⇒ React + Next.js + Tailwind"** — översätt komponent för komponent.

Det rätta tänkesättet är:

> ✅ **"Hur bygger vi det Streamlit gör *konceptuellt* (ramverksoberoende) i React + Next.js + Tailwind?"**

Den första ansatsen bär omedvetet med sig Streamlits artefakter in i React. Resultatet
"luktar Streamlit" även om det är skrivet i React — man har bytt syntax men behållit
den främmande arkitekturens fotavtryck.

---

## Begreppen som beskriver fällan

### Transliteration vs. reimplementation
Att **translitterera** är att översätta kod rad-för-rad / komponent-för-komponent och
bära med sig källans struktur och idiom. Att **reimplementera** är att bygga utifrån
vad systemet egentligen *ska göra*. Målet är reimplementation — inte transliteration.

Folkligt: man riskerar att skapa **"Streamlit-flavored React"** och *"port:a den
accidental komplexiteten"*.

### Essential vs. accidental complexity
*(Fred Brooks, "No Silver Bullet")* — den viktigaste distinktionen:

| Typ | Vad det är | Ska migreras? |
|-----|------------|---------------|
| **Essential complexity** | Det appen *konceptuellt är*: domänmodellen och den underliggande affärslogiken — det som skulle gälla oavsett ramverk | **Ja** — ramverksoberoende, ska bäras över |
| **Accidental complexity** | Allt som bara finns *för att det är Streamlit*: `st.session_state`, top-to-bottom re-run-modellen, widget-state, `st.rerun()` | **Nej** — ersätts av Reacts egna idiom |

Den naiva migrationen förväxlar de två och bär över Streamlits artefakter som om de vore
domänen.

### Leaky abstraction
När källteknologins särdrag "läcker" in i målet. Exempel: Streamlits re-run-modell läcker
in i React om man försöker återskapa `session_state` istället för att använda Reacts
state / Server Components.

---

## Hur man undviker det — designpraxisen

### 1. Model-first / domain-driven migration
Extrahera **domänmodellen** (kärnabstraktionerna) först, oberoende av båda ramverken.
Låt sedan *både* gammalt och nytt UI vara tunna adaptrar ovanpå den.

> Idealt är kärnlogiken redan isolerad i ett rent lager utan UI-/ramverksimporter.
> **Det lagret är den ramverksoberoende kärnan och ska bevaras** (eller exponeras via
> Python-API:t). Det är bara presentations- och state-lagret som faktiskt ska
> reimplementeras. Om backend också ska göras om är detta tillfället att rita gränsen
> mellan domän och presentation tydligt — så att kärnan står på egna ben och båda UI:n
> blir tunna adaptrar ovanpå den.

### 2. Anti-corruption layer (ACL)
*(Domain-Driven Design, Eric Evans)* — ett medvetet gränsskikt som hindrar källsystemets
modell från att "korrumpera" målsystemets.

> Här blir **Python-API:t din ACL**: det exponerar domänen i rena termer (scenarier,
> beräkningar, resultat) så att React aldrig behöver känna till att det en gång fanns
> Streamlit-widgets.

### 3. Strangler fig pattern
*(Martin Fowler)* — ersätt det gamla inkrementellt utan att translitterera: bygg nytt
runt om och låt det gamla vika undan bit för bit, mot ett rent måldesign.

---

## Sammanfattning

**Fällan att undvika:** att *translitterera accidental complexity* och bygga
*"Streamlit-flavored React"* med *leaky abstractions*.

**Det du vill göra istället — en model-first reimplementation:**

1. Identifiera **essential complexity** — domänmodellen och kärnlogiken.
2. Exponera den genom ett **anti-corruption layer** — Python-API:t.
3. Bygg Reacts UI utifrån *vad appen är* — inte utifrån *hur Streamlit råkade bygga det*.

> **Tumregel:** Varje gång en designbeslut motiveras med "så gjorde vi det i Streamlit" —
> stanna upp. Det är en accidental-complexity-artefakt som inte ska följa med.
