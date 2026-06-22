Chefen gillar Shapley-analysen i new_benchmarking_model/analysis/ (s4 LOO/AOI, s5 Shapley) och vill att den utvecklas vid sidan om för intressentmöten med Energimarknadsinspektionen (Ei). Den är fullt inkopplad men dold i V1-dashboardens UI (company_view.py HIDDEN_CHART_GROUPS, gruppen "Outcome decomposition").

Planerade utbyggnader och andra observationer.
1. Vi måste alltid se att vi använder rätt dataset, se minne opexp-vs-controllable-average-mismatch.
2. DEA-motorn är ren Python (PuLP/CBC supereffektivitet i calculations/frontier/), INTE rDEA. Kolla och bekräfta hela tiden vilken outlier-iteration vi kör, ska vi köra samma "dynamisk tills inga andra är outliers" hela tiden (många körningar men "korrektare") eller ha förbestämda outliers? (svagare eftersom outliers i nuvarande modell baseras på annan specifikation)
3. En ytterligare Shapley med effektivitet (cappad DEA min(θ,1)) som utfall istället för det tvåsidiga kravet, särskils mot föregående analys med mapp och filsuffix _eff vs _req. Notera att "antal spelare" skiljer sig mellan analyserna,
4. Dela upp non-controllable (idag en hopslagen spelare) i dess fyra kategorier — grid_subscription, grid_connection, feed_in_compensation, capacity_reserve. Spelarna går 4→7, Shapleyn 2⁴=16 → 2⁷=128 DEA-körningar (offline, ~12 min). De fyra per-kategori-kolumnerna finns redan i precomputade totex.parquet.
5. från "3. och 4." följer att den nuvarande analysen "req" måste köras om.
6. När vi gör om analyserna så vill jag att vi parametriserar scripts, snygga till mappstrukturen för outputs, sparar så mycket outputs som möjligt på så detaljerad nivå som möjligt (företagsnivå är minsta?) (kanske andra outputs från va vi har nu och intermediärer också)
