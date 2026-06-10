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

1. **Native topp-nav** via `st.navigation(..., position="top")` (inte ett eget
   `st.page_link`-bygge, inte Streamlit-sidofältet).
2. **Sektioner:** `Home` (hero), `Tools` (introduktion till alla verktyg),
   `Team` (team + kontakt). Tre nav-poster.
3. **`pages/login.py` retireras helt** — `auth_dialog()` sköter all inloggning.
4. **`contact.py` slås in i `team.py`**; **`user_manual.py` → `tools.py`**
   (manual-PDF:en bäddas in på Tools-sidan).
5. Faded `login_pic.jpg`-bakgrunden återanvänds som landningstema (utan
   sidofälts-krock).
6. Efter login: **bara tools** i sidofältet — inga landningssidor kvar där.

---

## Två zoner

```
ZON 1 — Landning (publik)            ZON 2 — Verktyget (bakom login)
────────────────────────            ──────────────────────────────
• native topp-nav (position=top)    • sidofält + Nordic Energy (som idag)
• inget Streamlit-sidofält          • BARA "Revenue cap tool" (1–5)
• faded login_pic-bakgrund          • render_sidebar(): företagsväljare + logout
• Sign in-CTA → auth_dialog()                 ▲
• egna designregler                           │ sign-in (dialog, scope="app" rerun)
          └───────────────────────────────────┘
```

`streamlit_app.py` är en **tvåzons-kontroller** som grenar på `check_auth()`.
Zonerna delar inte chrome.

## Kontrollflöde (`streamlit_app.py`)

```python
st.set_page_config(...)              # behålls
apply_base_styling()                 # BARA fonts + branding-borttagning (båda zonerna)
init_session_state()
try_restore_auth_from_cookie()

if check_auth():
    # ZON 2 — verktyget (i princip oförändrat)
    apply_tool_chrome()              # sidofälts-lås + Nordic Energy-finputs
    ... cookie/case-sync ...
    pg = st.navigation({"Revenue cap tool": APP_PAGES})   # sidofält, inga landningssidor
    render_sidebar()                 # företagsväljare + logout
    pg.run()
else:
    # ZON 1 — landningen, native topp-nav
    pg = st.navigation(LANDING_PAGES + APP_PAGES_HIDDEN, position="top")
    if pg in APP_PAGES_HIDDEN:
        st.switch_page(landing_home) # deep-link till skyddad sida → landningen
    else:
        pg.run()                     # varje landningssida kallar apply_landing_shell()
```

`position="top"` ger en native topp-navbar för landningssektionerna och inget
sidofält. Skyddade tool-sidor registreras fortfarande dolt (`visibility="hidden"`)
så att bokmärkta URL:er inte 404:ar — de bouncar nu till `landing_home` (inte
till en login-sida, den finns inte längre). Dolda sidor syns inte i topp-navet.

---

## Filer

### Sidor — zon 1 (design bor här, redigeras)

| Fil | Roll |
|---|---|
| `landing_pages/home.py` | **Home** — hero, tagline, intro, Sign in-CTA |
| `landing_pages/tools.py` *(ersätter `user_manual.py`)* | **Tools** — introduktion till alla verktyg + inbäddad manual-PDF-nedladdning |
| `landing_pages/team.py` | **Team** — team **+ kontakt** (sammanslagna) |
| ~~`landing_pages/contact.py`~~ | **Tas bort** — innehåll → `team.py` |
| ~~`landing_pages/user_manual.py`~~ | **Tas bort / döps om** → `tools.py` |

### Att skapa

| Fil | Roll |
|---|---|
| `frontend/common/landing_shell.py` | `apply_landing_shell()` — landningstema (full-bredd, **inget** sidofält, faded `login_pic`-bakgrund) + **Sign in-CTA** (knapp som öppnar `auth_dialog()`) + footer. Anropas överst på varje landningssida. *Bygger inte navbaren — det gör `st.navigation(position="top")`.* |
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

## Topp-navbar & Sign in

`st.navigation(LANDING_PAGES, position="top")` ritar den native topp-navbaren med
en post per sektion (Home / Tools / Team). Den kan bara innehålla *sidor* — så
**Sign in** (som öppnar en dialog, inte navigerar till en sida) renderas av
`apply_landing_shell()` som en prominent CTA i sidinnehållet (t.ex. hero + en
fast knapp högt upp), inte som en nav-post.

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
