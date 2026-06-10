"""Isolerat test: st.rerun()-beteende inuti st.dialog (Streamlit 1.55).

Kör:  ./venv/Scripts/python.exe -m streamlit run dialog_rerun_test.py

Syftet är att verifiera tre saker som vårt auth-dialog-förslag vilar på:

  1. Widget-interaktion inuti dialogen (form-submit, knapp) => FRAGMENT-rerun.
     Dialogen STÄNGS INTE; bara dialog-kroppen körs om. Hela appen körs INTE om.

  2. st.rerun(scope="fragment") inuti dialogen => byter vy INOM dialogen,
     dialogen FÖRBLIR ÖPPEN. (Detta är mekanismen för intern vy-växling, t.ex.
     login -> "väntar på verifiering".)

  3. st.rerun()  (default scope="app") inuti dialogen => HELA appen körs om,
     top-level anropar inte dialog-funktionen igen => dialogen STÄNGS.
     (Detta är exakt vad vi vill vid lyckad inloggning: stäng + bygg om nav.)

Observera räknarna:
  - "App-körningar" ökar bara vid full-app-rerun (öppna dialog, scope='app').
  - "Fragment-körningar" ökar vid varje interaktion inuti dialogen.
Om App-räknaren står still medan du klickar inuti dialogen => fragment-isolering
bekräftad.
"""

import streamlit as st

# --- Räknare för att se vilken sorts rerun som skett ---
st.session_state.setdefault("app_runs", 0)
st.session_state["app_runs"] += 1   # ökar vid varje FULL-app-körning

st.title("Dialog rerun-test (Streamlit %s)" % st.__version__)
st.metric("App-körningar (full script)", st.session_state["app_runs"])
st.caption(
    "Denna siffra ska INTE öka när du klickar inuti dialogen — bara när "
    "dialogen öppnas eller stängs via scope='app'."
)

if st.session_state.get("login_done"):
    st.success(f"Inloggad som: {st.session_state.get('who')}  ← satt inifrån dialogen, "
               "syns efter att dialogen stängdes via st.rerun() (scope='app').")
    if st.button("Återställ"):
        for k in ("login_done", "who", "step", "frag_runs"):
            st.session_state.pop(k, None)
        st.rerun()


@st.dialog("Auth-dialog (test)", width="large")
def auth_dialog():
    # Dialog-kroppen är en FRAGMENT. Allt här inne körs om vid interaktion,
    # utan att hela appen körs om.
    st.session_state["frag_runs"] = st.session_state.get("frag_runs", 0) + 1
    st.caption(f"Fragment-körningar: {st.session_state['frag_runs']} "
               "(ökar vid varje klick här inne; App-räknaren utanför står still)")

    step = st.session_state.get("step", "login")

    # ---- Vy 1: login ----
    if step == "login":
        st.subheader("Steg 1 — login")
        with st.form("login"):
            name = st.text_input("Namn", value="Erik")
            verified = st.checkbox("E-post verifierad?", value=False)
            submit = st.form_submit_button("Logga in", type="primary")
        if submit:
            st.session_state["who"] = name
            if not verified:
                # Byt vy INOM dialogen — dialogen ska förbli öppen.
                st.session_state["step"] = "verify"
                st.rerun(scope="fragment")          # <-- TEST 2
            else:
                # Lyckad inloggning — stäng dialogen + bygg om appen.
                st.session_state["login_done"] = True
                st.session_state["step"] = "login"
                st.rerun()                           # <-- TEST 3 (scope='app')

    # ---- Vy 2: väntar på verifiering ----
    elif step == "verify":
        st.subheader("Steg 2 — väntar på verifiering")
        st.warning("Din e-post är inte verifierad. (Detta är en ny vy INOM "
                   "samma dialog — om du ser den utan att dialogen stängdes är "
                   "fragment-vy-växling bekräftad.)")
        if st.button("Skicka verifiering igen"):
            st.toast("Verifiering skickad (låtsas)")   # knapp inuti dialog = fragment-rerun
        if st.button("Tillbaka till login"):
            st.session_state["step"] = "login"
            st.rerun(scope="fragment")


with st.sidebar:
    st.header("Test-kontroll")
    if st.button("Öppna auth-dialog", type="primary"):
        st.session_state["step"] = "login"
        auth_dialog()
