# Landing — arkitektur & ombyggnadsspec (Alt B, Streamlit v1)

Pekarfil + spec. Ge en framtida Claude-konversation den här för att ladda
kontext kring landningssidornas frontend.

> **Bakgrund (chef-möte):** landningssidorna ska vara ett **eget lager FÖRE**
> verktyget — inte en gren i samma sidofält som "Revenue cap tool". Flödet blir
> **landningssida → sign-in → verktyg**. Eftersom landningen ligger *före*
> inloggning behöver den **inte** följa verktygets konventioner (låst sidofält,
> Nordic Energy-chrome).
>
> Detta är **v1 i Streamlit (Alt B)**. En senare omskrivning till
> React + Next.js + Tailwind med ny backend (Alt A) ersätter denna zon helt —
> v1 hålls därför medvetet enkel.

## Låsta beslut

1. **En enda landningssida** (`landing_pages/landing.py`) med tre **ankrade
   sektioner** staplade vertikalt: `#home` (hero), `#tools` (alla verktyg),
   `#team` (team + kontakt). Topp-navens länkar **scrollar** till respektive
   sektion — ingen sidväxling, ingen rerun.
2. **Egen topp-bar** (`landing_shell.py`): wordmark + ankar-nav (Home/Tools/Team)
   fästa till vänster, Sign in-CTA till höger. Den native `st.navigation`
   topp-naven **döljs med CSS** (den finns kvar enbart för att registrera/köra
   sidor och för deep-link-bouncen).
3. **`pages/login.py` retireras helt** — den helsides-grinden `render_auth_gate()`
   (`auth_page.py`) sköter all inloggning, visad i verktygsfönstret när man är utloggad.
4. **`contact.py` slås in i `team.py`**; **`user_manual.py` → `tools.py`**
   (manual-PDF:en bäddas in på Tools-sidan).
5. Faded `login_pic.jpg`-bakgrunden återanvänds som landningstema (utan
   sidofälts-krock).
6. Efter login: **bara tools** i sidofältet — inga landningssidor kvar där.

---

## Två zoner

```
ZON 1 — Landning (publik)            ZON 2 — Verktyget (auth-grindat)
────────────────────────            ──────────────────────────────
• egen topp-bar, inget sidofält      • sidofält + Nordic Energy (som idag)
• faded login_pic-bakgrund           • "Revenue cap tool" + "Standalone tools"
• CTA: Open tool (alla, ny flik)   • render_sidebar(): företagsväljare,
• egna designregler                    Back to Home, logout
          │                                   ▲
          │ Open tool öppnar verktygs-      │ utloggad → sign-in-grind
          └ fönstret (ny flik); login ───────┘ in place (render_tool_gate)
            sker i grinden där
```

`streamlit_app.py` är en **route-baserad tvåzons-kontroller**: zonen avgörs av
URL:en (vilken sida `st.navigation` returnerar), inte av `check_auth()`. Auth
grindar bara verktygssidorna. Det gör att en inloggad användare kan ha landningen
i ett fönster och ett verktyg i ett annat samtidigt. Zonerna delar inte chrome.

## Kontrollflöde (`streamlit_app.py`)

```python
st.set_page_config(...)              # behålls
apply_base_styling()                 # BARA fonts + branding-borttagning (båda zonerna)
init_session_state()
try_restore_auth_from_cookie()

# EN navigation för allt — Streamlit löser begärd sida från riktiga URL:en (pålitligt).
# landing_main är HIDDEN DEFAULT (äger "/", syns ej i verktygets sidofältsnav).
pg = st.navigation({
    "Revenue cap tool": [landing_main, *REVENUE_CAP_PAGES],
    "Standalone tools": STANDALONE_PAGES,
})

if pg in TOOL_PAGES:
    # ZON 2 — verktyget, grindat av auth
    if not check_auth():
        render_tool_gate()           # utloggad: sign-in-grind in place (ingen bounce);
        st.stop()                    # lyckad login → rerun → samma fönster visar verktyget
    apply_tool_chrome()
    ... cookie/case-sync ...
    render_sidebar()                 # företagsväljare + Back to Home + logout
    pg.run()
else:
    # ZON 1 — landningen (pg == landing_main), oavsett auth
    pg.run()                         # landing.py kallar apply_landing_shell()
```

Varför en enad nav i stället för att läsa pathen själv: `st.context.url` är en
ögonblicksbild från anslutningstillfället och kan vara stale/`None` på första
körningen → opålitlig för zonval. `st.navigation` löser sidan korrekt internt, så
vi grenar på den returnerade sidan. landing_main är default + `visibility="hidden"`,
så bokmärkta tool-URL:er routar fortfarande (och visar sign-in-grinden in place om
utloggad — ingen bounce), men landningen skräpar inte ner verktygets sidofältsnav.

---

## Filer

### Sidor — zon 1 (design bor här, redigeras)

| Fil | Roll |
|---|---|
| `landing_pages/landing.py` | **Hela landningen** — en sida, tre ankrade sektioner: `#home` (hero, stats, feature-cards), `#tools` (registry-driven verktygsindex + manual-länkar), `#team` (profiler + kontakt). Varje sektion inleds med `landing_anchor("<id>")`. |
| ~~`landing_pages/home.py` / `tools.py` / `team.py`~~ | **Borttagna** — sammanslagna till `landing.py`. |

### Att skapa

| Fil | Roll |
|---|---|
| `frontend/common/landing_shell.py` | `apply_landing_shell()` — landningstema (full-bredd, **inget** sidofält, faded `login_pic`-bakgrund) + frusen topp-bar (wordmark + ankar-nav + en enda CTA: **Open tool** för alla, ny flik) + helpers (landing_anchor/cards/heading/profile/footer). Anropas överst i `landing.py`. Bygger själv baren; `st.navigation`-menyn döljs (landningen är dess dolda default-sida). |
| `frontend/common/auth_page.py` | `render_auth_gate()` — helsides sign-in-grind (glas-kort över faded `login_pic`, transparent header, dolt sidofält) + formulär-renderare (login/register/reset/verify). Visas i verktygsfönstret när man är utloggad. Ersatte den tidigare `auth_dialog.py` (popup); se historiska `auth_dialog_forslag.md`. |
| `static/regumetrica_user_manual.pdf` | Asset; kopieras från `user_manual_latex/build/Regumetrica user manual.pdf` (serveras via `enableStaticServing`). |

### Att ändra

| Fil | Ändring |
|---|---|
| `streamlit_app.py` | Tvåzons-kontrollern ovan. Landningsgruppen bort ur inloggad nav; deep-link-redirect → `landing_home`. |
| `frontend/common/styling.py` | Dela `apply_styling()` i **`apply_base_styling()`** (fonts + branding, båda zonerna) och **`apply_tool_chrome()`** (sidofälts-lås + finputs, BARA zon 2). Sidofälts-låset får inte läcka in på den sidofältslösa landningen. |

### Att ta bort

| Fil | Varför |
|---|---|
| `pages/login.py` | Retireras — `render_auth_gate()` (`auth_page.py`) sköter inloggningen i verktygsfönstrets grind. |

### Oförändrat

`pages/1..5_*.py` (verktyget), hela domänlagret (`calculations/`, `pipeline/`,
`config/`, `data_loaders/`), `auth/firebase_auth.py` (samma metoder anropas).

---

## Topp-bar, ankar-nav & Sign in

Landningen är `st.navigation`s **dolda default-sida**, så dess sidofältsnav är
gömd (`apply_landing_shell` döljer hela sidofältet via CSS). Hela baren ritas i
stället av `apply_landing_shell()`:

- **Wordmark + ankar-nav** (`.rm-topbar`, fixerad till vänster i stHeader-baren):
  `<a href="#home">` / `#tools` / `#team`. `html{scroll-behavior:smooth}` ger den
  mjuka glidningen; `.rm-anchor{scroll-margin-top}` håller målet fritt från baren.
- **CTA** (fäst till höger via `.st-key-rm_signin`, namnet behållet som CSS-hook):
  en enda **Open tool** (länk, ny flik) för alla. Verktyget öppnas i eget
  fönster; är man utloggad sker inloggningen i det fönstrets sign-in-grind.

Varje sektion i `landing.py` inleds med `landing_anchor("<id>")` (osynligt
scroll-mål). *Begränsning:* ingen levande scroll-spy (kräver JS som Streamlit inte
kör i huvuddokumentet); `:target` ger enkel highlight av den klickade länken.

---

## Sign-in-grinden (sammanfattning)

Sign in sker på en **helsida**, `render_auth_gate()` i `auth_page.py`, visad i
verktygsfönstret när man är utloggad (controllern kallar den i stället för att
bounca till landningen). Den ersatte den tidigare popup-dialogen (vars
rerun-mekanik finns historiskt beskriven i `auth_dialog_forslag.md`):

- Ingen `st.dialog` och inga fragment-reruns längre. Vy-byten (login →
  vänta-på-verifiering, reset) sker via session-flaggor (`_auth_step`) + vanlig
  app-rerun, eftersom det inte finns någon dialog att hålla öppen.
- En helsida har ingen stäng-X: man loggar in eller kommer inte in. Sidan ritar
  glas-kortet över faded `login_pic`-bakgrunden (`apply_auth_backdrop`), gör
  `stHeader` transparent och döljer sidofältet.
- Vid lyckad, verifierad login: `st.rerun()` (app-scope) → auth passerar →
  controllern renderar verktyget i samma fönster (ingen `switch_page`).

Cookie-deferralen (`_pending_auth_cookie`) är oförändrad: controllern skriver
cookien så fort auth passerar (efter login-rerun), innan verktyget renderas.

---

## Designsystem (återanvänds — ändra inte utan skäl)

| Fil | Roll |
|---|---|
| `config/colors.py` | `COLORS`, `CHART_COLORS`, `get_plotly_template()` — enda färgkällan |
| `.streamlit/config.toml` | `enableStaticServing = true` (PDF) + temafärger. **Obs:** faktisk Streamlit-version i venv är **1.55.0** (kommentaren i filen säger 1.52 — inaktuell). |
| `pages/login.py` | (Tills den tas bort) referensmönster för faded-bakgrunds-CSS som flyttas in i `landing_shell.py` |

## Ram (läs — ändra inte)

| Fil | Roll |
|---|---|
| `CLAUDE.md` | "Nordic Energy"-identitet. **Gäller zon 2.** Zon 1 (landningen) får egna regler. |
| `ARCHITECTURE.md` | Lagerdiagram + projektets helhet |

---

## Öppna punkter (uppskjutna)
- Landningens faktiska copy (hero-text, tools-beskrivningar, team-text).
- Om verktygszonen ska ha en väg *tillbaka* till landningen (logo-länk), eller
  om logout → `landing_home` räcker. *(Uppskjutet — beslutas senare.)*

## Se även
- `auth_dialog_forslag.md` — **historisk**: den tidigare popup-dialogen i detalj
  (struktur, pseudokod, verifierat rerun-beteende). Inloggningen är numera en
  helsida (`auth_page.py`), så dokumentet beskriver inte längre nuläget.
- `efter_möte.md`, `tankar.md` — ursprungliga diskussionsanteckningar.
