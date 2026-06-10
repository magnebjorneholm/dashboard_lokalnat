# Auth-dialog — detaljspec (appendix till FRONTEND_FILES.md)

> Detaljerad design av inloggnings-dialogen. Master-arkitekturen (två zoner,
> navbar, filstruktur) ligger i `FRONTEND_FILES.md`. Pseudokoden här är
> illustrativ — inte slutgiltig.

## Mål

Inloggning sker via en **Sign in-CTA i landningens topp-navbar** som öppnar en
`st.dialog` ovanpå landningssidan. Användaren stannar i kontext, kan logga in /
skapa konto / återställa lösenord, och vid lyckad inloggning byter appen från
zon 1 (landning) till zon 2 (verktyget).

`pages/login.py` retireras helt — dialogen sköter allt. Tidigare separata
login-sida med dolt sidofält finns inte längre.

---

## Var koden bor

| Fil | Roll |
|---|---|
| `frontend/common/auth_dialog.py` *(ny)* | `auth_dialog()` + formulär-renderarna (login/register/reset/verify). Importerar `auth.firebase_auth` (lägre lager — ok). |
| `frontend/common/landing_shell.py` *(ny)* | Topp-navbaren innehåller Sign in-knappen som anropar `auth_dialog()`. |
| `streamlit_app.py` | Logout bor i zon 2:s `render_sidebar` (som idag). Zon 1 har ingen logout — man är ju utloggad där. |

Formulärlogiken flyttas från (numera retirerade) `pages/login.py` —
`render_login_form`, `render_registration_form`, `render_password_reset`,
`render_verification_pending` är redan fristående och tar `auth_manager`, så de
anpassas, inte skrivs om från noll.

---

## Sign in-knappen (i navbaren)

Renderas av `apply_landing_shell()` på varje landningssida:

```python
# inuti landningens topp-navbar
if st.button("Sign in", type="primary"):
    auth_dialog()        # öppnar modalen ovanpå landningen
```

Inget togglande Sign in ↔ Log out behövs (till skillnad från den tidigare
sidofälts-idén): är man inloggad är man i zon 2, där sidofältet har logout.

---

## Dialogen — struktur

Designprincip: **ingen intern sid-navigering som kräver app-rerun**. Flikar och
expander är klient-sidiga; det enda `st.rerun()` med app-scope körs vid **lyckad
inloggning** (stänger dialogen + byter till zon 2).

```python
@st.dialog("Sign in to Regumetrica", width="large")
def auth_dialog():
    auth_manager = initialize_firebase_auth()

    # verifierings-vy som egen gren (se "E-postverifiering" nedan)
    if st.session_state.get("auth_step") == "verify":
        _render_verification(auth_manager)
        return

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])
    with tab_login:
        _render_login(auth_manager)        # + lösenordsåterställning som expander
    with tab_register:
        _render_register(auth_manager)
```

### Login-fliken

```python
def _render_login(auth_manager):
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submit:
        ok, err, user = auth_manager.sign_in(email, password)
        if not ok:
            st.error(err or "Login failed")
        elif not user.get("emailVerified"):
            _handle_unverified(user)        # se nedan
        else:
            st.session_state["_pending_auth_cookie"] = user.get("refreshToken", "")
            claims = auth_manager.get_user_claims(user["idToken"])
            _store_auth_session(user, email, claims)
            if claims and claims.get("role") == "company" and claims.get("reid"):
                set_user_reid(claims["reid"])
            st.rerun()                       # scope="app" → stäng dialog + byt till zon 2

    with st.expander("Forgot your password?"):
        with st.form("reset_form"):
            reset_email = st.text_input("Email", key="reset_email")
            send = st.form_submit_button("Send reset link", width="stretch")
        if send:
            if not reset_email:
                st.error("Please enter your email")
            else:
                ok, err = auth_manager.send_password_reset_email(reset_email)
                st.success("Reset link sent — check your inbox.") if ok \
                    else st.error(err or "Could not send email")
```

### Create account-fliken

Samma innehåll som tidigare `render_registration_form` — e-post, lösenord ×2,
roll-radio, företags-dropdown (för company), "Create account" → `sign_up()` →
meddelande "verifiera din e-post". Inget rerun.

> Sidofråga (utanför scope): registreringen läste rå `Företag` ur Excel via egen
> `load_company_list`, medan resten av appen använder kuraterade namn
> (`company_names.csv`). Kan enas vid implementering.

---

## E-postverifiering — VERIFIERAT: hålls helt i dialogen

> Källkodsgranskat mot **Streamlit 1.55** (faktisk version i venv; config.toml
> säger 1.52 men stämmer inte).

`st.dialog` lindar dialog-kroppen i en **`st.fragment`**
([dialog_decorator.py:99-104](../venv/Lib/site-packages/streamlit/elements/dialog_decorator.py#L99)).
Det ger tre beteenden som löser hela vy-växlingsfrågan:

| Händelse inuti dialogen | Effekt | Dialogen |
|---|---|---|
| Widget-interaktion (form-submit, knapp, flik) | **Fragment-rerun** — bara dialog-kroppen körs om, hela appen körs *inte* om | **Förblir öppen** |
| `st.rerun(scope="fragment")` | Kör om enbart dialog-fragmentet med nytt state | **Förblir öppen** |
| `st.rerun()` *(default `scope="app"`)* | Full-app-rerun; top-level anropar inte dialog-funktionen igen → | **Stängs** |

Vid ej-verifierad login sätter vi en flagga och kör `st.rerun(scope="fragment")`
— dialogen förblir öppen och renderar om med verifierings-vyn (med en fungerande,
beständig "Resend"-knapp). Enda app-scope-`st.rerun()` är vid **lyckad** login.

```python
def _handle_unverified(user):
    st.session_state["pending_verification_token"] = user.get("idToken")
    st.session_state["auth_step"] = "verify"
    st.rerun(scope="fragment")     # dialogen förblir öppen, byter vy
```

**Caveat:** `st.rerun(scope="fragment")` får bara anropas *under* en
fragment-rerun (alltså som svar på ett klick inuti dialogen), inte under den
första full-app-körningen då dialogen öppnas
([execution_control.py, rerun-docstring](../venv/Lib/site-packages/streamlit/commands/execution_control.py)).
Vårt mönster gör bara det → säkert. Att öppna dialogen från en knapp är explicit
stöttat — dekoratorn renderar på `event_dg` så den ärver inte omgivande tema
([dialog_decorator.py:80-89](../venv/Lib/site-packages/streamlit/elements/dialog_decorator.py#L80)).

### Körbart isolerat test

`dialog_rerun_test.py` (repo-roten) demonstrerar alla tre beteendena med synliga
räknare:

```
./venv/Scripts/python.exe -m streamlit run dialog_rerun_test.py
```

- **App-körningar**-räknaren står still när du klickar *inuti* dialogen →
  fragment-isolering bekräftad.
- Login med "verifierad" avbockad → byter till verifierings-vy **utan** att
  dialogen stängs (scope="fragment").
- Login med "verifierad" ibockad → dialogen **stängs** och huvudsidan visar
  inloggat läge (scope="app").

---

## Cookie / rerun-flödet steg för steg (lyckad inloggning)

1. Användaren submittar login i dialogen → `sign_in()` ok + verifierad.
2. Vi sätter `_pending_auth_cookie` + `auth_*` i session_state, `set_user_reid`.
3. `st.rerun()` (scope="app") → dialogen stängs.
4. `streamlit_app.py` körs om från toppen → `check_auth()` = True → **zon 2**.
5. `_pending_auth_cookie` plockas och `set_auth_cookie()` körs
   ([streamlit_app.py:371-373](../streamlit_app.py#L371)) — JS-komponenten hinner rendera.
6. `st.navigation` byggs för verktyget → sidofält + tools.

Identiskt deferral-mönster som idag; bara triggern flyttar från login-sidan till
dialogen.

---

## Deep-link-redirect

Skyddade tool-sidor registreras dolt i zon 1:s navigation så att bokmärkta
URL:er inte 404:ar ([streamlit_app.py:402-403](../streamlit_app.py#L402)).
Eftersom `pages/login.py` är borta blir redirect-målet **`landing_home`**:

```python
if pg in APP_PAGES_HIDDEN:
    st.switch_page(landing_home)     # tidigare: login_page
```

`landing_home` har Sign in-CTA i navbaren, så användaren kan logga in därifrån.

---

## Vad som INTE ändras
- **Navigationens auto-ombyggnad** vid auth-skifte (zon 1 ↔ zon 2).
- **Domänlagren** (`calculations/`, `pipeline/`, `config/`, `data_loaders/`).
- **Auth-managern** (`firebase_auth.py`) — samma metoder anropas.
- **Verktygets sidofält** (företagsväljare + logout) i zon 2.

## Beslut (låsta)
1. Sign in via dialog från landningens navbar — ✔
2. `pages/login.py` retireras helt — ✔
3. E-postverifiering hålls i dialogen via `st.rerun(scope="fragment")` — ✔ (verifierat)
4. Deep-link-redirect → `landing_home` — ✔
