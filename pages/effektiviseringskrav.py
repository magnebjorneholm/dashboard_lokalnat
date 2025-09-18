import streamlit as st

from effektiviseringskrav.app.data_loader import load_data
from effektiviseringskrav.view.show_dea import show_dea_view
from effektiviseringskrav.view.show_pystoned import show_pystoned_view
from effektiviseringskrav.view.show_fardiga_korningar import show_fardiga_korningar_view
from effektiviseringskrav.view.show_jamfor_korning import show_jamfor_korningar_view
from effektiviseringskrav.view.show_foretagsanalys import show_foretagsanalys_view
from effektiviseringskrav.view.show_heatmap import show_heatmap


if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

st.set_page_config(page_title="Effektiviseringskrav", layout="wide")
st.title("Effektiviseringskrav")
st.markdown("Beräkna effektiviseringskrav och påverkbara kostnader och exportera till intäktsramen.")

# --- Ladda data ---
data_file = "effektiviseringskrav/data/Data_modeller.xlsx"
df = load_data(data_file)

# --- Modellval ---
modellval = st.sidebar.selectbox(
    "Välj modell",
    ["DEA", "SFA och Pystoned", "Jämför körningar", "Företagsanalys", "Geografisk karta"]
)

if modellval == "DEA":
    show_dea_view(df)


# elif modellval == "PyStoned":
   # st.header("PyStoned")
   # st.warning("Tekniska problem för externa användare pga solver funkar bara lokalt")
   # st.info("Se 'färdiga körningar'")
   # st.stop()


#elif modellval == "SFA":
#    st.header("SFA")
#    st.warning("Tekniska problem")
#    st.info("Se 'färdiga körningar'")
#    st.stop()


elif modellval == "SFA och Pystoned":
    show_fardiga_korningar_view()


elif modellval == "Jämför körningar":
    show_jamfor_korningar_view()


elif modellval == "Företagsanalys":
    show_foretagsanalys_view(df)

elif modellval == "Geografisk karta":
    show_heatmap()

st.sidebar.markdown("---")
if st.sidebar.button("Logga ut"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()