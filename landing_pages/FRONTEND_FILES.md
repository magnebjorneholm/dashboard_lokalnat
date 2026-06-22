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
3. **`pages/login.py` retireras helt** — `auth_dialog()` sköter all inloggning.
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
• CTA: Sign in / Open tool ↗         • render_sidebar(): företagsväljare,
  (auth-medveten)                      Back to Home ↗, logout
• egna designregler                           ▲
          │ login: _login_redirect →  switch_page in i verktyget
          └───────────────────────────────────┘
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
login_redirect = st.session_state.pop("_login_redirect", False)

# EN navigation för allt — Streamlit löser begärd sida från riktiga URL:en (pålitligt).
# landing_main är HIDDEN DEFAULT (äger "/", syns ej i verktygets sidofältsnav).
pg = st.navigation({
    "Revenue cap tool": [landing_main, *REVENUE_CAP_PAGES],
    "Standalone tools": STANDALONE_PAGES,
})

# Färsk login hoppar rakt in i verktyget (switch_page går ej i auth_dialogs fragment).
if login_redirect and check_auth():
    st.switch_page(REVENUE_CAP_PAGES[0])

if pg in TOOL_PAGES:
    # ZON 2 — verktyget, grindat av auth
    if not check_auth():
        st.switch_page(landing_main) # tool-URL utloggad (bokmärke) → landningen
    apply_tool_chrome()
    ... cookie/case-sync ...
    render_sidebar()                 # företagsväljare + Back to Home ↗ + logout
    pg.run()
else:
    # ZON 1 — landningen (pg == landing_main), oavsett auth
    pg.run()                         # landing.py kallar apply_landing_shell()
```

Varför en enad nav i stället för att läsa pathen själv: `st.context.url` är en
ögonblicksbild från anslutningstillfället och kan vara stale/`None` på första
körningen → opålitlig för zonval. `st.navigation` löser sidan korrekt internt, så
vi grenar på den returnerade sidan. landing_main är default + `visibility="hidden"`,
så bokmärkta tool-URL:er routar fortfarande (och bouncar till landningen om
utloggad), men landningen skräpar inte ner verktygets sidofältsnav.

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
| `frontend/common/landing_shell.py` | `apply_landing_shell()` — landningstema (full-bredd, **inget** sidofält, faded `login_pic`-bakgrund) + frusen topp-bar (wordmark + ankar-nav + auth-medveten CTA: **Sign in** / **Open tool ↗**) + helpers (landing_anchor/cards/heading/profile/footer). Anropas överst i `landing.py`. Bygger själv baren; `st.navigation`-menyn döljs (landningen är dess dolda default-sida). |
| `frontend/common/auth_dialog.py` | `auth_dialog()` + omflyttade formulär-renderare (login/register/reset/verify). Se `auth_dialog_forslag.md`. |
| `static/regumetrica_user_manual.pdf` | Asset; kopieras från `user_manual_latex/build/Regumetrica user manual.pdf` (serveras via `enableStaticServing`). |

### Att ändra

| Fil | Ändring |
|---|---|
| `streamlit_app.py` | Tvåzons-kontrollern ovan. Landningsgruppen bort ur inloggad nav; deep-link-redirect → `landing_home`. |
| `frontend/common/styling.py` | Dela `apply_styling()` i **`apply_base_styling()`** (fonts + branding, båda zonerna) och **`apply_tool_chrome()`** (sidofälts-lås + finputs, BARA zon 2). Sidofälts-låset får inte läcka in på den sidofältslösa landningen. |

### Att ta bort

| Fil | Varför |
|---|---|
| `pages/login.py` | Retireras — `auth_dialog()` sköter inloggningen; `landing_home` är landningsplats för deep-links. |

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
- **CTA** (fäst till höger via `.st-key-rm_signin`): **Sign in** (öppnar dialogen,
  navigerar inte) när utloggad, eller **Open tool ↗** (länk, ny flik) när inloggad.

Varje sektion i `landing.py` inleds med `landing_anchor("<id>")` (osynligt
scroll-mål). *Begränsning:* ingen levande scroll-spy (kräver JS som Streamlit inte
kör i huvuddokumentet); `:target` ger enkel highlight av den klickade länken.

---

## Auth-dialogen (sammanfattning)

Sign in sker i en `st.dialog` ovanpå landningen — ingen navigering bort.
Detaljer + pseudokod i **`auth_dialog_forslag.md`**. Centralt fynd (verifierat
mot Streamlit 1.55):

- Dialog-kroppen är en `st.fragment`. Widget-klick inuti → **fragment-rerun**,
  dialogen förblir öppen.
- `st.rerun(scope="fragment")` → byter vy **inom** dialogen (t.ex. login →
  väntar-på-verifiering), dialogen förblir öppen.
- `st.rerun()` (default `scope="app"`) → **stänger** dialogen och bygger om
  appen — exakt vad vi vill vid lyckad inloggning (nav byts till zon 2).

Cookie-deferralen (`_pending_auth_cookie`) är oförändrad; triggern flyttar bara
från en sida till dialogen.

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
- `auth_dialog_forslag.md` — auth-dialogen i detalj (struktur, pseudokod,
  verifierat rerun-beteende, körbart test `dialog_rerun_test.py`).
- `efter_möte.md`, `tankar.md` — ursprungliga diskussionsanteckningar.
