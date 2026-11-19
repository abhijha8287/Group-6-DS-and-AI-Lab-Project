"""Arithmetic checks only: these are not model results or held-out scenarios."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from voice_agent.evaluation.measurement import (count_rate, exact_mcnemar, nearest_rank,
    normalize_transcript, repetition_summary, strict_completion, word_error_rate)


class MeasurementTests(unittest.TestCase):
    def test_normalization_keeps_negation_numbers_and_unicode_marks(self):
        self.assertEqual(normalize_transcript("  DON'T call—１２; नहीं! " ), ["don","t","call","12","नहीं"])
        self.assertNotEqual(normalize_transcript("twenty"), normalize_transcript("20"))
        self.assertEqual(normalize_transcript("A_B test-case"), ["a","b","test","case"])

    def test_wer_and_empty_reference(self):
        self.assertEqual(word_error_rate("a b c", "a x c d"),
            dict(reference_words=3,hypothesis_words=4,substitutions=1,deletions=0,insertions=1,errors=2,wer=2/3))
        self.assertEqual(word_error_rate("a b", "a")["deletions"], 1)
        self.assertIsNone(word_error_rate("", "extra")["wer"])
        self.assertEqual(word_error_rate("", "extra")["insertions"], 1)
        self.assertEqual(word_error_rate("a", "a b c")["wer"], 2)

    def test_strict_null_propagation_and_invalid_eligibility(self):
        self.assertIsNone(strict_completion(False, None, True, eligible=True))
        self.assertIsNone(strict_completion(True, True, True, eligible=False))
        self.assertFalse(strict_completion(True,True,False,eligible=True))
        self.assertTrue(strict_completion(True,True,True,eligible=True))
        with self.assertRaises(ValueError):strict_completion(1,True,True,eligible=True)

    def test_valid_scores_are_not_attempt_yield(self):
        self.assertEqual(count_rate([True,False,None]), dict(planned=3,valid=2,unknown=1,
            successes=1,failures=1,valid_rate=.5,confirmed_success_lower_bound=1/3,possible_success_upper_bound=2/3))
        self.assertIsNone(count_rate([])["valid_rate"])
        with self.assertRaises(ValueError):count_rate(["false"])

    def test_all_three_is_not_any_success(self):
        records=[dict(scenario_id="EXAMPLE",repetition=r,strict_success=v) for r,v in enumerate([True,False,True],1)]
        result=repetition_summary(records,["EXAMPLE"])
        self.assertEqual(result["all_three"]["valid_rate"],0)
        self.assertEqual(result["pass_at_3_complete_triplets"]["valid_rate"],1)
        self.assertEqual(result["scenario_count"],1)

    def test_missing_invalid_and_duplicate_slots(self):
        records=[dict(scenario_id="EXAMPLE",repetition=1,strict_success=True)]
        result=repetition_summary(records,["EXAMPLE"])
        self.assertEqual(result["not_recorded_attempts"],2)
        self.assertIsNone(result["all_three"]["valid_rate"])
        self.assertTrue(result["rows"][0]["any_success_observed"])
        with self.assertRaises(ValueError):repetition_summary(records+records,["EXAMPLE"])
        with self.assertRaises(ValueError):repetition_summary([dict(scenario_id="EXAMPLE",repetition=True,strict_success=True)],["EXAMPLE"])

    def test_nearest_rank_and_invalid_observations(self):
        self.assertEqual(nearest_rank(range(1,21),.95),19)
        self.assertEqual(nearest_rank([3,1,2],.5),2)
        self.assertIsNone(nearest_rank([],.95))
        with self.assertRaises(ValueError):nearest_rank([float("nan")],.5)

    def test_exact_paired_test(self):
        result=exact_mcnemar([(False,True)]*6+[(True,True)]*4)
        self.assertEqual(result["p_two_sided"],.03125)
        self.assertEqual(result["difference"],.6)
        self.assertEqual(exact_mcnemar([(True,True)])["p_two_sided"],1)
        self.assertIsNone(exact_mcnemar([])["p_two_sided"])
        with self.assertRaises(ValueError):exact_mcnemar([(1,True)])
