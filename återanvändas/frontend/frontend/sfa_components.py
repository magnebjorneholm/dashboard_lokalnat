"""
effektivitet/frontend/sfa_components.py
Frontend Streamlit-komponenter för SFA-analys.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Optional


# ============================================================================
# PARAMETER-KOMPONENTER
# ============================================================================

def display_sfa_parameters(df: pd.DataFrame, scenario_info: dict) -> Optional[Dict]:
    """
    Visar SFA-parametrar och returnerar användarens val.
    
    Args:
        df: DataFrame med data
        scenario_info: Info om CAPEX-scenarier från Kapitalbas
        
    Returns:
        Dict med parametrar eller None om ogiltigt val
    """
    st.subheader("SFA-parametrar")
    
    # Input-variabler
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    
    # Lägg till scenario-kolumner om de finns
    if scenario_info.get("found"):
        capex_wacc_col = scenario_info.get("capex_col")
        totex_wacc_col = scenario_info.get("totex_col")
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]
        st.success(
            f"WACC-scenario aktivt: {scenario_info['tag'].replace('p','.')} • "
            f"täckning {scenario_info['coverage']:.0%}"
        )
    else:
        st.info("Inget CAPEX-scenario från Kapitalbas")
    
    # Output-variabel (endast en!)
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variabler**")
        input_cols = st.multiselect(
            "Inputvariabler", 
            all_inputs, 
            default=[c for c in ["CAPEX", "OPEXp"] if c in all_inputs],
            help="Välj kostnadsvariabler"
        )
        
        output_col = st.selectbox(
            "Outputvariabel (endast en!)", 
            all_outputs,
            index=0,
            help="SFA stödjer endast en output-variabel"
        )
    
    with col2:
        st.markdown("**Modellinställningar**")
        
        fun_type = st.selectbox(
            "Funktionstyp",
            ["prod", "cost"],
            index=0,
            format_func=lambda x: "Produktionsfunktion" if x == "prod" else "Kostnadsfunktion",
            help="Produktionsfunktion: maximera output | Kostnadsfunktion: minimera input"
        )
        
        intercept = st.checkbox(
            "Inkludera intercept",
            value=True,
            help="Om intercept ska inkluderas i regressionen"
        )
        
        lambda0 = st.number_input(
            "Initial lambda (λ₀)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help="Initialt värde för lambda-parametern i optimeringen"
        )
        
        method = st.selectbox(
            "TE-beräkningsmetod",
            ["teJ", "te", "teMod"],
            index=0,
            format_func=lambda x: {
                "teJ": "Jondrow et al. (1982) - Conditional mean",
                "te": "Battese & Coelli (1988) - MSE-minimering",
                "teMod": "Conditional mode"
            }[x],
            help="Metod för att beräkna teknisk effektivitet"
        )
    
    if not input_cols:
        st.warning("Välj minst en input-variabel")
        return None
    
    # Outlier-definition
    st.markdown("---")
    st.markdown("**Outlier-definition**")
    st.caption("Outliers identifieras baserat på extremt låg teknisk effektivitet")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        use_outlier_filter = st.checkbox(
            "Filtrera outliers",
            value=True,
            help="Identifiera företag med extremt låg effektivitet"
        )
    
    with col4:
        q_lower = st.slider(
            "Nedre kvartil",
            0, 50, 25,
            step=5,
            disabled=not use_outlier_filter,
            help="Nedre kvartil för outlier-tröskel"
        )
    
    with col5:
        multiplier = st.slider(
            "IQR-multiplikator",
            1.0, 3.0, 2.0,
            step=0.1,
            disabled=not use_outlier_filter,
            help="Multiplikator för interkvartilavstånd"
        )
    
    if use_outlier_filter:
        st.caption(f"Threshold: Q{q_lower} - {multiplier} × IQR (låg TE = outlier)")
    
    # Körknapp
    st.markdown("")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        run_model = st.button("Kör SFA-analys", type="primary", use_container_width=True)
    
    if not run_model:
        return None
    
    return {
        'fun': fun_type,
        'input_cols': input_cols,
        'output_col': output_col,
        'intercept': intercept,
        'lambda0': lambda0,
        'method': method,
        'outlier_filter': use_outlier_filter,
        'q_lower': q_lower,
        'q_upper': 75.0,  # Fast övre kvartil
        'multiplier': multiplier
    }


# ============================================================================
# RESULTAT-KOMPONENTER
# ============================================================================

def display_sfa_results_summary(result: pd.DataFrame, stats: Dict):
    """Visar sammanfattande metrics för SFA-resultat."""
    st.subheader("SFA-resultat")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Totalt antal DMU", stats['n_total'])
    
    with col2:
        st.metric("Outliers", stats['n_outliers'])
    
    with col3:
        st.metric("Medeleffektivitet", f"{stats['te_mean']:.3f}")
    
    with col4:
        avg_pot = 1 - stats['te_mean']
        st.metric("Medelpotential", f"{avg_pot:.3f}")
    
    if stats['n_outliers'] > 0:
        st.warning(f"{stats['n_outliers']} företag klassificerade som outliers")
        _display_sfa_outliers_table(result)


def _display_sfa_outliers_table(result: pd.DataFrame):
    """Visar expanderbar tabell med SFA outliers."""
    df_outliers = result[result["is_outlier"] == True][
        ["Företag", "TE_SFA", "potential"]
    ].copy()
    df_outliers["potential"] = df_outliers["potential"].round(4)
    
    with st.expander("Visa outliers"):
        st.dataframe(df_outliers, width='stretch')


def display_sfa_parameters_table(stats: Dict, beta_df: pd.DataFrame):
    """Visar parameterskattningar från SFA."""
    st.subheader("Parameterskattningar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Koefficienter**")
        if not beta_df.empty:
            for _, row in beta_df.iterrows():
                st.metric(row['Variable'], f"{row['Coefficient']:.4f}")
    
    with col2:
        st.markdown("**Varianskomponenter**")
        st.metric("λ (lambda)", f"{stats['lambda']:.4f}")
        st.metric("σ² (total varians)", f"{stats['sigma2']:.6f}")
        
        col2a, col2b = st.columns(2)
        with col2a:
            st.metric("σᵤ² (ineffektivitet)", f"{stats['sigmau2']:.6f}")
        with col2b:
            sigma_u_share = stats['sigmau2'] / stats['sigma2'] * 100 if stats['sigma2'] > 0 else 0
            st.caption(f"({sigma_u_share:.1f}% av total)")
        
        col2c, col2d = st.columns(2)
        with col2c:
            st.metric("σᵥ² (random noise)", f"{stats['sigmav2']:.6f}")
        with col2d:
            sigma_v_share = stats['sigmav2'] / stats['sigma2'] * 100 if stats['sigma2'] > 0 else 0
            st.caption(f"({sigma_v_share:.1f}% av total)")


def display_sfa_results_table(result: pd.DataFrame):
    """Visar huvudresultat-tabell för SFA."""
    display_result = result[
        ["DMU", "Företag", "TE_SFA", "potential", "is_outlier"]
    ].copy()
    
    display_result["potential"] = (display_result["potential"] * 100).round(2)
    display_result = display_result.rename(columns={
        "TE_SFA": "Effektivitet",
        "potential": "Potential (%)",
        "is_outlier": "Outlier"
    })
    
    st.dataframe(display_result, width='stretch')


def display_sfa_efficiency_histogram(data: pd.Series, title: str = "Teknisk effektivitet (SFA)"):
    """Visar histogram för SFA-effektivitet."""
    data_clean = pd.to_numeric(data, errors="coerce").dropna()
    
    if data_clean.empty:
        st.warning("Ingen data att visa")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=data_clean,
        nbinsx=15,
        marker=dict(
            color='#1976D2',
            line=dict(color='#0D3B66', width=1)
        ),
        hovertemplate='TE: %{x:.3f}<br>Antal: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14, color='#1E3A5F')
        ),
        xaxis=dict(
            title="Teknisk effektivitet",
            gridcolor='#E5E5E5'
        ),
        yaxis=dict(
            title="Antal företag",
            gridcolor='#E5E5E5'
        ),
        plot_bgcolor='#F5F7FA',
        paper_bgcolor='#F5F7FA',
        height=400,
        font=dict(family="sans-serif", size=12, color='#2C3E50')
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_sfa_efficiency_distributions(result: pd.DataFrame):
    """Visar två histogram: effektivitet och potential."""
    st.subheader("Fördelningar")
    
    col1, col2 = st.columns(2)
    
    df_plot = result[result["is_outlier"] == False]
    
    with col1:
        display_sfa_efficiency_histogram(
            df_plot["TE_SFA"], 
            title="Effektivitet (exkl. outliers)"
        )
    
    with col2:
        display_sfa_efficiency_histogram(
            df_plot["potential"] * 100, 
            title="Potential (%) (exkl. outliers)"
        )