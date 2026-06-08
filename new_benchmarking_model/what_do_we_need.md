1. TOTEX + nätförlustkostnader värderat till gemensamt pris nf_obs · k_nf · e_in
2. Alla outputs finns med undantag för **MWhh gränspunkt**, kolla om det är samma (antar det)
3. ledniningens fysiska längd (inte fågelvägen) i km finns för alla subcat som count_comp. Kommer med all sannolikhet va **output**
4. Förläggningsmiljö
    - Ja, för jordkabel finns redan kodade i subcat-kolumnen i capbase_a med exakt de fyra nivåerna Ei refererar till: jordkabel landsbygd normal (baslinje enligt Ei), jordkabel landsbygd svår, jordkabel tätort, jordkabel city
    - Nej för stationer, subcat-värdena är nätstation, station, kopplingsstation, tillägg nätstation, kontrollutrustning, station — inte uppdelade på förläggningsmiljö.

Klar?
1. Förläggningsmiljö för kabel och station är klar.
2. OPEX (benchmarking) = påverkbara (controllable_cost_average)
                    + nätförluster till gemensamt pris   (nf_obs · k_nf · e_in)
                    + grid_subscription + grid_connection
                    + feed_in_compensation + capacity_reserve
                    − regulatory_fees (exkluderas)
    - Notera Periodglapp: påverkbara är 2018-2021, opåverkbara 2024-2027.
3. Kabellängd klar