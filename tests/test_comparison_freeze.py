"""Offline preregistration integrity checks, not permission to run comparisons."""
import copy
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT/"scripts/check_comparison_freeze.py"))


class ComparisonFreezeTests(unittest.TestCase):
    def setUp(self):
        self.settings = MODULE["plan"]()

    def test_matrix_is_three_repeats_and_not_authorized(self):
        result=MODULE["check"](self.settings)
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(sum(c["planned_attempts"] for c in self.settings["core_cells"]),240)
        self.assertEqual(self.settings["targeted_validation"]["planned_attempts"],24)
        self.assertEqual({tuple(c["repetitions"]) for c in self.settings["core_cells"]},{(1,2,3)})
        self.assertFalse(self.settings["heldout"]["evaluation_allowed"])
        self.assertFalse(self.settings["voice"]["execution_allowed"])

    def test_hash_drift_is_rejected(self):
        key=next(iter(self.settings["input_sha256"]))
        self.settings["input_sha256"][key]="0"*64
        with self.assertRaisesRegex(ValueError,"drift"):MODULE["check"](self.settings)

    def test_membership_drift_before_new_file_read(self):
        self.settings["input_sha256"]["src/voice_agent/not_registered.py"]="0"*64
        with patch.dict(MODULE["inputs"].__globals__,{"sha":lambda path: self.fail("Read file before membership check")}):
            with self.assertRaisesRegex(ValueError,"membership drift"):MODULE["check"](self.settings)

    def test_runtime_and_authorization_drift(self):
        changed=copy.deepcopy(self.settings)
        changed["runtime"]["python"]="different"
        with self.assertRaisesRegex(ValueError,"Runtime differs"):MODULE["check"](changed)
        changed=copy.deepcopy(self.settings);changed["execution_allowed"]=True
        with self.assertRaisesRegex(ValueError,"blocked plan"):MODULE["check"](changed)

    def test_registered_values_and_nested_authorization(self):
        for section,key,value in [("voice","execution_allowed",True),
                                  ("heldout","evaluation_allowed",True),
                                  ("targeted_validation","planned_attempts",0),
                                  ("roles","temperature",1.0)]:
            changed=copy.deepcopy(self.settings);changed[section][key]=value
            with self.subTest(section=section):
                with self.assertRaisesRegex(ValueError,"Registered settings differ"):MODULE["check"](changed)
        changed=copy.deepcopy(self.settings);changed["core_cells"][0]["model"]="substitute"
        with self.assertRaisesRegex(ValueError,"Registered settings differ"):MODULE["check"](changed)
        changed=copy.deepcopy(self.settings);changed["core_cells"][0]["scenario_ids"][0]="SUBSTITUTE"
        with self.assertRaisesRegex(ValueError,"Registered settings differ"):MODULE["check"](changed)

    def test_invalid_matrix_slot_is_rejected(self):
        self.settings["core_cells"][0]["repetitions"]=[1,2]
        with self.assertRaisesRegex(ValueError,"slots"):MODULE["check"](self.settings)
