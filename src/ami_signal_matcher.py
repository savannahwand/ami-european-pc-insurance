"""
AMI signal matcher — reference scaffold (v0.2.2)
Loads ami_signal_dictionary.yaml and extracts gated, function-attributed
signals from a document, then computes per-function automation-depth signals
and the four AMI dimension inputs.

This is a STARTING SCAFFOLD, not production code. It uses simple regex phrase
matching + sentence splitting so it runs with no model downloads. For real use,
lemmatize with spaCy first and swap the tokenizer accordingly.

CHANGELOG vs v0.2.1:
- Fixed a bug in gated_agentic_hits(): ambiguous_requires_qualifier terms
  (e.g. "automation", "AI", "automatisierung") that had NO nearby agentic
  qualifier were previously silently dropped -- counted toward neither the
  agentic numerator nor the prior-gen-automation denominator. A report that
  discusses plain automation extensively but never pairs it with a term like
  "generative"/"agentic" would score a spurious 0/0 (undefined -> displayed
  as 0.0) instead of a well-evidenced low agentic_share_of_automation. These
  terms now fall through to the automation (denominator) bucket when no
  qualifier is nearby, instead of being discarded. This affects every
  company in the corpus that uses bare "AI"/"automation"-type language
  without an adjacent agentic-specific qualifier -- not just one report --
  so raw_prior_gen_automation counts across the full dataset were likely
  undercounted before this fix, and should be re-run corpus-wide, not just
  for the report that surfaced the bug.
- automation_not_agentic terms are now also checked against negation_cues,
  matching the same treatment already applied to the agentic and ambiguous
  loops. Previously "no plans to use a rules engine" would still count
  "rules engine" as automation evidence.

CHANGELOG vs v0.2:
- Fixed a bug in gated_agentic_hits(): negation checking was previously called
  with a hardcoded empty cue list and a zero-token window, which silently
  disabled negation detection entirely. A sentence like "we have no plans to
  deploy generative AI" would have scored as a positive agentic hit. Negation
  is now driven by the dictionary's own `negation_cues` and
  `matching_rules.negation_window_tokens`, and is also applied to the
  ambiguous/qualifier-gated term loop, which previously had no negation check
  at all.

KNOWN OPEN ISSUES (not yet fixed, flag for team discussion):
- dimension_1_automation_depth.function_specific phrases (e.g. "algorithmic
  pricing") are counted at full weight without passing through the agentic
  gate, which is inconsistent with the gate's own rule that "algorithmic"
  alone requires a nearby qualifier to count as agentic.
- No distinction between a firm describing AI as an external/industry risk
  ("AI could introduce new liabilities") and a firm claiming its own AI
  deployment. Both currently score identically.
- No lemmatization: "deploy/deploys/deployed/deploying" are four separate
  strings to the matcher.
- qualifier_near/negated use an 8-chars/token heuristic for window sizing.
  This was tuned against English/Romance-language text; German's longer
  average word length (compounding) means a 12-token qualifier window may
  cover less real context than intended for German documents. Not fixed
  here -- flag if German qualifier-matching looks too narrow in practice.

Usage:
    python ami_signal_matcher.py            # runs the built-in demo
    from ami_signal_matcher import score_document
"""

import re
import yaml
from pathlib import Path

DICT_PATH = Path(__file__).with_name("ami_signal_dictionary.yaml")


def load_dictionary(path=DICT_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def split_sentences(text):
    # lightweight sentence splitter; replace with spaCy for real use
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def find_terms(text_lower, terms):
    """Return list of (term, start_char) for each phrase occurrence, longest-first."""
    hits = []
    for term in sorted(terms, key=len, reverse=True):
        # word-ish boundary that tolerates hyphens/spaces inside the phrase
        pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        for m in re.finditer(pattern, text_lower):
            hits.append((term, m.start()))
    return hits


def qualifier_near(text_lower, pos, qualifiers, window_tokens):
    """True if any qualifier appears within +/- window_tokens tokens of pos."""
    window_chars = window_tokens * 8  # ~8 chars/token heuristic
    lo, hi = max(0, pos - window_chars), pos + window_chars
    span = text_lower[lo:hi]
    return any(q in span for q in qualifiers)


def negated(text_lower, pos, neg_cues, window_tokens):
    window_chars = window_tokens * 8
    span = text_lower[max(0, pos - window_chars):pos]
    return any(c in span for c in neg_cues)


def gated_agentic_hits(sentence_lower, gate, rules, negation_cues, negation_window_tokens):
    """Return agentic hits and prior-gen automation hits in one sentence, after gating."""
    agentic, automation = [], []

    for term, pos in find_terms(sentence_lower, gate["agentic"]):
        if not negated(sentence_lower, pos, negation_cues, negation_window_tokens):
            agentic.append(term)

    for term, pos in find_terms(sentence_lower, gate["automation_not_agentic"]):
        if not negated(sentence_lower, pos, negation_cues, negation_window_tokens):
            automation.append(term)

    qwin = rules.get("qualifier_window_tokens", 12)
    for term, pos in find_terms(sentence_lower, gate["ambiguous_requires_qualifier"]):
        if negated(sentence_lower, pos, negation_cues, negation_window_tokens):
            continue  # negated mentions count toward neither bucket
        if qualifier_near(sentence_lower, pos, gate["agentic_qualifiers"], qwin):
            agentic.append(term)
        else:
            # ambiguous term, no nearby agentic qualifier -> plain automation
            # evidence, NOT discarded. This is the v0.2.2 fix: previously
            # these terms were found and then silently dropped, contributing
            # to neither bucket.
            automation.append(term)

    return agentic, automation


def attribute_function(sentence_lower, anchors):
    """Return the set of functions whose anchors appear in this sentence."""
    funcs = set()
    for func, terms in anchors.items():
        if find_terms(sentence_lower, terms):
            funcs.add(func)
    return funcs


def score_document(text, d):
    """Core routine: returns per-function agentic counts + dimension raw counts."""
    rules = d["matching_rules"]
    gate = d["agentic_gate"]
    anchors = d["function_anchors"]
    functions = d["meta"]["functions"]

    # collapse all whitespace (newlines, tabs, runs of spaces) to single spaces —
    # essential for PDF-extracted text, where phrases wrap across lines
    text_lower = re.sub(r"\s+", " ", text.lower())
    n_tokens = max(1, len(text_lower.split()))
    per10k = lambda c: round(c / n_tokens * rules["normalize_per_tokens"], 2)

    func_agentic = {f: 0 for f in functions}
    total_agentic = 0
    total_automation = 0

    negation_cues = d.get("negation_cues", [])
    negation_window_tokens = rules.get("negation_window_tokens", 6)

    # 1. Gated agentic depth, attributed to functions by sentence co-occurrence
    for sent in split_sentences(text_lower):
        ag, au = gated_agentic_hits(sent, gate, rules, negation_cues, negation_window_tokens)
        total_agentic += len(ag)
        total_automation += len(au)
        if ag:
            for f in attribute_function(sent, anchors):
                func_agentic[f] += len(ag)

    # 1b. Pre-attributed function-specific agentic phrases
    for f, terms in d["dimension_1_automation_depth"]["function_specific"].items():
        func_agentic[f] += len(find_terms(text_lower, terms))

    # 2/4. Dimension raw counts (role-evolution, governance, tech-stack)
    def count_group(group):
        return sum(len(find_terms(text_lower, terms)) for terms in group.values())

    dim2 = count_group(d["dimension_2_role_evolution"])
    dim3 = count_group(d["dimension_3_tech_stack"])
    dim4 = count_group(d["dimension_4_governance"])

    # Maturity-stage balance
    stage = {s: len(find_terms(text_lower, t)) for s, t in d["maturity_stage"].items()}

    agentic_share = round(total_agentic / max(1, total_agentic + total_automation), 2)

    return {
        "tokens": n_tokens,
        "agentic_share_of_automation": agentic_share,
        "automation_depth_per_function_per10k": {f: per10k(c) for f, c in func_agentic.items()},
        "dimension_inputs_per10k": {
            "role_evolution": per10k(dim2),
            "tech_stack": per10k(dim3),
            "governance": per10k(dim4),
        },
        "maturity_stage_counts": stage,
        "raw_totals": {"agentic": total_agentic, "prior_gen_automation": total_automation},
    }


# HAR(function) = mean(automation_depth_signal, role_evolution_signal), each min-max scaled 0-1
# across the peer set. Scaling needs all firms, so it's applied AFTER scoring every document.
def minmax(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


if __name__ == "__main__":
    d = load_dictionary()

    demo = """
    Our claims organisation has deployed an AI agent for first notice of loss,
    now handling 40% of motor claims end-to-end without human intervention.
    In underwriting we are piloting a generative AI copilot that assists our
    underwriters. We continue to rely on straight-through processing and a
    rules engine for renewals in policy servicing. We have appointed a Chief AI
    Officer and established an AI governance committee aligned to the EU AI Act.
    Distribution remains driven by our independent agent network. We have no
    plans to automate actuarial reserving.
    """

    result = score_document(demo, d)
    import json
    print(json.dumps(result, indent=2))
