"""
frontend/common/formulas.py

LaTeX-formler fÃ¶r Regumetrica UI.
Organiserade efter modul och berÃ¤kningskedja.

AnvÃ¤ndning:
    from frontend.common.formulas import FORMULA_WACC_REAL
    st.latex(FORMULA_WACC_REAL)

Verifierad mot:
- wacc_calculations.py
- dea_calculations.py
- effektiviseringskrav.py
- kent_calculations.py
- incentive_calculations.py
- Bilaga 4 (Ei)
- Regumetrica UM 2.pdf
"""

# =============================================================================
# M3: WACC - Cost of Capital (wacc_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: Hamada â†’ CAPM â†’ Kostnad skuld â†’ WACC nom â†’ Fisher â†’ WACC real
# AnvÃ¤nds i: m3_cost_of_capital.py, pre_dea.py (WACC-skalning)

# 3.2.1 Hamada-formeln: Konverterar tillgÃ¥ngsbeta till aktiebeta
# Tar hÃ¤nsyn till skuldsÃ¤ttning och skatteskÃ¶ld
FORMULA_HAMADA = r"\beta_E = \beta_A \times \left(1 + (1 - \tau) \times \frac{S}{1-S}\right)"

# Hamada med variabelfÃ¶rklaring
FORMULA_HAMADA_EXPLAINED = r"""
\beta_E = \beta_A \times \left(1 + (1 - \tau) \times \frac{S}{1-S}\right)
"""

# 3.2.2 CAPM: Kostnad fÃ¶r eget kapital (nominell, efter skatt)
# Klassisk Capital Asset Pricing Model
FORMULA_CAPM = r"R_e = R_f + \beta_E \times MRP"

# CAPM med fullstÃ¤ndiga variabelnamn
# KORRIGERAD: AnvÃ¤nder MRP (marknadsriskpremie), inte R_m
FORMULA_CAPM_FULL = r"R_e^{nom} = R_f + \beta_E \times MRP"

# 3.2.3 Kostnad fÃ¶r skuld (nominell, fÃ¶re skatt)
FORMULA_COST_OF_DEBT = r"R_d = R_f + \text{kreditriskpremie}"

# 3.2.4 WACC nominell efter skatt
# Viktat genomsnitt av kostnad fÃ¶r eget kapital och skuld
FORMULA_WACC_NOMINAL_AFTER_TAX = r"WACC_{nom}^{efter} = (1-S) \times R_e + S \times R_d \times (1-\tau)"

# 3.2.4 WACC nominell fÃ¶re skatt
# Grossas upp fÃ¶r att kompensera fÃ¶r skatteavdrag
FORMULA_WACC_NOMINAL_BEFORE_TAX = r"WACC_{nom}^{fÃ¶re} = \frac{WACC_{nom}^{efter}}{1 - \tau}"

# Komplett WACC-formel (kombinerar ovanstÃ¥ende)
FORMULA_WACC_NOMINAL_COMPLETE = r"WACC_{nom} = \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1 - \tau}"

# 3.2.5 Fisher-ekvationen: Nominell â†’ Real
# OmrÃ¤kning frÃ¥n nominell till real rÃ¤nta
FORMULA_FISHER = r"WACC_{real} = \frac{1 + WACC_{nom}}{1 + \pi} - 1"

# Alternativ notation fÃ¶r Fisher
FORMULA_FISHER_ALT = r"r_{real} = \frac{1 + r_{nom}}{1 + \pi} - 1"

# Komplett WACC-berÃ¤kning i ett steg (fÃ¶r sammanfattning)
FORMULA_WACC_COMPLETE = r"""
WACC_{real} = \frac{1 + \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1-\tau}}{1 + \pi} - 1
"""

# VariabelfÃ¶rklaringar fÃ¶r WACC
WACC_VARIABLE_DESCRIPTIONS = {
    "beta_A": "TillgÃ¥ngsbeta (obelanad)",
    "beta_E": "Aktiebeta (belanad)",
    "S": "SkuldsÃ¤ttningsgrad D/(D+E)",
    "tau": "Bolagsskattesats",
    "R_f": "Riskfri rÃ¤nta",
    "R_e": "Kostnad eget kapital",
    "R_d": "Kostnad skuld",
    "MRP": "Marknadsriskpremie",
    "pi": "Inflation (CPIF)",
}


# =============================================================================
# M3: HÃ¤rledda parametrar - Alternativ WACC-inmatning
# =============================================================================
# FÃ¶r anvÃ¤ndare som vill ange Re, Rd, S, Ï„, Ï€ direkt

FORMULA_WACC_FROM_DERIVED = r"WACC_{real} = \frac{1 + \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1-\tau}}{1 + \pi} - 1"


# =============================================================================
# M5: Effektiviseringskrav (effektiviseringskrav.py)
# =============================================================================
# BerÃ¤kningskedja: DEA-potential â†’ Trunkering â†’ Total eff â†’ Ã…rligt krav
# AnvÃ¤nds i: m5_efficiency.py, post_dea.py

# Total effektivisering under tillsynsperioden
# Kombinerar trunkerad potential med kunddelning och realiseringstid
FORMULA_TOTAL_EFFICIENCY = r"\text{Total eff.} = \text{potential}_{trunk} \times \text{kunddelning} \times \frac{\text{tillsynsperiod}}{\text{realiseringstid}}"

# Årligt effektiviseringskrav (ränta-på-ränta)
# Fördelar total effektivisering jämnt över tillsynsperioden
FORMULA_ANNUAL_EFFICIENCY_REQ = r"\text{Effkrav}_{Årligt} = \left(1 + \text{Total eff.}\right)^{\frac{1}{\text{tillsynsperiod}}} - 1"

# Kombinerad formel för årligt krav (med fullständiga svenska termer)
FORMULA_EFFICIENCY_COMPLETE = r"""
\text{Effkrav} = \left(1 + \text{potential}_{trunk} \times \text{kunddelning} \times \frac{\text{tillsynsperiod}}{\text{realiseringstid}}\right)^{\frac{1}{\text{tillsynsperiod}}} - 1
"""

# Med baseline-vÃ¤rden (fÃ¶r illustration)
FORMULA_EFFICIENCY_WITH_BASELINE = r"""
\text{Effkrav} = \left(1 + \min(\max(\text{pot}, 0.162), 0.30) \times 0.5 \times \frac{4}{8}\right)^{\frac{1}{4}} - 1
"""

# Max Ã¥rligt krav (vid 30% potential)
# Notering: Ei anvÃ¤nder 1.82% i dokumentation (avrundning nedÃ¥t frÃ¥n 1.827%)
FORMULA_MAX_EFFICIENCY_REQ = r"\text{Max effkrav} = \left(1 + 0.30 \times 0.50 \times \frac{4}{8}\right)^{0.25} - 1 \approx 1.83\%"


# =============================================================================
# Benchmarking: DEA (dea_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: LP-optimering â†’ Supereffektivitet â†’ Outlier-identifiering
# AnvÃ¤nds i: benchmarking.py, dea.py

# DEA input-oriented LP-formulering (CRS, Super-efficiency)
# Minimerar input-skalning Î¸ fÃ¶r att nÃ¥ fronten
# OBS: j â‰  i innebÃ¤r att DMU i exkluderas frÃ¥n referensmÃ¤ngden (super-efficiency)
FORMULA_DEA_LP = r"""
\begin{aligned}
\min_{\theta, \lambda} \quad & \theta \\
\text{s.t.} \quad & \sum_{j \neq i} \lambda_j x_j \leq \theta x_i \\
& \sum_{j \neq i} \lambda_j y_j \geq y_i \\
& \lambda_j \geq 0
\end{aligned}
"""

# Standard DEA (inkluderar alla DMU:er i referensmÃ¤ngden)
FORMULA_DEA_LP_STANDARD = r"""
\begin{aligned}
\min_{\theta, \lambda} \quad & \theta \\
\text{s.t.} \quad & \sum_{j} \lambda_j x_j \leq \theta x_i \\
& \sum_{j} \lambda_j y_j \geq y_i \\
& \lambda_j \geq 0
\end{aligned}
"""

# Kompakt DEA-formulering (fÃ¶r inline-visning)
FORMULA_DEA_COMPACT = r"\theta^* = \min\{\theta : \sum_j \lambda_j x_j \leq \theta x_0, \sum_j \lambda_j y_j \geq y_0, \lambda \geq 0\}"

# VRS-constraint (om variabel skalavkastning)
FORMULA_DEA_VRS_CONSTRAINT = r"\sum_{j} \lambda_j = 1"

# Effektivitetspotential
FORMULA_EFFICIENCY_POTENTIAL = r"\text{potential} = 1 - \theta"

# Outlier-threshold (IQR-metod)
FORMULA_OUTLIER_THRESHOLD = r"\text{threshold} = Q_{75} + k \times (Q_{75} - Q_{25})"

# Outlier-threshold med default k=2
FORMULA_OUTLIER_THRESHOLD_DEFAULT = r"\text{threshold} = Q_3 + 2 \times IQR"

# =============================================================================
# Incitament: Kvalitet (incentive_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: AIT/AIF-norm â†’ Utfall â†’ Differens â†’ Kostnad â†’ Justering
# AnvÃ¤nds i: m3_cost_of_capital.py (kvalitetssektion), post_dea.py
# KÃ¤lla: Bilaga 4 (Ei)

# AIT-definition (Average Interruption Time)
# Effektviktad medelavbrottstid
# KORRIGERAD enligt Bilaga 4, sida 6
FORMULA_AIT_DEFINITION = r"AIT_j^k = \frac{ILE_j^k}{\sum_i P_i} = \frac{\sum_i (P_i \times d_{i,j})}{\sum_i P_i}"

# AIF-definition (Average Interruption Frequency)
# Effektviktad medelavbrottsfrekvens
# KORRIGERAD enligt Bilaga 4, sida 6
FORMULA_AIF_DEFINITION = r"AIF_j^k = \frac{ILEffekt_j^k}{\sum_i P_i} = \frac{\sum_i P_i \times n_{i,j}}{\sum_i P_i}"

# ILE (Icke-Levererad Energi) per avbrott
# d = avbrottstid i timmar, P = Ã¥rsmedeleffekt i kW
FORMULA_ILE = r"ILE = d \times P"

# ILEffekt (Icke-Levererad Effekt)
# Summering av bortkopplad effekt vid avbrott
# Notering: Per avbrott Ã¤r ILEffekt = P, men totalt summeras Ã¶ver alla avbrott
FORMULA_ILEFFEKT = r"ILEffekt = \sum_{\text{avbrott}} P"

# Ã…rsmedeleffekt
FORMULA_ANNUAL_AVERAGE_POWER = r"P = \frac{E}{t_y}"

# Kvalitetskostnad fÃ¶r AIT (per kundtyp och avbrottstyp)
# KORRIGERAD: AnvÃ¤nder Ã…ME (Ã¥rsmedeleffekt) fÃ¶r kundtypen
FORMULA_QUALITY_COST_AIT = r"K_{AIT,j}^k = (AIT_{norm,j}^k - AIT_{utfall,j}^k) \times \text{Ã…ME}^k \times v_{ILE,j}^k"

# Kvalitetskostnad fÃ¶r AIF (per kundtyp och avbrottstyp)
FORMULA_QUALITY_COST_AIF = r"K_{AIF,j}^k = (AIF_{norm,j}^k - AIF_{utfall,j}^k) \times \text{Ã…ME}^k \times v_{ILEffekt,j}^k"

# Total kvalitetsjustering per Ã¥r
FORMULA_QUALITY_TOTAL = r"\text{Kvalitet}_{Ã¥r} = \sum_j \sum_k (K_{AIT,j}^k + K_{AIF,j}^k) \times KPI"

# Kvalitetsjustering med CEMI4-korrigering
FORMULA_QUALITY_WITH_CEMI = r"\text{Kvalitet}_{just} = \text{Kvalitet} \times (1 - \min(adj_{CEMI4}, \Delta CEMI4))"


# =============================================================================
# Incitament: NÃ¤tfÃ¶rlust (incentive_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: FÃ¶rlust-norm â†’ Observerad â†’ Differens â†’ Kostnad
# AnvÃ¤nds i: m3_cost_of_capital.py (nÃ¤tfÃ¶rlustsektion), post_dea.py

# NÃ¤tfÃ¶rlustincitament per Ã¥r
FORMULA_NETLOSS_INCENTIVE = r"\text{NÃ¤tfÃ¶rlust}_{Ã¥r} = (\text{fÃ¶rlust}_{norm} - \text{fÃ¶rlust}_{obs}) \times k_{NF} \times s_{NF}"

# Med variabelfÃ¶rklaring
FORMULA_NETLOSS_INCENTIVE_EXPLAINED = r"""
\text{Inc}_{NF} = (\text{FÃ¶rlust}_{norm} - \text{FÃ¶rlust}_{obs}) \times k_{NF} \times s
"""

# Andel nÃ¤tfÃ¶rluster (definition)
# KORRIGERAD: Relation till total tillfÃ¶rd energi enligt Ei's nya definition
FORMULA_NETLOSS_SHARE = r"\text{FÃ¶rlustprocent} = \frac{E_{in} - E_{ut}}{E_{in}}"


# =============================================================================
# Incitament: Belastning (incentive_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: Utnyttjandegrad-norm â†’ Observerad â†’ Differens â†’ Kostnad
# AnvÃ¤nds i: m3_cost_of_capital.py (belastningssektion), post_dea.py

# Belastningsincitament per Ã¥r
FORMULA_LOAD_INCENTIVE = r"\text{Belastning}_{Ã¥r} = (UG_{obs} - UG_{norm}) \times k_{upstream}"

# Utnyttjandegrad (definition)
FORMULA_UTILIZATION_RATE = r"UG = \frac{\bar{P}_{dygn}}{P_{max,4}}"


# =============================================================================
# Incitament: BegrÃ¤nsningar/Cap (incentive_calculations.py)
# =============================================================================
# BerÃ¤kningskedja: BerÃ¤kna delincitament â†’ Applicera individuell cap â†’ Summera â†’ Total cap
# AnvÃ¤nds i: post_dea.py

# Cap pÃ¥ individuellt incitament
FORMULA_INCENTIVE_CAP_INDIVIDUAL = r"|Inc_i| \leq \frac{1}{3} \times R_{Ã¥r}"

# Cap pÃ¥ totalt incitament per Ã¥r
FORMULA_INCENTIVE_CAP_TOTAL = r"\left|\sum_i Inc_i\right| \leq \frac{1}{3} \times R_{Ã¥r}"

# Total incitamentjustering med cap
FORMULA_INCENTIVE_TOTAL_WITH_CAP = r"""
\text{Inc}_{total} = \text{clip}\left(\sum_i Inc_i, -\frac{R}{3}, \frac{R}{3}\right)
"""


# =============================================================================
# IntÃ¤ktsram: Assemblering (intaktsram_assembly.py)
# =============================================================================
# BerÃ¤kningskedja: Komponenter â†’ Summering â†’ Total intÃ¤ktsram
# AnvÃ¤nds i: post_dea.py, 2_results.py

# Total intÃ¤ktsram (huvudformel)
FORMULA_INTAKTSRAM_TOTAL = r"""
IR = \text{PÃ¥verkbara} + \text{OpÃ¥verkbara} + \text{Kapitalkostnad} + \text{Incitament}
"""

# IntÃ¤ktsram med alla komponenter
FORMULA_INTAKTSRAM_COMPLETE = r"""
IR = P_{pÃ¥v} + P_{opÃ¥v} + (D + R) + (Inc_{kval} + Inc_{NF} + Inc_{bel})
"""

# PÃ¥verkbara kostnader efter effektiviseringskrav
FORMULA_PAVERKBARA_AFTER_EFFKRAV = r"""
P_{pÃ¥v,ny} = P_{pÃ¥v,baseline} \times \prod_{t=1}^{4} (1 - \text{effkrav}_t)
"""


# =============================================================================
# NormnivÃ¥er: Kvalitetsindikatorer (incentive_parameters.py)
# =============================================================================
# FrÃ¥n Bilaga 4 - kurvanpassning fÃ¶r normnivÃ¥er
# KORRIGERAD enligt Bilaga 4, sida 9

# NormnivÃ¥ som funktion av kundtÃ¤thet (T)
# T = antal kunder per km ledning
FORMULA_NORM_AIT = r"AIT_j^k(T) = \alpha_{j,AIT}^k + \frac{\beta_{j,AIT}^k}{\gamma_{j,AIT}^k + T}"

FORMULA_NORM_AIF = r"AIF_j^k(T) = \alpha_{j,AIF}^k + \frac{\beta_{j,AIF}^k}{\gamma_{j,AIF}^k + T}"

# Generell form (fÃ¶r dokumentation)
FORMULA_NORM_GENERAL = r"Y(T) = \alpha + \frac{\beta}{\gamma + T}"

# Parametrar varierar per kundtyp (k) och avbrottstyp (j), se Bilaga 4, Tabell 2
# k âˆˆ {HushÃ¥ll, Industri, Jordbruk, Handel/tjÃ¤nster, Offentlig v., GrÃ¤nspunkt}
# j âˆˆ {oaviserade, aviserade}


# =============================================================================
# VariabelfÃ¶rklaringar (fÃ¶r dokumentation)
# =============================================================================

VARIABLE_GLOSSARY = {
    # WACC
    "beta_A": ("Î²_A", "TillgÃ¥ngsbeta (obelanad/unlevered)"),
    "beta_E": ("Î²_E", "Aktiebeta (belanad/levered)"),
    "S": ("S", "SkuldsÃ¤ttningsgrad D/(D+E)"),
    "tau": ("Ï„", "Bolagsskattesats"),
    "R_f": ("R_f", "Riskfri rÃ¤nta (10-Ã¥rig statsobligation)"),
    "R_e": ("R_e", "Kostnad fÃ¶r eget kapital"),
    "R_d": ("R_d", "Kostnad fÃ¶r skuld"),
    "MRP": ("MRP", "Marknadsriskpremie"),
    "pi": ("Ï€", "Inflation (CPIF-prognos)"),
    
    # DEA
    "theta": ("Î¸", "Effektivitetsscore (1 = effektiv)"),
    "lambda": ("Î»", "Vikter fÃ¶r referensfÃ¶retag"),
    "x": ("x", "Input-vektor (kostnader)"),
    "y": ("y", "Output-vektor (volymer)"),
    
    # Effektiviseringskrav
    "pot": ("pot", "Effektiviseringspotential (1 - Î¸)"),
    "k": ("k", "Kunddelningsfaktor"),
    "T_p": ("T_p", "Tillsynsperiod (Ã¥r)"),
    "T_r": ("T_r", "Realiseringstid (Ã¥r)"),
    
    # Kapitalbas
    "NUAV": ("NUAV", "NuanskaffningsvÃ¤rde"),
    "T_ek": ("T_ek", "Ekonomisk livslÃ¤ngd (halvÃ¥r)"),
    "D": ("D", "Avskrivning (kapitalfÃ¶rslitning)"),
    "R": ("R", "Avkastning (kapitalbindning)"),
    
    # Incitament
    "AIT": ("AIT", "Average Interruption Time (medelavbrottstid)"),
    "AIF": ("AIF", "Average Interruption Frequency"),
    "ILE": ("ILE", "Icke-levererad energi (kWh)"),
    "ILEffekt": ("ILEffekt", "Icke-levererad effekt (kW)"),
    "P": ("P", "Ã…rsmedeleffekt (kW)"),
    "d": ("d", "Avbrottstid (timmar)"),
    "k_NF": ("k_NF", "NÃ¤tfÃ¶rlustkostnad (kr/MWh)"),
    "s_NF": ("s", "Delningsfaktor nÃ¤tfÃ¶rlust"),
    "UG": ("UG", "Utnyttjandegrad"),
    "CEMI4": ("CEMI4", "Andel kunder med â‰¥4 avbrott"),
}


# =============================================================================
# HjÃ¤lpfunktioner fÃ¶r UI
# =============================================================================

def get_formula_with_caption(formula_key: str) -> tuple:
    """
    Returnerar formel och beskrivning fÃ¶r en given nyckel.
    
    AnvÃ¤ndning:
        formula, caption = get_formula_with_caption("WACC_REAL")
        st.latex(formula)
        st.caption(caption)
    """
    formulas_with_captions = {
        "HAMADA": (FORMULA_HAMADA, "Hamada-formeln: konverterar tillgÃ¥ngsbeta till aktiebeta"),
        "CAPM": (FORMULA_CAPM, "CAPM: kostnad fÃ¶r eget kapital"),
        "FISHER": (FORMULA_FISHER, "Fisher-ekvationen: nominell till real rÃ¤nta"),
        "WACC_NOMINAL": (FORMULA_WACC_NOMINAL_COMPLETE, "WACC nominell fÃ¶re skatt"),
        "WACC_REAL": (FORMULA_FISHER, "WACC real fÃ¶re skatt"),
        "EFFICIENCY_REQ": (FORMULA_ANNUAL_EFFICIENCY_REQ, "Ã…rligt effektiviseringskrav"),
        "DEA": (FORMULA_DEA_COMPACT, "DEA input-oriented optimering"),
        "DEA_SUPER": (FORMULA_DEA_LP, "DEA super-efficiency (exkluderar DMU i)"),
        "QUALITY_AIT": (FORMULA_QUALITY_COST_AIT, "Kvalitetskostnad baserat pÃ¥ AIT"),
        "QUALITY_AIF": (FORMULA_QUALITY_COST_AIF, "Kvalitetskostnad baserat pÃ¥ AIF"),
        "NETLOSS": (FORMULA_NETLOSS_INCENTIVE, "NÃ¤tfÃ¶rlustincitament"),
        "LOAD": (FORMULA_LOAD_INCENTIVE, "Belastningsincitament"),
        "INTAKTSRAM": (FORMULA_INTAKTSRAM_TOTAL, "Total intÃ¤ktsram"),
        "NORM_AIT": (FORMULA_NORM_AIT, "NormnivÃ¥ AIT som funktion av kundtÃ¤thet"),
        "NORM_AIF": (FORMULA_NORM_AIF, "NormnivÃ¥ AIF som funktion av kundtÃ¤thet"),
    }
    return formulas_with_captions.get(formula_key, (None, None))


def get_all_formula_keys() -> list:
    """Returnerar alla tillgÃ¤ngliga formelnyckar."""
    return [
        "HAMADA", "CAPM", "FISHER", "WACC_NOMINAL", "WACC_REAL",
        "EFFICIENCY_REQ", "DEA", "DEA_SUPER",
        "QUALITY_AIT", "QUALITY_AIF", "NETLOSS", "LOAD",
        "INTAKTSRAM", "NORM_AIT", "NORM_AIF"
    ]