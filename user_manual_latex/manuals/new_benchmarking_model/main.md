# Regumetrica

*Beta version*  
The new benchmarking model  
Method, results, and user guide  
Version 1.0

[www.regumetrica.com/um](https://www.regumetrica.com/um)

June 2026

---

> *Status: this is a method description. It sets out our operationalisation and reading of the direction the Swedish Energy Markets Inspectorate (Energimarknadsinspektionen, Ei) has taken for the benchmarking model, given the information the authority has published up to June 2026. Throughout, we separate what Ei has stated as its direction from our own working assumptions. Where the model rests on working assumptions, above all in parameter values and in the handling of data, the outcomes that follow are conditional on those assumptions. The figures in this manual are reported as conditional illustrations computed on current-regulation data; the manual explains the method and how to read the tool, not a forecast of the 2028 to 2031 levels.*

---

## Contents

- [1. Introduction](#1-introduction)
- [2. General principles](#2-general-principles)
- [3. Changes in the new model](#3-changes-in-the-new-model)
  - [3.1 The cost base](#31-the-cost-base)
    - [3.1.1 The OPEX variable](#311-the-opex-variable)
    - [3.1.2 The placement-environment correction](#312-the-placement-environment-correction)
    - [3.1.3 The merged TOTEX input](#313-the-merged-totex-input)
  - [3.2 Cable length as a structural variable](#32-cable-length-as-a-structural-variable)
  - [3.3 The two-sided efficiency requirement](#33-the-two-sided-efficiency-requirement)
  - [3.4 The monetary effect: two cost bases](#34-the-monetary-effect-two-cost-bases)
- [4. Using the tool](#4-using-the-tool)
- [5. Working assumptions and limitations](#5-working-assumptions-and-limitations)
- [6. Summary](#6-summary)
- [References](#references)

---

## 1. Introduction

The new benchmarking model is a standalone tool in Regumetrica. It answers one question: how would a network company be affected by Ei's proposed new benchmarking model if that change were made on its own and everything else were held constant. The tool is deliberately decoupled from the revenue-frame calculation. It does not build a regulatory case and does not feed the revenue cap; it isolates the benchmarking change so that its effect can be read on its own.

We wrote this manual for readers that know the building blocks, the DEA method, the capital base, and the cost posts, but not necessarily how the individual changes are constructed or how their combined effect can be measured. The text is mostly a method description, or more precisely our working interpretation of Ei's method. Where it quotes a number, the number is an illustration computed on the current regulatory period's data under our reading of Ei's method, and it is conditional on the working assumptions set out in Section 5.

Two features of the tool shape the rest of the manual. First, the model is fixed at a reference reading, so the page shows a result immediately and the only thing a user adjusts is a short set of fine-tuning controls. Second, the new model changes several things at once, which makes the combined effect easy to see but the contribution of any single change hard to isolate. The first of these is covered in the user guide (Section 4); the second is a caution that runs through the whole method and that a company should keep in mind when reading its own result.

The manual proceeds as follows. Section 2 states two principles that recur in several of the changes. Section 3 describes the changes in the model: how the cost base is built and how the efficiency requirement is computed. Section 4 is a short guide to the page. Section 5 lists our working assumptions and the data limitations on which the reported magnitudes depend, and Section 6 summarises.

## 2. General principles

Two principles return in several of the changes, and we state them once here so that each later change reads correctly.

Several of the changes correct for cost differences a network company cannot control, for example the electricity price in its bidding zone or the placement environment in its network area. The correction is made in the benchmarking, so that companies are compared on more equal terms. At the point where the incentive is applied, no such correction is made: the incentive works on the actual, uncorrected costs, so that relative prices carry through to the final outcome.

DEA measures each company against a frontier of the most efficient companies, and the reference level is read from the same distribution. The corrections in this manual redefine a cost post for every company at once, so the whole input is rescaled: the frontier is re-formed, which companies are efficient can change, and almost every company's relative position shifts. (A change to a single company would move the frontier only if that company is, or becomes, one of the frontier companies; a company in the interior moves only itself.) The effect of a change is therefore distributional rather than absolute: it reallocates outcomes between companies rather than creating or removing costs in absolute terms. This property is decisive for how the corrections should be read.

## 3. Changes in the new model

### 3.1 The cost base

The first group of changes concerns how the cost base that enters DEA is built. The starting point is a TOTEX approach: every cost post except regulatory fees enters one and the same cost variable (Ei 2026a). The reason is a fairer comparison. One company can have a higher capital cost but lower costs for subscriptions to the overlying grid, while another has the opposite composition. If companies are judged on only a subset of their costs, they are compared on their cost composition rather than on their total efficiency. Regulatory fees are excluded because they are neither controllable nor substitutable, but a fixed sum that follows from the number of customers and their voltage levels.

#### 3.1.1 The OPEX variable

The operating-cost variable collects the running costs. The controllable costs are reused from the baseline, so that the new and the current model start from exactly the same controllable figure and can be compared directly. To these we add price-adjusted network losses and a selection of non-controllable but substitutable posts. The composition is

$$
\mathrm{OPEX} = \text{controllable} \;+\; \text{valued losses}
\;+\; \sum \text{selected non-controllable} \;-\; \text{regulatory fees},
$$

where the valued losses are given by

$$
\text{adjusted losses} = \text{loss factor} \times \text{common price} \times
\text{energy fed in},
$$

summed over the forecast years and averaged.

Network losses enter TOTEX, which at the same time means that the standalone incentive for network losses is removed: a TOTEX model already gives an incentive to reduce losses, because a lower loss cost lowers the total cost (Ei 2025b). In the benchmarking, losses are valued at a common price rather than at each company's actual loss cost, because the actual cost depends on the electricity price in the company's bidding zone. This is the first principle above: the price difference is neutralised in the comparison, while the incentive works on the actual costs. Ei's direction allows network losses, subscriptions, or both to be valued at a common price (Ei 2026a). At present the model does this for network losses only, which follows from a data limitation, not a methodological choice (subscriptions, the largest non-controllable post at about 68 percent of it on current data, lack sufficiently detailed data).

Among the non-controllable posts, subscriptions to the overlying and neighbouring grid is the only one the direction names explicitly (Ei 2026a). It is included even though it is hard to influence in the short run, because it is substitutable against capital cost. Further posts are brought in under Ei's general criterion that a cost should be substitutable against, or controllable to, some degree. Beyond subscriptions, Ei names no specific posts; our working assumption is that grid subscription, grid connection, feed-in compensation, and capacity reserve are the included posts.

#### 3.1.2 The placement-environment correction

Building an electricity network costs different amounts depending on the placement environment, for example in an urban setting compared with the countryside, which a company normally cannot control given its network area. A company with a more expensive placement environment has a higher capital cost and therefore scores worse in the benchmarking in a way that does not reflect its genuine managerial efficiency. The direction is to adjust the acquisition value (anskaffningsvärde) of ground cable down to a common, reference level for the more expensive environments. Ground cable is included because it makes up a large part of the capital base (about 57 percent of total NUAV on current data); cable cabinets are excluded as negligible (about 4 percent); and a corresponding correction is made for substations (about 10 percent) (Ei 2026a).

The methodologically decisive observation is that the placement-environment premium is already in the price list. In their reporting, (Ei 2026a) only states that a flat-percentage deduction is applied to the total acquisition value of ground cable, without specifying how the percentage is derived; deriving it from the price list, as we do, is therefore our current working operationalisation, and any uncertainty in outcomes concerns how well it matches the method Ei will eventually adopt and the relative magnitude of the two. Each cable type's price per kilometre is set for the exact cable type in its specific placement environment, so an urban cable has a higher price than the same cable type in the countryside. The correction is therefore not a measurement problem but a re-pricing problem: to level a cable, one replaces its price with the rural-normal price for the same cable type. The premium does not need to be estimated externally; it is the difference between the environment's price and the rural-normal price in the same list. From this price structure we derive a flat percentage deduction per placement environment, which is the form the direction asks for so that detailed reporting per cable type is not needed (Ei 2026a). That the flat percentage is accurate enough is confirmed by the fact that it nearly coincides with an exact re-pricing per cable type at the sector level.

Two properties of the correction are easy to misread. First, the whole placement-environment gradient is levelled down to rural normal, including difficult rural terrain, so the correction is not a relief for urban networks alone. Second, it adjusts downward only: a cable cheaper than rural normal is left unchanged. This downward-only asymmetry is our reading; Ei says only that values are adjusted down to the rural-normal level. The correction can therefore only reduce the measured regulatory value of the capital base. Because DEA is relative, its effect on the individual company's requirement is distributional, in line with the principle above. As an illustration on current data, the correction removes approximately 20 percent of the sector's unadjusted capital cost, about 4.8 billion SEK per year, and the percentages we use are our derivation from the price list rather than figures Ei has published.

#### 3.1.3 The merged TOTEX input

In the current model the controllable running costs and the capital cost enter DEA as two separate inputs. In the new model they are merged into a single TOTEX input. The reason, according to the direction (Ei 2026a), is that today's regulation gives an incentive not to invest in overly expensive plant but no incentive to choose the most cost-effective solution, whether that solution runs through operating costs or through investment. With a merged cost variable a company is judged on its total cost rather than on the split between running costs and capital, which makes the comparison solution-neutral. One consequence is that operating efficiency and capital efficiency can no longer be judged separately; what is measured is total cost efficiency.

### 3.2 Cable length as a structural variable

DEA relates costs to the outputs a network is built to deliver. The current model's DEA uses five output-side variables: four production outputs, the number of connection points, the maximum subscribed/withdrawn power, and energy delivered at low and high voltage, and one structural variable, the number of network stations, which corrects for differences in density. The new model adds physical line length as a second structural variable (Ei 2026a). Like the number of network stations, line length captures low customer density: two companies that deliver the same energy to the same number of customers can require very different amounts of plant if one covers a sparse, low-density area and the other a dense one. For some companies line length is the better measure of low density, which is why Ei adds it. Our working assumption is that the line-length variable counts the electrical line types and excludes optical fibre.

### 3.3 The two-sided efficiency requirement

The second change concerns how the efficiency requirement is computed from the DEA outcome. Let $E_i$ denote company $i$'s efficiency. In the current model each company is measured against the frontier ($E = 1$), and the potential, the distance to the frontier, is always non-negative. The potential is truncated at a lower and an upper bound. The lower bound gives every company a minimal requirement, set at one percent per year, in line with the sector's general productivity development; the upper bound caps the largest potentials (Ei 2024). The result is that every company receives a deduction, and this lower bound works in practice as a general efficiency requirement laid on all.

In the new model the reference point is moved from the frontier to the third quartile, that is, to the efficiency level $E_{75}$ at the 75th percentile, computed excluding outliers. The gap is defined as

$$
\text{gap} = E_{75} - E_i,
$$

and can now be negative. A company below the threshold has its revenue frame decreased, a company at the threshold receives full cost coverage (no adjustment), and a company above the threshold has its revenue frame increased. Because the threshold sits at the 75th percentile, it is by definition the top quarter that receives full coverage or more (Ei 2026b). The choice of the third quartile as the reference follows practice in Great Britain, which Ei cites as a precedent (Ei 2026b). One implication is that the benchmark is *moving* and relative: it is recomputed each supervision period from the current distribution, so it rises as the sector as a whole becomes more efficient. With this, today's floor and fixed outlier requirement are removed, and there is no separate general efficiency requirement in the new model (Ei 2026b).

The calculation chain from gap to annual requirement keeps its form in all essentials from today's model. This is clearest when the two formulas are set side by side, where $s$ is the customer share, $\operatorname{clip}$ truncates the argument to the stated interval, and the factor $\tfrac{4}{8}$ scales for the potential being realised over eight years while the requirement is set per four-year supervision period (Ei 2026b):

$$
\begin{aligned}
  \text{Current:} \quad
    & \text{requirement} = \Bigl(1 + \operatorname{clip}\bigl(1 - E_i,\ \text{floor},\ \text{cap}\bigr)
      \cdot s \cdot \tfrac{4}{8}\Bigr)^{1/4} - 1, \\[2pt]
  \text{New:} \quad
    & \text{requirement} = \Bigl(1 + \operatorname{clip}\bigl(E_{75} - E_i,\ -\text{cap},\ +\text{cap}\bigr)
      \cdot s \cdot \tfrac{4}{8}\Bigr)^{1/4} - 1.
\end{aligned}
$$

What has changed is the definition of the gap and that the sign can become negative. Table 1 summarises the difference.

**Table 1.** The computation of the efficiency requirement in the current and the new model.

| | Current | New |
|---|---|---|
| Reference point | frontier ($E = 1$) | third quartile ($E_{75}$) |
| Sign | deduction only | deduction and addition |
| Driver of magnitude | gap to the frontier | gap to $E_{75}$ |
| Floor | yes, gives a general requirement | no |

One structural property is worth raising: the two-sidedness is skewed. Efficiency is capped at its highest value and the threshold sits near the top, so a company can lie only a little above the threshold but considerably below it. The reward side is therefore structurally limited while the deduction side can be large, whatever level a symmetric cap is set at. The two-sidedness is genuine but uneven in substance.

The concrete parameter values in this chain, the customer share, the cap on the gap, and the realisation scaling, have not yet been published by Ei. We have fixed them as working assumptions, chosen to mirror today's calculation chain, and we report them in Section 5. The level of the cap is explicitly one of the authority's open questions (Ei 2026b).

As an illustration on current data, the third-quartile reference is $E_{75} \approx 0.93$. Of the 145 scored companies (excluding three outliers), 107 receive a deduction to its revenue frame, 37 receive an addition, and 1 lands at full coverage. We report the outcome as the impact on the revenue frame. The annual outcomes range from about $-1.82$ percentage points per year to about $+0.43$ percentage points per year, with a median of about $-0.61$ percentage points per year. That roughly three quarters of companies fall on the deduction side is expected by construction, since the threshold is the 75th percentile.

### 3.4 The monetary effect: two cost bases

The efficiency requirement/addition is a percentage. The monetary effect is the percentage applied to a cost base over the four-year supervision period, and the two models apply their percentage to different bases (Ei 2025b). The current model applies its percentage to an operating-cost base, and the new model applies its percentage to the full uncorrected TOTEX: controllable costs, annualised non-controllable costs, the actual network losses at their actual cost, the selected non-controllable posts, and the unadjusted capital cost.

Two things follow. First, in line with the first principle, the benchmarking corrections, the common loss price and the placement-environment levelling, set the percentage but never the monetary base. The base is the company's actual, uncorrected costs. Second, because the new percentage is applied to a much larger base, an outcome can fall in percentage terms yet rise in monetary terms. On current data this is the case for about half of the companies (roughly 52 percent), and it is the headline result of the comparison. For the sector as a whole, the new model roughly doubles the aggregate requirement in monetary terms, from about 1.4 billion SEK to about 2.8 billion SEK over the four-year period. We note that this doubling is largely mechanical, the incentive applied to the whole TOTEX rather than to operating cost alone, and not a new empirical finding.

## 4. Using the tool

The page is simple to operate, because the model is fixed at the reference reading described above and almost nothing needs to be set.

Select a company in the sidebar. The main model runs for all companies at once; it is pre-computed, so the result appears immediately. The verdict at the top states whether the new model raises or lowers the company's revenue frame relative to the current model, with a higher cap shown as positive. Four cards give the supporting figures, each as the change from the current model: the efficiency requirement as an annual percentage, the same outcome in monetary terms over the period, the company's efficiency rank among the scored companies, and its DEA efficiency. A note under the cards repeats that these are the isolated effect of the benchmarking change on current-regulation data, not a forecast.

Below the verdict the result is grouped into two views. The model-outputs view shows where every company falls relative to the third-quartile benchmark $E_{75}$, the distribution of outcomes across the sector, the counts of companies with a lower cap, full coverage, and a higher cap, and three company-by-company comparisons of the new model against the current one (rank, efficiency, and the revenue-frame impact). The TOTEX decomposition shows a waterfall from the old cost base to the new DEA TOTEX in two phases: first the cost posts the new model brings in that the old did not, the network losses and the selected non-controllable posts, then the benchmarking corrections, the losses revalued to a common price and the placement-environment levelling of capital cost split into cable and station. When an outcome improves in percentage terms but costs more in monetary terms, or the reverse, the tool says so in words, because the two models apply the percentage to different bases.

One panel is adjustable. The Experiment expander lets a user change three things on top of the fixed main model: the common loss price in SEK per megawatt hour; the placement-environment method for cable and for station, either the exact re-pricing or a flat-percentage schablon; and which line types feed the cable-length output. The DEA run is heavy, so it fires only when the *Run experiment* button is clicked; editing the controls merely marks pending changes. The *Reset to main model* button returns to the reference reading. Everything else, the TOTEX composition, the outputs, and the returns to scale, is fixed at the main-model specification. These controls are for exploration; the defaults reproduce the reference reading on which the figures in this manual rest.

## 5. Working assumptions and limitations

The following points are our working assumptions or follow from the available data, and should be read as such until the authority's specification is published. All magnitudes reported separately are conditional on them.

*The two-sided requirement.*

1. The customer share, the cap on the gap, and the realisation scaling have not been published by Ei. We have fixed them to mirror today's calculation chain, which gives a customer share of $0.50$, a symmetric cap of $0.30$ on the gap, and a realisation factor of $4/8$, so that the maximum deduction is about $1.82$ percentage points per year, equal to today's cap. The level of the cap is an open regulatory question.
2. That the magnitude is set by the cardinal gap, and that the floor and the fixed outlier requirement are removed, is our reading of a functional form the authority has not fixed.

*The placement-environment correction.*

3. The concrete percentages are our derivation from the price structure; the authority's official flat-percentage deduction has not yet been published.
4. The premium is derived from the norm-value list, while the coming method targets the acquisition value (Ei 2025a), which is missing from nearly all available data. The derivation therefore rests on the assumption that the price relation between placement environments is the same in acquisition value as in norm value. The assumption is reasonable but not verifiable from this data.

*The OPEX variable.*

5. Valuing only network losses, and not subscriptions, at a common price at present follows from a data limitation, not from a methodological choice.
6. The selection of non-controllable posts beyond subscriptions rests on the general substitutability criterion and is classified in the data pipeline.
7. The mixing of periods and the choice of forecast period are known model simplifications that mirror today's model.

*Scope and inference.*

8. Three companies that Ei treats as unsuitable for DEA are removed from the reference set and from the third-quartile benchmark and are left unscored, so the reported outcome figures cover 145 scored companies.

## 6. Summary

1. The cost base is built as a TOTEX: every post except regulatory fees is collected into one cost variable, so that companies are compared on total cost rather than on cost composition, and the two earlier inputs are merged into one.
2. Network losses are valued at a common price and the placement environment is levelled to a common level, both under the principle of normalising in the comparison while giving the incentive on the actual costs. Physical line length is added as a new structural output.
3. The efficiency requirement becomes two-sided: the reference moves from the frontier to the third quartile, the requirement can become negative, the top quarter receives full coverage or more, and today's floor is removed. The two-sidedness is structurally skewed.
4. Because the new percentage is applied to the full TOTEX rather than to operating cost alone, an outcome can fall in percentage terms yet rise in monetary terms, which holds for about half of the companies and roughly doubles the sector's aggregate requirement in monetary terms on current data. The combined effect should be read as the joint effect of all the changes at once.
5. Parameter values and several data choices are working assumptions, not the authority's decisions, and the magnitudes reported separately are conditional on them.

## References

Citations use the short form "(Ei YEAR)" for Energimarknadsinspektionen; where two sources share a year they are distinguished by a/b.

- **Ei 2024** — Energimarknadsinspektionen (2024). *Bilaga 9 – Effektiviseringskrav för lokalnätsföretag.* Författare Mattias Önnegren. För tillsynsperioden 2024–2027.
- **Ei 2025a** — Energimarknadsinspektionen (2025). *Inriktning för reglering av elnätsföretagens intäktsramar 2028–2031.* PowerPoint-presentation. [Source](https://ei.se/download/18.5dd55f67196f65729054863/1749545562024/Presentation-Inriktning-f%C3%B6r-reglering-av-eln%C3%A4tsf%C3%B6retagens-int%C3%A4ktsramar-2028-2031-Ei.pdf)
- **Ei 2025b** — Energimarknadsinspektionen (2025). *Tillämpningsmetod för effektiviseringsincitament i elnätsregleringen.* [Source](https://ei.se/om-oss/projekt/pagaende/intaktsramar-elnat-och-gasnat/intaktsramar-elnat-2024-2027/2025-12-10-tillampningsmetod-for-effektiviseringsincitament-i-elnatsregleringen)
- **Ei 2026a** — Energimarknadsinspektionen (2026). *Ny modell för benchmarking i elnätsregleringen.* [Source](https://ei.se/om-oss/projekt/pagaende/intaktsramar-elnat-och-gasnat/intaktsramar-elnat-2024-2027/2026-05-29-ny-modell-for-benchmarking-i-elnatsregleringen)
- **Ei 2026b** — Energimarknadsinspektionen (2026). *Nytt om effektiviseringsincitament i elnätsregleringen.* [Source](https://ei.se/om-oss/projekt/pagaende/intaktsramar-elnat-och-gasnat/intaktsramar-elnat-2024-2027/2026-05-12-nytt-om-effektiviseringsincitament-i-elnatsregleringen)
