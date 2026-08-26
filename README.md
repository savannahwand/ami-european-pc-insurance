# Agentic Maturity Index for European P&C Insurance

Code, dictionary, and derived data for an MSc research project building an
**Agentic Maturity Index (AMI)** for 29 European property and casualty insurers,
using natural language processing of two independent evidence sources: annual
reports and regulatory filings, and job postings.

**Author:** Savannah Wand
**Supervisor:** Rui Zhu, Bayes Business School, City St George's, University of London
**Sponsor:** Alchemy Crew Ventures
**Submitted:** BBM110 General Research Project, 2026

---

## What this repository contains

The pipeline scores each company on two independent tracks, standardises both,
and combines them into a single 0–100 score bucketed into three maturity phases.

| Track | Source | Measure |
|---|---|---|
| Report-side | 86 annual reports and regulatory filings, FY2022–2025 | Agentic share of all automation language |
| Postings-side | 2,984 EU/UK job postings (current snapshot) | Mean agentic-signal density per posting |

Scoring uses a versioned signal dictionary (v0.7: 1,490 terms, 13 languages)
and a rule-based matcher, rather than a supervised classifier, so that every
score can be traced back to a specific phrase match in a named source document.

---

## Repository structure

```
├── src/
│   └── ami_signal_matcher.py        Rule-based phrase matcher (v0.2.2)
├── dictionary/
│   └── ami_signal_dictionary.yaml   Signal dictionary (v0.7)
├── notebooks/
│   ├── 01_report_pipeline.ipynb            Report extraction and scoring
│   ├── 02_job_postings_nlp.ipynb           Postings cleaning and scoring
│   ├── 03_report_eda.ipynb                 Report-side EDA
│   ├── 04_job_scaling_eda.ipynb            Job-postings EDA
│   ├── 05_combine_scoring_seniority.ipynb  Main scoring pipeline
│   └── 06_ml_analysis.ipynb                Clustering, GMM, bootstrap
├── data/
│   ├── processed/                   Derived, analysis-ready CSVs
│   └── manifest/                    Source document index (see data/README.md)
└── figures/                         Generated plots
```

---

## Setup

Requires Python 3.11 or later.

```bash
# 1. clone
git clone https://github.com/YOUR-USERNAME/ami-european-pc-insurance.git
cd ami-european-pc-insurance

# 2. create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. install dependencies
pip install -r requirements.txt

# 4. launch
jupyter lab
```

---

## Running the analysis

Notebooks are designed to be run **in order**, since later ones depend on CSVs
written by earlier ones. Notebooks 01 and 02 require the source corpus, which is
not redistributed here — see [`data/README.md`](data/README.md).

| Order | Notebook | Produces |
|---|---|---|
| 1 | `01_report_pipeline.ipynb` | Report-side scores per company-year |
| 2 | `02_job_postings_nlp.ipynb` | Posting-level signal counts and densities |
| 3 | `03_report_eda.ipynb` | Report-side exploratory analysis |
| 4 | `04_job_scaling_eda.ipynb` | Job-postings exploratory analysis |
| 5 | `05_combine_scoring_seniority.ipynb` | AMI scores, phases, archetypes, seniority supplement |
| 6 | `06_ml_analysis.ipynb` | k-means, GMM, bootstrap validation |

Because the derived CSVs in `data/processed/` are included, notebooks 03–06 can
be run without reconstructing the source corpus.

**Restart the kernel and run all cells in sequence** before treating any output
as final. Several silent errors during development traced to stale kernel state
where a variable defined in a deleted cell was still resolving.

---

## Two things that will break the pipeline if changed

**1. The dictionary path must be passed explicitly.**

```python
load_dictionary(path=DICT_PATH)     # correct
load_dictionary()                   # will not pick up the YAML on disk
```

**2. Dictionary edits must be made in the YAML file, not in a notebook cell.**
Terms added to an in-notebook dictionary object have no effect on a real scoring
run. Edit `dictionary/ami_signal_dictionary.yaml`, then re-run.

---

## Method summary

**Report-side aggregation.** Raw agentic and prior-generation-automation hit
counts are summed across all available years *before* taking the ratio, rather
than averaging yearly ratios or using the latest year only:

```
agentic_share = Σ raw_agentic / Σ (raw_agentic + raw_prior_gen_automation)
```

**Combination.** Both tracks are z-scored, binned into quartiles, and combined
on a 4×4 grid with a penalty for disagreement between the two:

```
score = max(0, (report_bin + postings_bin)/6 × 100 − GAP_PENALTY × |report_bin − postings_bin|)
```

with `GAP_PENALTY = 12`. Two alternative combination methods (bottleneck and
distance-from-origin) are implemented for comparison; all three agree at
Spearman ρ = 0.88–0.99.

**Archetypes.** Companies are classified by the sign of their two z-scores:
Aligned Leaders (high/high), Talkers (high report, low postings), Quiet Builders
(low report, high postings), Laggards (low/low).

---

## Known limitations

These are documented in full in the report; the ones that matter most for anyone
re-using this code:

- **Thin denominators.** 13 of 29 companies register fewer than 20 total
  automation hits across their entire corpus. Extreme scores are the least
  reliable, not the most.
- **Undefined ratios.** One company (Bolttech) has zero hits in both categories,
  making its ratio mathematically undefined; the pipeline returns 0.0.
- **No lemmatisation.** Morphological variants (`deploy` / `deploys` /
  `deployed`) are matched as separate strings.
- **Risk framing is not distinguished from deployment.** A firm describing AI as
  an industry-wide risk scores identically to one describing its own rollout.
- **Peer-relative scoring.** Scores are quartile positions within this specific
  29-company sample, not absolute measures. Changing the sample changes the
  scores.

---

## Data availability

Source documents are **not** redistributed in this repository. See
[`data/README.md`](data/README.md) for what is included, what is not, and how to
reconstruct the corpus from public sources.

---

## Citation

If you use this dictionary, matcher, or method, please cite the accompanying
report:

> Wand, S. (2026) *The Agentic Maturity Index: Mapping Human–Agent Ratios in
> European P&C Insurance.* MSc research project, Bayes Business School, City
> St George's, University of London.
