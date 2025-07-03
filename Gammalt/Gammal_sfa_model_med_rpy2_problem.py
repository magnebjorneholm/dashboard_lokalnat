import pandas as pd
import numpy as np
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri, default_converter
from rpy2.robjects.conversion import localconverter

def run_sfa_model(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Filtrera bort negativa eller nollvärden
    vars_required = ['OPEXp', 'CAPEX', 'MW', 'NS', 'MWhl']
    df = df[(df[vars_required] > 0).all(axis=1)].copy()

    # 2. Log-transformera
    df['ln_OPEXp'] = np.log(df['OPEXp'])
    df['ln_CAPEX'] = np.log(df['CAPEX'])
    df['ln_MW'] = np.log(df['MW'])
    df['ln_NS'] = np.log(df['NS'])
    df['ln_MWhl'] = np.log(df['MWhl'])

    # 3. Skicka till R via rpy2
    with localconverter(default_converter + pandas2ri.converter):
        robjects.globalenv['df_r'] = pandas2ri.py2rpy(df)

    # 4. Kör SFA-modellen i R
    frontier = importr("frontier")
    robjects.r('''
    library(frontier)
    model <- sfa(
        ln_MWhl ~ ln_OPEXp + ln_CAPEX + ln_MW + ln_NS,
        data = df_r,
        truncNorm = TRUE
    )
    u_hat <- efficiencies(model)
    ''')

    # 5. Extrahera ineffektivitet û och beräkna effektivitet
    u_hat = np.array(robjects.r['u_hat']).ravel()
    theta = np.exp(-u_hat)  # Effektivitet

    # 6. Effektivitetskrav enligt samma metodik som DEA
    revred = 1 - theta
    revred_compress = np.clip(revred, 0.162416, 0.3)
    effkrav_proc = ((1 + revred_compress / 4) ** 0.25) - 1

    # 7. Sätt ihop slutlig resultattabell
    df_result = df[["DMU", "Företag", "OPEXp", "CAPEX", "MW", "NS", "MWhl"]].copy()
    df_result["Effektivitet"] = theta
    df_result["Effkrav_proc"] = effkrav_proc

    return df_result
