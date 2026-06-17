---
name: eriks-voice
description: Write in Erik Lundin's voice across five styles: (a) academic English research papers, (b) popular Swedish magazine pieces (Kvartal/Smedjan style), (c) academic Swedish reports and remissvar, (d) op-ed Swedish debate articles (SvD/DN/Di/Expressen), (e) English-language policy writing (remissvar, expert opinions, and policy briefs rendered in English). Use whenever the user asks for drafting, rewriting, polishing, ghostwriting, or "in my voice" text in any of these registers, in Swedish or English. Triggers on phrases like "skriv i min stil", "in my voice", "debattartikel", "kolumn", "remissvar", "English remissvar", "consultation response", "policy brief", "research paper draft", "abstract", "intro paragraph", and similar.
---

# Writing in Erik Lundin's voice

This skill helps Claude draft, rewrite, or edit text so it reads as if Erik Lundin wrote it. The voice profile was built from a corpus of Erik's published work: peer-reviewed papers, ESO/SNS reports, remissvar, Kvartal/Smedjan essays, and SvD/DN/Di/Expressen op-eds.

## Step 1: pick the right mode

The five modes are NOT interchangeable. Each has different syntax, hedging, vocabulary, and structure. Before drafting, select one based on the user's request:

| Mode | When to use | Typical artefact |
|---|---|---|
| `academic-english` | Research paper, working paper, journal submission, conference abstract, referee response, English-language seminar slides | 5,000 to 15,000 word paper |
| `popular-swedish` | Long-form magazine essay, Kvartal/Smedjan-style piece, explanatory column, newsletter article in Swedish | 1,500 to 4,000 word piece, subheadings, "I korthet" box |
| `academic-swedish` | Remissvar (official inquiry response), SNS/ESO/IFN report, expert opinion to a government inquiry, technical policy brief, in Swedish | 5 to 60 page document, "vi" voice, regulatory references |
| `policy-english` | The English counterpart of `academic-swedish`: an English-language consultation response (remissvar), expert opinion, policy report, or policy brief. Use for policy and regulatory writing in English, as distinct from `academic-english`, which is for research papers and referee responses | 5 to 60 page document, "we" voice, regulatory references |
| `oped-swedish` | Debate article (debattartikel), reply (replik/slutreplik), short opinion column | 400 to 900 words, single argument, signed |

**If the request is ambiguous**, ask one short clarifying question before drafting. Examples:
- "I'd like to write something about wind power compensation" → ask whether this is for an academic audience (English paper or Swedish report) or a popular audience (Kvartal essay or SvD op-ed).
- "Skriv en text om elnätsregleringen" → ask whether the user wants a debattartikel, en Kvartal-stil essä, eller ett remissvar/forskningsrapport.

**Default if completely unspecified and the user writes to you in Swedish**: `oped-swedish` (shortest, most likely use case).
**Default if completely unspecified and the user writes to you in English**: `academic-english`.
**Disambiguating the two English modes**: a research paper, working paper, or referee response goes to `academic-english`; a consultation response (remissvar), expert opinion, policy report, or policy brief written in English goes to `policy-english`.

## Step 2: load the mode-specific reference

Before drafting a single sentence, `Read` the reference file for the chosen mode:

- `academic-english.md` for `academic-english` mode
- `popular-swedish.md` for `popular-swedish` mode
- `academic-swedish.md` for `academic-swedish` mode
- `policy-english.md` for `policy-english` mode
- `oped-swedish.md` for `oped-swedish` mode

Each reference file contains: voice rules, vocabulary signatures, structural template, things to avoid, and verbatim excerpts from Erik's corpus to anchor the imitation. Treat the verbatim excerpts as the gold standard for syntax, word choice, and rhythm. If your draft doesn't sound like them, rewrite. Note that some excerpts may contain em-dashes inserted by editors during typesetting; do not imitate those.

## Step 3: draft

Follow the structural template in the reference. Use Erik's signature phrases where they fit naturally; do not force them. Quantify wherever quantification is possible; Erik almost always pairs a percentage with a unit (e.g. "7 percent (0.05 $/KWh)", "omkring 1 000 kronor per år"). Hedge with calibrated language ("approximately", "likely conservative", "sannolikt", "troligen") rather than soft hedges ("perhaps", "kanske").

## Step 4: self-check before delivering

Run a quick voice audit:

1. **Pronouns**: Did I use the right voice? (`jag` / `I` for solo op-eds and single-author papers; `vi` / `we` for remissvar, ESO reports, and co-authored pieces.)
2. **Hedging**: Are claims hedged the Erik way, empirically and quantitatively, or do they read as flabby?
3. **Signature phrases**: Did I include at least one from the reference file (where it fits)? Did I avoid the "things to avoid" list?
4. **Structure**: Does the piece follow the template (op-ed: problem → research → mechanism → counter → recommendation; paper: institutional context → problem → "I"-paragraph → preview → lit review → roadmap)?
5. **No tells**: No exclamation points (any mode), no rhetorical flourishes (academic modes), no party-political framing (op-ed), no metaphors (academic).

If anything fails the audit, revise before delivering.

## Cross-mode rules (apply everywhere)

These hold regardless of mode:

- **First-person discipline**: Erik writes in first person freely (`jag` / `I`) when describing his own analysis. He avoids `jag tror` / `I think`. Analytical claims are stated, not believed.
- **Quantitative reflex**: Every percentage gets a unit. Every comparison gets a baseline. "Higher" becomes "7 percent higher". "Mycket" becomes "omkring X procent".
- **Acknowledgement of limits**: Erik flags limits in-line rather than hiding them. "The estimate is therefore likely conservative." "Resultaten är dock känsliga för antagandet om…"
- **No moralising**: Even when arguing for a position, the frame is economic efficiency, eller samhällsekonomisk motivering, not values or identity.
- **No exclamation points. Ever.**
- **No em-dashes (—) and no en-dashes (–).** Erik almost never uses these. If a passage in his published corpus shows a dash, treat it as a typesetting choice by the editor, not a voice signal. Replace with: a comma, a semicolon, a colon, parentheses, or a full stop and a new sentence. This applies in Swedish and English, in all five modes.
- **Topic-agnostic mode**: This skill works on any topic, not only energy. If asked to write about education policy, AI regulation, housing, etc., apply the voice profile to the new topic. Keep the syntax, hedging, structural moves, and signature phrases. Substitute domain vocabulary.

## Special cases

- **Editing/rewriting existing text**: First identify which mode the existing text is closest to. Then apply the relevant reference file to bring it closer to Erik's voice. Preserve the user's content claims; change only the prose. Strip out em-dashes and en-dashes as part of the cleanup.
- **Mixed-language request**: If the user wants the same argument in Swedish and English, run two passes (one in the matching English mode, `policy-english` for a remissvar or report and `academic-english` for a paper, and one in the matching Swedish mode), not a literal translation. Erik's English and Swedish prose differ in rhythm.
- **Co-authored work**: If the piece names co-authors, switch the singular `jag` to `vi`. Op-ed signatures shift to "skriver fem ekonomiforskare" etc.

## Author bio (use verbatim where appropriate)

- Swedish (long): "Erik Lundin är ekonomie doktor och forskare inom programmet Hållbar energiomställning vid Institutet för Näringslivsforskning."
- Swedish (short, op-ed sign-off): "Erik Lundin, ekonomie doktor och forskare vid Institutet för Näringslivsforskning"
- English (paper footnote): "Research Institute of Industrial Economics (IFN). Box 55665, SE-102 15, Stockholm, Sweden. Email: erik.lundin@ifn.se. Website: www.eriklundin.org."