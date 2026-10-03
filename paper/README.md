# Expanded PACT manuscript

This extends the supplied nine-page architecture paper, retaining its title,
authorship, nine main sections, two architectural figures and original benchmark.
Sections 2-6 preserve the original prose unchanged. The evaluation section adds
matched systems experiments, fault/policy probes, ablations, reuse, graph scaling,
reproducibility and explicitly unverified author-reported LLM aggregates.
The abstract, introduction provenance note, limitations and conclusion are updated.
The expanded PDF is 13 pages. The separate evaluation report remains supplemental.

## Build

Requires Python 3 and a TeX Live installation with the packages listed in the source.
From the repository root:

```bash
python paper/typeset.py
pdflatex -interaction=nonstopmode -halt-on-error -output-directory paper/build paper/build/PACT_From_Instructions_to_Procedures.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory paper/build paper/build/PACT_From_Instructions_to_Procedures.tex
```

The Markdown is the manuscript source; typeset.py preserves the paper style and
embeds tables from the recorded evaluation snapshot. Original model-benchmark
numbers are retained as historical reports, not new executions. The additional
LLM numbers remain author-reported and unverified. The measured deterministic
suite is in experiments/pact_evaluation/results; its source hashes are unchanged.
