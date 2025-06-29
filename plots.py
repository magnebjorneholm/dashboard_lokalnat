# plots.py

import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd

def plot_efficiency_histogram(eff_series, title="Effektivitet"):
    # Filtrera numeriska
    eff_series = pd.to_numeric(eff_series, errors="coerce").dropna()

    plt.figure(figsize=(8, 5))
    plt.hist(eff_series, bins=15, edgecolor='black')
    plt.title(title)
    plt.xlabel("Värde")
    plt.ylabel("Antal företag")
    plt.grid(True)
    st.pyplot(plt)
    plt.close()

def plot_efficiency_boxplot(eff_series, title="Effektivitet (boxplot)"):
    eff_series = pd.to_numeric(eff_series, errors="coerce").dropna()
    plt.figure(figsize=(6, 4))
    plt.boxplot(eff_series, vert=False)
    plt.title(title)
    plt.xlabel("Effektivitet")
    st.pyplot(plt)
    plt.close()

def plot_efficiency_vs_size(df, size_col="MWhl", eff_col="Effektivitet"):
    df = df.dropna(subset=[size_col, eff_col])
    x = pd.to_numeric(df[size_col], errors="coerce")
    y = pd.to_numeric(df[eff_col], errors="coerce")

    plt.figure(figsize=(8, 5))
    plt.scatter(x, y, alpha=0.7)
    plt.title("Effektivitet i förhållande till levererad energi (MWhl)")
    plt.xlabel("MWhl")
    plt.ylabel("Effektivitet")
    plt.grid(True)
    st.pyplot(plt)
    plt.close()
