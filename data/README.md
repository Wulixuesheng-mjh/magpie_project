# Data preparation

`public/pilot-index.jsonl` records the first 60 public issue candidates, their
source URLs and initial triage flags. It deliberately contains no issue bodies,
user profiles, annotations or credentials. It is an index, not a formal dataset.

`public/collection-manifest.json` preserves collection endpoints, response hashes,
counts and the upstream collection timestamp for audit purposes. The response
snapshots referenced in it are local-only and are not part of the repository.

The original candidate bodies, API snapshots and annotation worksheets remain in
`private/public-issues-pilot/`, which Git ignores. Initial screening excluded 8
candidates; 52 still require review. Usage checks and formal annotation have not
been completed, so the formal evaluation sample count is zero.

To collect a new local candidate pool:

```powershell
python scripts/collect_public_issues.py --output data/private/new-public-pilot
```

The script accesses GitHub over the network and does not overwrite existing
outputs. A fresh collection may return different issues; it is not a replacement
for the original response snapshots. Review provenance and usage conditions
before adding any text to a formal dataset. See `docs/annotation-guide.md`.
