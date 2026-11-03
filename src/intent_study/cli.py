import argparse
import json
from collections import Counter
from pathlib import Path

from .core import dataset_hash, grouped_split, metrics, read_jsonl, validate, write_jsonl


def main():
    parser = argparse.ArgumentParser(description="Magpie intent research tools; no paid calls")
    parser.add_argument("--labels", default="configs/labels.json")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "split"):
        p = sub.add_parser(name)
        p.add_argument("dataset")
        p.add_argument("--formal", action="store_true")
        if name == "split":
            p.add_argument("output")
            p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("score")
    p.add_argument("dataset")
    p.add_argument("predictions")
    p.add_argument("--split", choices=["train", "validation", "test", "challenge"], required=True)
    args = parser.parse_args()
    labels = [r["id"] for r in json.loads(Path(args.labels).read_text(encoding="utf-8"))["labels"]]
    rows = read_jsonl(args.dataset)
    problems = validate(rows, labels, formal=getattr(args, "formal", False))
    if problems:
        parser.exit(2, "\n".join(problems) + "\n")
    if args.command == "validate":
        print(json.dumps({"n": len(rows), "sha256": dataset_hash(args.dataset),
                          "labels": dict(Counter(r["label"] for r in rows)),
                          "provenance": dict(Counter(r["provenance"] for r in rows))}, ensure_ascii=False, indent=2))
    elif args.command == "split":
        if any("split" in r for r in rows):
            parser.error("input already has split assignments; refusing to reshuffle")
        split_rows = grouped_split(rows, args.seed)
        errors = validate(split_rows, labels, formal=args.formal)
        if errors:
            parser.exit(2, "\n".join(errors))
        write_jsonl(args.output, split_rows)
        print(json.dumps({"seed": args.seed, "counts": dict(Counter(r["split"] for r in split_rows)),
                          "sha256": dataset_hash(args.output)}, indent=2))
    else:
        subset = [r for r in rows if r.get("split") == args.split]
        report = metrics(subset, read_jsonl(args.predictions), labels)
        report["dataset_sha256"] = dataset_hash(args.dataset)
        report["split"] = args.split
        report["by_provenance"] = {}
        for provenance in sorted({r["provenance"] for r in subset}):
            group = [r for r in subset if r["provenance"] == provenance]
            ids = {r["id"] for r in group}
            report["by_provenance"][provenance] = metrics(
                group, [p for p in read_jsonl(args.predictions) if p["id"] in ids], labels)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
