"""Offline policy-pack integrity, provenance, reproducibility and retrieval checks."""

import copy
import hashlib
import json
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from voice_agent.data.loader import BusinessPack
from voice_agent.data.preprocess import chunk_knowledge
from voice_agent.inference.retrieval import BM25Index

ROOT = Path(__file__).resolve().parents[1]
BUILD = runpy.run_path(str(ROOT / "scripts/preprocess_policy_packs.py"))
PACKS = BUILD["PACK_ROOT"]


class PolicyPackTests(unittest.TestCase):
    def test_shared_sections_and_answer_annotations(self):
        packs, annotations, sources = BUILD["prepare"](PACKS)
        self.assertEqual((PACKS / "short/knowledge.md").read_bytes(),
                         (ROOT / "milestones/M2_dataset/solar_pilot/knowledge.md").read_bytes())
        short = {c["section_id"]: c["text"] for c in packs["short"]["chunks"]}
        large = {c["section_id"]: c["text"] for c in packs["large"]["chunks"]}
        self.assertEqual(len(short), 15)
        self.assertEqual(len(large), 53)
        self.assertTrue(all(large[i] == text for i, text in short.items()))
        self.assertEqual(sum(q["answerable"] for q in annotations["questions"]), 14)
        self.assertEqual(sum(not q["answerable"] for q in annotations["questions"]), 6)
        self.assertEqual(sources["R1"]["license"], "unknown")
        self.assertEqual(sources["SYNTHETIC"]["human_review"], "pending")

    def test_new_enquiry_exception_is_in_supported_actions_and_q07(self):
        packs, annotations, _ = BUILD["prepare"](PACKS)
        s3 = next(c["text"] for c in packs["short"]["chunks"] if c["section_id"] == "S3")
        self.assertIn("new-enquiry creation", s3)
        self.assertIn("S1", s3)
        self.assertIn("no-match", s3)
        self.assertIn("explicit-confirmation", s3)
        q07 = next(q for q in annotations["questions"] if q["id"] == "Q07")
        self.assertEqual(set(q07["required_section_ids"]), {"S1", "S3"})
        self.assertIn("new enquiry", q07["expected_answer"].lower())
        for variant in ("short", "large"):
            self.assertTrue({"S1", "S3"} <= set(q07["relevant_section_ids_by_pack"][variant]))

    def test_chunk_and_source_ids_survive_retrieval(self):
        packs, _, _ = BUILD["prepare"](PACKS)
        for variant, pack in packs.items():
            by_id = {c["chunk_id"]: c for c in pack["chunks"]}
            for chunk in pack["chunks"]:
                hits = BM25Index(pack["chunks"]).search(chunk["text"], k=len(pack["chunks"]))
                hit = next(h for h in hits if h["chunk_id"] == chunk["chunk_id"])
                self.assertEqual(hit["id"], chunk["section_id"])
                self.assertEqual(hit["document_id"], f"{variant}/knowledge")
                self.assertEqual(hit["sources"], by_id[hit["chunk_id"]]["sources"])
                self.assertTrue(hit["sources"])
                self.assertTrue(all(s["metadata"]["permission_status"] for s in hit["sources"]))
        self.assertTrue(set(c["chunk_id"] for c in packs["short"]["chunks"]).isdisjoint(
            c["chunk_id"] for c in packs["large"]["chunks"]))

    def test_recall_denominators_and_unanswerable_exclusion(self):
        packs, annotations, _ = BUILD["prepare"](PACKS)
        for variant, pack in packs.items():
            report = BUILD["retrieval_report"](pack["chunks"], annotations["questions"], variant)
            self.assertEqual(report["answerable_denominator"], 14)
            self.assertEqual(report["unanswerable_count_excluded_from_recall"], 6)
            self.assertIsNone(report["abstention_accuracy"])
            self.assertIsNone(report["answer_accuracy"])
            for k in report["ks"]:
                scores = []
                for row in report["questions"]:
                    if not row["answerable"]:
                        self.assertIsNone(row["recall_at_k"])
                        continue
                    gold = set(row["relevant_section_ids"])
                    core = set(row["required_section_ids"])
                    hits = {h["section_id"] for h in row["hits"][:k]}
                    expected = len(gold & hits) / len(gold)
                    self.assertEqual(row["recall_at_k"][str(k)], expected)
                    self.assertEqual(row["canonical_core_recall_at_k"][str(k)], len(core & hits)/len(core))
                    self.assertEqual(row["any_relevant_hit_at_k"][str(k)], bool(gold & hits))
                    scores.append(expected)
                self.assertEqual(report["macro_recall_at_k"][str(k)], sum(scores)/14)

    def test_alternative_evidence_is_not_mislabeled_irrelevant(self):
        packs, annotations, _ = BUILD["prepare"](PACKS)
        q = next(q for q in annotations["questions"] if q["id"] == "Q08")
        self.assertIn("S24", q["relevant_section_ids_by_pack"]["large"])
        # A valid alternative can count as relevant without retrieving its canonical core row.
        chunk = next(c for c in packs["large"]["chunks"] if c["section_id"] == "S24")
        report = BUILD["retrieval_report"]([chunk], [q], "large")
        row = report["questions"][0]
        self.assertTrue(row["any_relevant_hit_at_k"]["1"])
        self.assertEqual(row["recall_at_k"]["1"], 0.5)
        self.assertEqual(row["canonical_core_recall_at_k"]["1"], 0)

    def test_dated_exception_sections_remain_text_not_engine_claims(self):
        packs, _, _ = BUILD["prepare"](PACKS)
        sections = {c["section_id"]: c for c in packs["large"]["chunks"]}
        for section_id, boundary in (("S46", "2026-11-15"), ("S47", "2026-11-10"), ("S48", "2026-11-01")):
            section = sections[section_id]
            self.assertEqual(section["kind"], "sandbox_rule")
            self.assertEqual(section["sources"][0]["id"], "SYNTHETIC")
            self.assertIn(boundary, section["text"])
            self.assertIn("Exception", section["text"])
        # This is content/ID validation, not execution or verification of temporal reasoning.

    def test_repeat_builds_are_byte_identical_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp)/"a", Path(temp)/"b"
            BUILD["build"](PACKS, a)
            BUILD["build"](PACKS, b)
            self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()},
                             {p.name: p.read_bytes() for p in b.iterdir()})
            manifest = json.loads((a/"manifest.json").read_text())
            for name, digest in manifest["input_sha256"].items():
                self.assertEqual(hashlib.sha256((PACKS/name).read_bytes()).hexdigest(), digest)
            for name, digest in manifest["output_sha256"].items():
                self.assertEqual(hashlib.sha256((a/name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                BUILD["build"](PACKS, a)

    def test_bad_annotations_and_source_metadata_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"packs"
            shutil.copytree(PACKS, root)
            original = json.loads((root/"questions.json").read_text())
            mutations = []
            bad = copy.deepcopy(original); bad["questions"][0]["required_section_ids"] = ["S999"]
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][0]["required_section_ids"] = []
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][-1]["required_section_ids"] = ["F3"]
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][-1]["missing_information"] = []
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][1]["id"] = bad["questions"][0]["id"]
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][0]["relevant_section_ids_by_pack"]["large"] = ["S999"]
            mutations.append(bad)
            bad = copy.deepcopy(original); bad["questions"][0]["relevant_section_ids_by_pack"]["large"] = []
            mutations.append(bad)
            for bad in mutations:
                (root/"questions.json").write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    BUILD["prepare"](root)
            (root/"questions.json").write_text(json.dumps(original))
            sources = json.loads((root/"sources.json").read_text())
            sources["R1"]["permission_status"] = ""
            (root/"sources.json").write_text(json.dumps(sources))
            with self.assertRaisesRegex(ValueError, "permission"):
                BUILD["prepare"](root)

    def test_duplicate_section_and_invalid_document_ids_rejected(self):
        pack = BusinessPack("solar", "Solar", "| S1 | alpha |\n| S1 | beta |", {"business_id":"solar"})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            chunk_knowledge(pack)
        for document_id in ("", "a#b", 1):
            with self.assertRaisesRegex(ValueError, "document_id"):
                chunk_knowledge(pack, document_id=document_id)


if __name__ == "__main__":
    unittest.main()
