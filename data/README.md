# Data

## What is in this repository

| Path | Contents |
|---|---|
| `processed/ami_results_wide.csv` | Report-side scores, one row per company-year (86 rows): token counts, raw agentic and prior-generation hit counts, agentic share, and per-dimension densities per 10k words. |
| `processed/posting_level_detail.csv` | Posting-level signal counts for the 2,984 cleaned EU/UK postings, with company, country, region, job title, and matched phrases. |
| `processed/phrase_detail.csv` | Phrase-level match counts by company, country, and dictionary category. |
| `processed/company_summary.csv`, `company_country_summary.csv`, `region_summary.csv` | Postings aggregates at company, company-country, and region level. |
| `processed/job_postings_combined_cleaned.csv` | Cleaned job postings data including EU, UK, and non-EU/UK job postings|
| `manifest/document_manifest.csv` | Index of all 86 source documents: company, tier, financial year, document type, source type, and filename. |


## What is NOT in this repository, and why

**Source PDFs (86 annual reports, SFCRs, and financial statements).**
Not redistributed. These are third-party copyrighted documents and would exceed
GitHub file-size limits. Individual source URLs were not recorded at collection
time, but every document is publicly available from the issuing company's
investor-relations page (annual reports and financial statements) or its
Solvency II regulatory disclosures (SFCRs). The combination of company, year,
and document type in `manifest/document_manifest.csv` identifies each one
uniquely. A copy of the full PDF corpus has been shared separately with the
project supervisor.

**Raw job-postings scrape (134,682 postings).**
Not redistributed. Collected from company career pages and one aggregator whose
terms do not permit redistribution. The derived, analysis-ready file
(`processed/posting_level_detail.csv`) is included instead.

**Sponsor documents.**
The project specification and methodology documents provided by Alchemy Crew
Ventures are marked confidential and are not included.

## Reconstructing the corpus

1. For each row in `manifest/document_manifest.csv`, locate the document on the
   issuing company's investor-relations page or Solvency II disclosures, using
   the company, year, and doc_type columns.
2. Save to `data/raw/reports/` using the exact filename given in the manifest —
   the pipeline matches documents to companies by filename.
3. Run the notebooks in the order given in the top-level README.

Note that job postings are a **current snapshot** and are not reproducible after
the fact: postings are removed once filled, so re-running the collection will
produce a different corpus. This is a deliberate methodological constraint, not
an oversight — historical postings are not reliably archived.

Because the derived CSVs above are included, the scoring, combination, and
validation stages (notebooks 03–06) can be reproduced without reconstructing the
source corpus. Only notebooks 01 and 02 require the raw documents.

## Column reference — `ami_results_wide.csv`

| Column | Meaning |
|---|---|
| `company`, `tier`, `year` | Identifiers |
| `doc_type` | Annual Report / SFCR / Financial Statement |
| `filename` | Source file, matches the manifest |
| `tokens` | Whitespace-normalised token count for the document |
| `raw_agentic` | Phrase hits passing the agentic gate |
| `raw_prior_gen_automation` | Phrase hits routed to the prior-generation denominator |
| `agentic_share_of_automation` | `raw_agentic / (raw_agentic + raw_prior_gen_automation)` |
| `dim_*_per10k` | Per-dimension term density, normalised per 10,000 tokens |
| `automation_depth_*_per10k` | Per-function automation-depth density |
| `stage_*` | Maturity-stage term counts |

## Column reference — `posting_level_detail.csv`

| Column | Meaning |
|---|---|
| `company`, `country`, `region` | Identifiers; region is EU or UK |
| `is_english` | Whether the posting was detected as English |
| `job_title` | Posting title, used for seniority classification |
| `signal_count` | Total agentic signal hits in the posting |
| `distinct_phrases` | Number of distinct dictionary phrases matched |
| `phrases_found` | Matched phrases, **semicolon-delimited** (parse with `str.split(';')`) |
