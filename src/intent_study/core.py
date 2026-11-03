from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

PROVENANCE = {"real_assistant", "public_proxy", "synthetic_debug"}


def read_jsonl(path):
    rows = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{n}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{n}: expected JSON object")
            rows.append(row)
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalized(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()


def input_fingerprint(row):
    # "Continue" with different prior turns is a different classification input.
    context = row.get("context", [])
    if not isinstance(context, list):
        context = []
    return json.dumps([normalized(row["text"]), [
        [m.get("role"), normalized(m.get("content", ""))]
        for m in context if isinstance(m, dict) and isinstance(m.get("content", ""), str)
    ]], ensure_ascii=False)


def validate(rows, labels, *, formal=False):
    errors, ids, texts, groups = [], set(), {}, {}
    for n, row in enumerate(rows, 1):
        prefix = f"row {n}"
        for field in ("id", "text", "conversation_id", "source_group", "source_ref", "language", "label"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{prefix}: missing/non-string {field}")
        sid = row.get("id")
        if isinstance(sid, str):
            if sid in ids:
                errors.append(f"{prefix}: duplicate id {sid}")
            ids.add(sid)
        if row.get("label") not in labels:
            errors.append(f"{prefix}: unknown label")
        if row.get("provenance") not in PROVENANCE:
            errors.append(f"{prefix}: invalid provenance")
        if formal and row.get("provenance") == "synthetic_debug":
            errors.append(f"{prefix}: synthetic samples forbidden in formal data")
        if formal and row.get("consent_or_license_checked") is not True:
            errors.append(f"{prefix}: data-use permission not checked")
        if formal and row.get("annotation_status") != "adjudicated":
            errors.append(f"{prefix}: annotation not adjudicated")
        split = row.get("split")
        if split is not None and split not in {"train", "validation", "test", "challenge"}:
            errors.append(f"{prefix}: invalid split")
        if isinstance(row.get("text"), str):
            key = input_fingerprint(row)
            if key in texts:
                errors.append(f"{prefix}: normalized duplicate of row {texts[key]}")
            texts[key] = n
        for field in ("conversation_id", "source_group", "duplicate_group"):
            value = row.get(field)
            if isinstance(value, str) and value:
                group = (field, value)
                if split and group in groups and groups[group] != split:
                    errors.append(f"{prefix}: {field} crosses splits")
                if split:
                    groups[group] = split
        prior = row.get("context", [])
        if not isinstance(prior, list) or any(
            not isinstance(m, dict) or m.get("role") not in {"user", "assistant"}
            or not isinstance(m.get("content"), str) for m in prior
        ):
            errors.append(f"{prefix}: invalid context (only user/assistant text allowed)")
    if not rows:
        errors.append("empty dataset")
    return errors


def grouped_split(rows, seed=42):
    """Keep transitive conversation/source/near-duplicate groups together."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        keys = [(f, row.get(f)) for f in ("conversation_id", "source_group", "duplicate_group") if row.get(f)]
        keys.append(("input", input_fingerprint(row)))
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            seen[key] = i
    blocks = defaultdict(list)
    for i, row in enumerate(rows):
        blocks[find(i)].append(row)
    blocks = list(blocks.values())
    random.Random(seed).shuffle(blocks)
    blocks.sort(key=len, reverse=True)
    names, ratios = ["train", "validation", "test"], [0.6, 0.2, 0.2]
    total = Counter(r["label"] for r in rows)
    counts = {s: Counter() for s in names}
    assignments = {}
    for block in blocks:
        bc = Counter(r["label"] for r in block)

        def cost(candidate):
            return sum(
                ((counts[s][label] + (bc[label] if s == candidate else 0)
                  - total[label] * ratio) ** 2) / max(total[label] * ratio, 1)
                for s, ratio in zip(names, ratios) for label in total
            )

        choice = min(names, key=cost)
        counts[choice].update(bc)
        for row in block:
            assignments[row["id"]] = choice
    return [{**r, "split": assignments[r["id"]]} for r in rows]


def dataset_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(samples, predictions, labels):
    expected = {r["id"]: r for r in samples}
    predicted = {}
    for row in predictions:
        if row["id"] in predicted:
            raise ValueError(f"duplicate prediction: {row['id']}")
        if row["id"] not in expected:
            raise ValueError(f"unknown prediction: {row['id']}")
        if row.get("label") is not None and row["label"] not in labels:
            raise ValueError("unknown predicted label")
        if row.get("label") is not None and (row.get("error") or row.get("abstained")):
            raise ValueError("prediction cannot be accepted and failed/abstained")
        if row.get("label") is None and not row.get("error") and not row.get("abstained"):
            raise ValueError("unanswered prediction must state error or abstained")
        predicted[row["id"]] = row
    if not expected:
        raise ValueError("empty evaluation set")
    matrix, accepted, correct = Counter(), 0, 0
    errors = Counter()
    for sid, sample in expected.items():
        p = predicted.get(sid, {})
        label = p.get("label") if not p.get("error") and not p.get("abstained") else None
        if label is not None:
            accepted += 1
        if label == sample["label"]:
            correct += 1
        matrix[(sample["label"], label or "__unanswered__")] += 1
        if not p:
            errors["missing_prediction"] += 1
        elif p.get("error"):
            errors[p["error"]] += 1
        elif p.get("abstained"):
            errors["abstained"] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label, label]
        support = sum(v for (a, _), v in matrix.items() if a == label)
        predicted_n = sum(v for (_, b), v in matrix.items() if b == label)
        precision, recall = tp / predicted_n if predicted_n else 0, tp / support if support else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_class[label] = dict(precision=precision, recall=recall, f1=f1, support=support)
    times = sorted(p["elapsed_ms"] for p in predicted.values() if isinstance(p.get("elapsed_ms"), (int, float)))
    def percentile(q):
        if not times:
            return None
        at = (len(times) - 1) * q
        lo, hi = int(at), min(int(at) + 1, len(times) - 1)
        return times[lo] + (times[hi] - times[lo]) * (at - lo)
    return dict(n=len(expected), accuracy=correct / len(expected),
                macro_f1=sum(v["f1"] for v in per_class.values()) / len(labels),
                coverage=accepted / len(expected), accepted_accuracy=correct / accepted if accepted else None,
                per_class=per_class, errors=dict(errors), p50_ms=percentile(.5), p95_ms=percentile(.95),
                confusion=[{"gold": a, "predicted": b, "count": n} for (a, b), n in sorted(matrix.items())])
