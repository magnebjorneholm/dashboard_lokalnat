"""
Page 5 - New benchmarking model (isolated add-on).

Thin Streamlit shim: the page lives in pages/ for Streamlit's navigation, but all of
its logic lives in the feature module (new_benchmarking_model/ui/page.py).
"""

from new_benchmarking_model.ui.page import render_page

render_page()
