import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CLITests(unittest.TestCase):
    def test_validate_split_score_and_no_overwrite(self):
        project = Path(__file__).resolve().parents[1]
        env = {**os.environ, "PYTHONPATH": str(project / "src")}
        def run(*args):
            return subprocess.run([sys.executable, "-m", "intent_study.cli", *map(str, args)],
                                  cwd=project, env=env, capture_output=True, text=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, split, predictions = root / "input.jsonl", root / "split.jsonl", root / "predictions.jsonl"
            labels = [r["id"] for r in json.loads((project / "configs/labels.json").read_text(encoding="utf-8"))["labels"]]
            rows = [dict(id=str(i), text=f"工程测试占位 {i}", label=labels[i % 6], conversation_id=str(i),
                         source_group=str(i), source_ref="synthetic-test", language="zh", provenance="synthetic_debug")
                    for i in range(60)]
            dataset.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            self.assertEqual(run("validate", dataset).returncode, 0)
            self.assertNotEqual(run("validate", dataset, "--formal").returncode, 0)
            self.assertEqual(run("split", dataset, split).returncode, 0)
            self.assertNotEqual(run("split", dataset, split).returncode, 0)
            chosen = [r for r in map(json.loads, split.read_text(encoding="utf-8").splitlines()) if r["split"] == "validation"]
            predictions.write_text("\n".join(json.dumps(dict(id=r["id"], label=r["label"])) for r in chosen), encoding="utf-8")
            result = run("score", split, predictions, "--split", "validation")
            self.assertEqual(result.returncode, 0, result.stderr)
            # Artificial perfect predictions only check arithmetic and CLI plumbing.
            self.assertEqual(json.loads(result.stdout)["accuracy"], 1)
