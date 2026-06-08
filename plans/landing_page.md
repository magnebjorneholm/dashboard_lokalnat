# Plan: Landningssida i Streamlit med `landing_pages/` och `st.navigation()`

## Context

Regumetrica byggs i nuläget endast som en dashboard (revenue cap-beräkning för svenska elnätsföretag). Chefen vill att `regumetrica.com` blir en *landningssida* där dashboarden är **ett** av flera framtida verktyg. På sikt byts frontend till något bättre (Next.js / Astro), men i nuläget ska allt fortsätta köras som **en** Streamlit-process för konsistens med appen och enkelhet i deploy.

Mycket viktig upptäckt under utforskning: **appen använder redan `st.navigation()` + `st.Page()`** i [streamlit_app.py:331-391](streamlit_app.py#L331-L391). Vi behöver alltså *inte* migrera bort från auto-discovery — det är gjort. Vi behöver bara **utöka** den existerande navigationen med en publik gren som exponerar landningssidor.

---

## Svar på de tre frågorna

### Fråga 1 — Hur routas användarna från landningssidan till dashboarden?

**Tekniskt:** Dashboarden kräver Firebase-auth, så vägen går alltid via login först (för nya användare). Tre tekniker:

| Teknik | Användning | Var den passar |
|---|---|---|
| `st.switch_page(login_page)` | Programmatisk navigation från knapp/callback | Internlogik, t.ex. logout som hoppar tillbaka till landningssidan |
| `st.page_link(...)` | Snyggt formaterad länk-widget | Inbäddade länkar i text |
| `st.navigation(position="top")` | Inbyggd top-nav-meny | **Huvudmekanism** för att navigera mellan landningssidor och in i verktyget |

Alla tre lever inom **samma Streamlit-process** — ingen extern redirect, inga subdomäner.

**Visuellt — så här blir det:**

- **Publik/oautentiserad:** Top-nav (`position="top"`), **ingen sidebar**, marknadsförings-layout. Top-nav-länken längst till höger heter "Sign in" och leder till login-sidan.
- **Inloggad användare på landningssidan:** Samma top-nav som publik, **men** "Sign in"-länken byts dynamiskt till "Open tool" som leder direkt till `case_manager` (ingen reauth — Firebase-cookien är fortfarande giltig). *Inga aggressiva CTA-knappar i hero* — landningssidan förblir informativ.
- **Inne i dashboarden:** Befintlig sidebar med företagsväljare + logout, linjärt flöde. Oförändrat.

Övergången är abrupt och tydlig: när användaren klickar "Sign in" / "Open tool" *byter hela layouten skepnad*. Det signalerar tydligt "nu är du i produkten".

**Alternativ jag valde bort:**
- *Auto-redirect inloggade besökare till dashboarden* — du ville uttryckligen att landningssidan ska visas även för inloggade.
- *Subdomän (`app.regumetrica.com`)* — överkurs nu, sparas till frontend-bytet.

### Fråga 2 — Kan vi i framtiden ha fler "verktyg" likt dashboarden?

**Ja.** Modulregistret i [config/module_registry.py](config/module_registry.py) är *inte* lämpligt för detta — där betyder "modul" en del av *revenue cap-beräkningen* (M1-M7), inte ett självständigt verktyg. Ett nytt verktyg är en separat sidserie.

Tre realistiska arkitekturer:

| Arkitektur | Hur det ser ut | När det passar |
|---|---|---|
| **A. Allt i samma repo, samma Streamlit-process** | `pages/` (revenue cap), `pages_tariff/` (nytt verktyg), `landing_pages/`. `st.navigation()` exponerar olika sidlistor beroende på `?tool=` query param eller val på landningssida. | **Nu och nästa verktyg.** Enklast. Delad auth, delad branding, en deploy. |
| **B. Separata Streamlit-deploys på subdomäner** | `regumetrica.com` (landningssida), `revenue-cap.regumetrica.com`, `tariff.regumetrica.com`. Varje verktyg = eget repo eller egen mapp. | När verktygen blir tunga, team blir större, eller releasecykler divergerar. |
| **C. Hybrid via Next.js-landningssida** | Slutmål enligt din plan: landningssida som Next.js på `regumetrica.com`, dashboards kvar som Streamlit-deploys på subdomäner. | Senare frontend-byte. |

**Förberedelse i denna plan:**

Strukturen `landing_pages/` ligger som en *systermapp* till `pages/`. När verktyg 2 kommer:
1. Lägg till `pages_tariff/` med dess Streamlit-sidor.
2. Lägg till `st.Page()`-objekt för dessa i [streamlit_app.py](streamlit_app.py).
3. Modifiera autentiserade greningen så valet av sidlista görs på `st.query_params.get("tool")` eller på användarens behörighet.
4. På landningssidan: lägg till en "Products"-sektion (ny `landing_pages/products.py`) som listar verktygen.

Detta är inte byggt nu — men strukturen är förberedd för det.

### Fråga 3 — Hur ersätts och vart hamnar innehållet i nuvarande `streamlit_app.py`?

**Kort svar: ingenting flyttas ut. Filen utökas.**

Inventering av [streamlit_app.py](streamlit_app.py):

| Block | Rader (ca) | Påverkan |
|---|---|---|
| `st.set_page_config(...)` | 29-34 | Oförändrad. |
| `apply_styling()` | 37 | Oförändrad. |
| `init_session_state()` | 40 | Oförändrad. |
| Företagsnamns-cachers | 43-105 | Oförändrad. |
| `try_restore_auth_from_cookie()` | 100-152 | Oförändrad. |
| `try_restore_case_from_cookie()`, `_sync_case_cookie()` | ~155-215 | Oförändrad (körs bara när autentiserad). |
| `render_sidebar()` | 217-324 | Oförändrad. **Logout-callback** ([rad 308-324](streamlit_app.py#L308-L324)) ändras: efter `sign_out()` → `st.switch_page(landing_home)` istället för nuvarande implicit rerun till login. |
| `st.Page()`-definitioner | 331-354 | **Utökas** med 4 nya landningssidor. |
| Huvud `if check_auth(): ... else: ...` | 364-391 | **`else`-grenen byggs om** för att exponera landningssidor istället för att tvinga login. **`if`-grenen** får dynamisk "Open tool"-länk i top-nav när landningssida visas för inloggad användare. |

Inget innehåll behöver flyttas till någon annan fil.

---

## Föreslagen mappstruktur och filer

```
dashboard_lokalnat/
├── streamlit_app.py                 # MODIFIED: utökad st.Page-lista + omskriven huvudgrening
├── pages/                           # OFÖRÄNDRAD (login + dashboard-flöde)
│   ├── login.py
│   ├── 1_create_and_select_case.py
│   ├── 2_case_setup.py
│   ├── 3_specification.py
│   └── 4_revenue_frame.py
├── landing_pages/                   # NY
│   ├── __init__.py
│   ├── home.py                      # Welcome + intro
│   ├── user_manual.py               # PDF-nedladdning + (framtida) interaktiv version
│   ├── team.py                      # Meet the team
│   └── contact.py                   # Kontaktinfo
├── static/                          # NY (om saknas) — Streamlit static serving är redan på
│   └── regumetrica_user_manual.pdf  # Kopierad/byggd från user_manual_latex/build/
└── frontend/common/
    └── landing_styling.py           # NY: hjälpare som döljer sidebar + tillämpar landningssidans CSS
```

### Innehåll per fil

**`landing_pages/home.py`** — startsidan
- `apply_landing_styling()` överst (döljer sidebar)
- Hero: stor rubrik "Regumetrica", tagline ("Web-based tool for computing scenario-based revenue frames")
- Intro-stycke: 2-3 meningar om vad plattformen gör för svenska elnätsföretag
- Ingen aggressiv CTA-knapp (per ditt val). Användare som vill in i verktyget använder top-nav.
- Eventuellt: 3-4 nyckelfunktioner i st.columns

**`landing_pages/user_manual.py`** — användarmanual
- `apply_landing_styling()`
- Rubrik "User Manual"
- Kort beskrivning
- **PDF-nedladdning:** länk till `/app/static/regumetrica_user_manual.pdf` via `st.link_button` eller `st.download_button` (läser bytes från `static/`)
- Placeholder-sektion "Interactive version coming soon" — kan i framtiden konverteras från LaTeX till web (separat projekt)

**`landing_pages/team.py`** — Meet the Team
- `apply_landing_styling()`
- Rubrik "Meet the Team"
- Team-grid (st.columns med foto/namn/titel/kort bio) — innehåll fylls i av dig

**`landing_pages/contact.py`** — Contact
- `apply_landing_styling()`
- Rubrik "Contact"
- Kontaktinformation (email, eventuellt formulär via `st.form` som mailar via en backend-funktion — kan börja som ren info-sida)

**`frontend/common/landing_styling.py`** (NY)
```python
import streamlit as st

def apply_landing_styling() -> None:
    """Hide sidebar, apply landing-page CSS. Call at top of each landing page."""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .block-container { max-width: 1100px; padding-top: 3rem; }
        </style>
    """, unsafe_allow_html=True)
```

Mönstret är hämtat från [pages/login.py](pages/login.py) som redan döljer sidebar via CSS.

**`landing_pages/__init__.py`** — tom, gör mappen till ett paket.

### `streamlit_app.py` — exakta ändringar

**1. Nya `st.Page()`-definitioner** efter nuvarande [rad 354](streamlit_app.py#L354):

```python
landing_home = st.Page("landing_pages/home.py", title="Home", icon="🏠", default=True)
landing_user_manual = st.Page("landing_pages/user_manual.py", title="User Manual", icon="📖")
landing_team = st.Page("landing_pages/team.py", title="Meet the Team", icon="👥")
landing_contact = st.Page("landing_pages/contact.py", title="Contact", icon="✉️")
```

**2. Huvudgreningen** ([rad 360-391](streamlit_app.py#L360-L391)) skrivs om:

```python
try_restore_auth_from_cookie()

LANDING_PAGES = [landing_home, landing_user_manual, landing_team, landing_contact]
APP_PAGES = [case_manager, case_setup, specification, revenue_frame]

if check_auth():
    pending_token = st.session_state.pop("_pending_auth_cookie", None)
    if pending_token:
        set_auth_cookie(pending_token)
    try_restore_case_from_cookie()
    _sync_case_cookie()

    # Dynamisk "tool"-länk i top-nav: leder direkt till case_manager (ingen reauth)
    tool_link = st.Page(
        "pages/1_create_and_select_case.py",
        title="Open tool",
        icon="🚀",
        url_path="open_tool",  # undvik kollision med samma sidobjekt i APP_PAGES
    )

    pg = st.navigation(
        {
            "": LANDING_PAGES + [tool_link],
            "_app_": APP_PAGES,
        },
        position="top",
    )

    # Sidebar visas BARA i app-sidor, inte i landningssidor
    if pg in APP_PAGES or pg == tool_link:
        render_sidebar()

    pg.run()

else:
    # Publik: top-nav med landningssidor + "Sign in"
    public_pages = LANDING_PAGES + [login_page]
    pg = st.navigation(
        {
            "": public_pages,
            "_protected_": APP_PAGES,  # registrerade för att undvika "page not found"
        },
        position="top",
    )
    if pg in APP_PAGES:
        st.switch_page(login_page)  # bokmärkt skyddad URL → login
    else:
        pg.run()
```

**Anmärkning om `tool_link`:** Eftersom `st.Page` med samma sökväg två gånger kan ge bekymmer registrerar vi en separat `tool_link` med eget `url_path`. Den pekar mot samma fil som `case_manager` men visas som ett separat top-nav-objekt med titeln "Open tool".

**3. Logout-callback** ([rad 308-324](streamlit_app.py#L308-L324)) — `st.switch_page(landing_home)` läggs till efter `sign_out()`:

```python
if st.button("Yes, log out", type="primary", use_container_width=True):
    st.session_state["_logging_out"] = True
    auth_manager = initialize_firebase_auth()
    auth_manager.sign_out()
    st.session_state["user_reid"] = None
    st.switch_page("landing_pages/home.py")  # NYTT
```

**4. `login_page`-objektet** (rad 331-334) — login-sidans titel ändras från "Login" till "Sign in" för konsistens med top-nav-etiketten.

---

## Återanvändning av existerande utilities

| Vad | Var | Hur det används |
|---|---|---|
| `apply_styling()` | [frontend/common/styling.py](frontend/common/styling.py) | Körs en gång i `streamlit_app.py` — gäller redan alla sidor inkl. landningssidor (fonts, Nordic Blue-tema). |
| `is_authenticated()`, `get_auth_email()` | [frontend/utils/state_manager.py](frontend/utils/state_manager.py) | Inte nödvändigt på landningssidan eftersom vi inte visar CTA. Kan användas för subtil "Logged in as X"-text i toppen. |
| `st.switch_page(...)` | Inbyggd | Logout-callback och eventuella interna länkar. |
| Cookie-baserad återställning | [auth/cookie_session.py](auth/cookie_session.py) | Körs redan i `try_restore_auth_from_cookie()` — återvändande inloggade användare får `check_auth() == True` automatiskt. |
| Color tokens | [config/colors.py](config/colors.py) | Använd `COLORS["primary"]` osv. i landningssidans CSS. |
| Streamlit static serving | `.streamlit/config.toml` rad 32 | `enableStaticServing = true` finns redan — PDF i `static/` blir åtkomlig via `/app/static/regumetrica_user_manual.pdf`. |

---

## PDF-hantering för User Manual

LaTeX-källan ([user_manual_latex/Regumetrica user manual.tex](user_manual_latex/Regumetrica%20user%20manual.tex)) bygger till `user_manual_latex/build/Regumetrica user manual.pdf`, som är gitignored. Tre alternativ för att exponera PDF:n via landningssidan:

1. **Committa en byggd PDF** till `static/regumetrica_user_manual.pdf` — enklast, men du måste komma ihåg att uppdatera när manualen ändras. Rekommenderas för start.
2. **Bygg-steg vid deploy** — Render kör `latexmk` som del av build. Mer infra-tungt, MiKTeX är inte trivialt i en Docker-image.
3. **Extern länk** — host PDF:n hos t.ex. Google Drive med publik länk. Pragmatiskt men splittrar var saker bor.

**Rekommendation:** Alternativ 1 i denna iteration. Byt till alternativ 2 om PDF uppdateras ofta.

---

## Verification (slutmanuell test)

1. `./venv/Scripts/python.exe -m streamlit run streamlit_app.py`
2. **Publik bruk (utloggad)**:
   - Öppna `http://localhost:8501/` → landningssidan (home) visas, ingen sidebar, top-nav med Home / User Manual / Meet the Team / Contact / Sign in.
   - Klicka mellan landningssidorna → varje sida renderar utan att kicka till login.
   - Klicka "Sign in" → login-sidan visas.
   - Försök öppna `http://localhost:8501/case_manager` direkt → ska redirecta till login.
3. **Logga in**:
   - Efter lyckad login → top-nav byter "Sign in" mot "Open tool", landar i `case_manager` (befintligt beteende).
   - Klicka "Open tool" i top-nav → går direkt till `case_manager` med sidebar synlig.
4. **Inloggad besöker landningssidan**:
   - Klicka "Home" i top-nav → landningssidan visas, **ingen reauth**, ingen aggressiv CTA, top-nav visar "Open tool".
5. **Logga ut**:
   - I sidebar i `case_manager`: klicka Log out → bekräfta → hamnar på landningssidans Home.
6. **Återvändande användare (giltig cookie, ny tab)**:
   - Öppna `http://localhost:8501/` → cookie restaurerar auth → landningssidans Home visas, top-nav visar "Open tool".
7. **User Manual PDF**:
   - Öppna User Manual → klicka nedladdningslänk → PDF laddas ned från `/app/static/regumetrica_user_manual.pdf`.
8. **Tester**:
   - `./venv/Scripts/python.exe -m pytest tests/ -v` — ska fortfarande vara grön (inga calculations/pipeline/data_loaders berörda).

---

## Sammanfattning av filändringar

| Fil | Operation | Storlek på ändring |
|---|---|---|
| [streamlit_app.py](streamlit_app.py) | Modifiera | ~40 rader (utökade Page-defs, omskriven huvudgrening, justerad logout) |
| `landing_pages/__init__.py` | Skapa | tom |
| `landing_pages/home.py` | Skapa | ~30-50 rader |
| `landing_pages/user_manual.py` | Skapa | ~20-30 rader |
| `landing_pages/team.py` | Skapa | ~20-40 rader |
| `landing_pages/contact.py` | Skapa | ~20-30 rader |
| `frontend/common/landing_styling.py` | Skapa | ~15 rader |
| `static/regumetrica_user_manual.pdf` | Lägg till (binär) | Bygg från LaTeX-källa |

Inga ändringar i: `pages/`, `config/`, `calculations/`, `pipeline/`, `data_loaders/`, `tests/`, `auth/` (utöver titelsträng), `frontend/utils/`, `frontend/modules/`, `frontend/results/`, `visualization/`.

Inga regressionsrisker i beräkningar eller datalager. Den största risken är navigationslogiken i `streamlit_app.py` — verifieras med scenariolistan ovan.
