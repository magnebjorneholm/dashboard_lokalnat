1. Gillar inte expanders. "What this model changes vs. the current one" ska alltid visas längst upp, inte i expander.

# Sector overview
2. Vi ska inte visuellt skriva ut "EIs_DEA", det är bara ett filnamn
3. I nuläget visas bara "median delta requirement" med "mean" i tooltip, borde gå att klämma in "mean delta..." bredvid "median delta"? eller är 5 KPI för mycket?
4. För markeringarna "Your firm: ***" så borde företagsnamnet användas. Dock är vissa namn väldigt långa, ska fixa så det finns förkortade namn
5. i histogrammet "delta efficiency vs. current model" så är de röda barsen bredare än de gröna av någon anledning... 
6. I båda histogrammen under taben "change (delta)", istället för "higher/lower (better/worse)" ska det va "higher/lower efficiency"

# Your company
7. Denna dupliceras väldigt mycket och jag tror det kan göras mycket smartare och snyggare. Att det dupliceras tror jag beror på att vi dels gör en del in-house och en del från återanvända funktioner. Jag tänker mig att endast följande ska finnas (varje bullet point nedan avser ny "row"/rad, samt så ska vi alltid ha precis som i frontend\results\m5_efficiency_output.py med st.metric så man får "delta" som markering med pil)
    - Efficiency score, efficiency requirement, raw och truncated potential, och rank
    - Waterfall med TOTEX, denna bygger jag senare.

# Explore
8. Vänta med denna.

# Experiment - fine-tune the model
9. Känns konstigt att detta är en expander längst ner, jag är inte säker på placering så vi avvaktar här med