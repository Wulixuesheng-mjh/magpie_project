"""Collect public issue candidates without credentials; never marks them usable/formal."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

REPOSITORIES = [("yetone/magpie", 20), ("pytest-dev/pytest", 10),
                ("fastapi/fastapi", 10), ("psf/requests", 10), ("pallets/flask", 10)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/private/public-issues-pilot")
    parser.add_argument("--version", default="", help="new artifact suffix; existing outputs are never overwritten")
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    rows, manifest = [], []
    for repository, count in REPOSITORIES:
        endpoint = f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100&sort=created&direction=desc"
        request = urllib.request.Request(endpoint, headers={"Accept": "application/vnd.github+json", "User-Agent": "magpie-intent-research/0.1"})
        snapshot = root / (repository.replace("/", "__") + ".json")
        if snapshot.exists():
            data = snapshot.read_bytes()
        else:
            data = urllib.request.urlopen(request, timeout=30).read()
            if not isinstance(json.loads(data), list):
                raise ValueError(f"{repository}: API response is not an issue list")
            with snapshot.open("xb") as stream:
                stream.write(data)
        def eligible(i):
            return "pull_request" not in i and isinstance(i.get("body"), str) and i["body"].strip() and not i.get("user", {}).get("login", "").endswith("[bot]")
        issues = [i for i in json.loads(data) if eligible(i)][:count]
        evidence = dict(repository=repository, endpoint=endpoint, snapshot=snapshot.name,
                        sha256=hashlib.sha256(data).hexdigest())
        if len(issues) < count:
            # Some repositories have almost exclusively PRs in the issues endpoint.
            search_url = f"https://api.github.com/search/issues?q=repo:{repository}+is:issue&per_page=100&sort=created&order=desc"
            search_path = root / (repository.replace("/", "__") + "__issues_search.json")
            if search_path.exists():
                search_data = search_path.read_bytes()
            else:
                search_request = urllib.request.Request(search_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "magpie-intent-research/0.1"})
                search_data = urllib.request.urlopen(search_request, timeout=30).read()
                json.loads(search_data)["items"]
                with search_path.open("xb") as stream:
                    stream.write(search_data)
            known = {i["id"] for i in issues}
            issues.extend(i for i in json.loads(search_data)["items"] if eligible(i) and i["id"] not in known)
            issues = issues[:count]
            evidence["supplement"] = dict(endpoint=search_url, snapshot=search_path.name,
                                           sha256=hashlib.sha256(search_data).hexdigest())
        evidence["n"] = len(issues)
        manifest.append(evidence)
        for issue in issues:
            rows.append(dict(id=f"github:{repository}:{issue['number']}",
                             text=issue["title"] + "\n\n" + issue["body"],
                             conversation_id=issue["html_url"], source_group=issue["html_url"],
                             source_ref=issue["html_url"], provenance="public_proxy", language="unreviewed",
                             label=None, context=[], consent_or_license_checked=False,
                             annotation_status="pending", annotator=None, reviewer=None, rationale="",
                             repository=repository, source_created_at=issue["created_at"],
                             source_updated_at=issue["updated_at"], title=issue["title"]))
        print(f"{repository}: {len(issues)} candidates", flush=True)
    suffix = "-" + args.version if args.version else ""
    with (root / f"candidates{suffix}.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["id", "title", "source_ref", "label", "language", "annotation_status", "consent_or_license_checked", "rationale"]
    with (root / f"annotation-worksheet{suffix}.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (root / f"collection-manifest{suffix}.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                       status="unreviewed_candidates_not_formal_data", n=len(rows), sources=manifest), stream, indent=2)
    print(f"Total {len(rows)}; all labels and usage checks remain pending.")


if __name__ == "__main__":
    main()
