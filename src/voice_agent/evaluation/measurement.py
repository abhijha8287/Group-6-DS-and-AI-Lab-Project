"""Offline reference arithmetic, not an automatic semantic judge. Protocol: m4-metrics-v1."""

import math
import unicodedata


def normalize_transcript(text):
    if not isinstance(text, str):
        raise ValueError("Transcript must be text")
    words, word = [], []
    for char in unicodedata.normalize("NFKC", text).casefold():
        if char.isalnum() or unicodedata.category(char).startswith("M"):
            word.append(char)
        elif word:
            words.append("".join(word))
            word = []
    if word:
        words.append("".join(word))
    return words


def word_error_rate(reference, hypothesis):
    ref, hyp = normalize_transcript(reference), normalize_transcript(hypothesis)
    # Tuple: distance, substitutions, deletions, insertions. Ties prefer diagonal, deletion, insertion.
    previous = [(i, 0, 0, i) for i in range(len(hyp)+1)]
    for r, token in enumerate(ref, 1):
        current = [(r, 0, r, 0)]
        for h, other in enumerate(hyp, 1):
            diagonal = previous[h-1]
            if token != other:
                diagonal = (diagonal[0]+1, diagonal[1]+1, diagonal[2], diagonal[3])
            deletion = previous[h]
            insertion = current[h-1]
            candidates = [diagonal, (deletion[0]+1,deletion[1],deletion[2]+1,deletion[3]),
                          (insertion[0]+1,insertion[1],insertion[2],insertion[3]+1)]
            current.append(min(candidates, key=lambda value: value[0]))
        previous = current
    errors, substitutions, deletions, insertions = previous[-1]
    return {"reference_words":len(ref), "hypothesis_words":len(hyp), "substitutions":substitutions,
            "deletions":deletions, "insertions":insertions, "errors":errors,
            "wer": errors/len(ref) if ref else None}


def strict_completion(db_pass, communicate_pass, safety_pass, *, eligible):
    values = (db_pass, communicate_pass, safety_pass)
    if type(eligible) is not bool or any(v is not None and type(v) is not bool for v in values):
        raise ValueError("Eligibility and component scores must be real booleans (or null components)")
    return all(values) if eligible and all(v is not None for v in values) else None


def count_rate(values):
    values = list(values)
    if any(v is not None and type(v) is not bool for v in values):
        raise ValueError("Scores must be boolean or null")
    successes = sum(v is True for v in values)
    failures = sum(v is False for v in values)
    unknown = sum(v is None for v in values)
    valid, planned = successes+failures, len(values)
    return {"planned":planned, "valid":valid, "unknown":unknown, "successes":successes,
            "failures":failures, "valid_rate":successes/valid if valid else None,
            "confirmed_success_lower_bound":successes/planned if planned else None,
            "possible_success_upper_bound":(successes+unknown)/planned if planned else None}


def repetition_summary(records, scenario_ids):
    ids = list(scenario_ids)
    if len(ids) != len(set(ids)):
        raise ValueError("Scenario IDs must be unique")
    slots = {s: {} for s in ids}
    for record in records:
        scenario, repetition, success = record["scenario_id"], record["repetition"], record["strict_success"]
        if (scenario not in slots or type(repetition) is not int or repetition not in (1,2,3)
                or repetition in slots[scenario] or (success is not None and type(success) is not bool)):
            raise ValueError("Unknown scenario, duplicate slot, invalid repetition or score")
        slots[scenario][repetition] = success
    rows = []
    for scenario in ids:
        values = [slots[scenario].get(i) for i in (1,2,3)]
        complete = all(v is not None for v in values)
        rows.append({"scenario_id":scenario, "slots":values, "recorded_attempts":len(slots[scenario]),
                     "all_three_success":all(values) if complete else None,
                     "pass_at_3_complete_triplet":any(values) if complete else None,
                     "any_success_observed":any(v is True for v in values)})
    return {"planned_attempts":3*len(ids), "recorded_attempts":sum(len(s) for s in slots.values()),
            "not_recorded_attempts":3*len(ids)-sum(len(s) for s in slots.values()),
            "scenario_count":len(ids), "all_three":count_rate(r["all_three_success"] for r in rows),
            "pass_at_3_complete_triplets":count_rate(r["pass_at_3_complete_triplet"] for r in rows),
            "rows":rows}


def nearest_rank(values, quantile):
    values = list(values)
    if (type(quantile) not in (int,float) or not math.isfinite(quantile) or not 0 < quantile <= 1
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
        raise ValueError("Finite numeric observations and a quantile in (0,1] required")
    return sorted(values)[math.ceil(quantile*len(values))-1] if values else None


def exact_mcnemar(pairs):
    pairs = list(pairs)
    if any(len(pair)!=2 or any(type(v) is not bool for v in pair) for pair in pairs):
        raise ValueError("Scorable paired booleans required")
    b = sum(a and not t for a,t in pairs)
    c = sum(t and not a for a,t in pairs)
    n = b+c
    p = min(1.0, 2*sum(math.comb(n,i) for i in range(min(b,c)+1))/2**n) if n else 1.0
    return {"pairs":len(pairs), "baseline_only":b, "treatment_only":c,
            "p_two_sided":p if pairs else None,
            "difference":(c-b)/len(pairs) if pairs else None}
