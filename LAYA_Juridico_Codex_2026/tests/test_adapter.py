import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from laya_adapter import Candidate, score_candidates, rrf


class FakeRouter:
    def predict_batch(self, requests, **kwargs):
        assert kwargs["batch_size"] == 8
        assert all(item["model"] == "multilingual" for item in requests)
        return [
            {"answers": {"relevance": {
                "choice": "direct" if i == 0 else "none",
                "probabilities": {"direct": .8 if i == 0 else .1},
                "answer_confidence": .8}}, "usage": {"truncated": False}}
            for i in range(len(requests))
        ]


class AdapterTests(unittest.TestCase):
    def test_calls_real_batch_shape_without_weights(self):
        cs = [Candidate("a", "ejemplo 1", "un texto"), Candidate("b", "ejemplo 2", "otro texto")]
        results = score_candidates("una consulta", cs, FakeRouter())
        self.assertEqual([x["candidate_id"] for x in results], ["a", "b"])
        self.assertEqual([x["class"] for x in results], ["direct", "none"])

    def test_empty(self):
        self.assertEqual(score_candidates("q", [], FakeRouter()), [])

    def test_rrf_union_and_sort(self):
        results = rrf([["a", "b"], ["b", "c"]])
        self.assertEqual(results[0][0], "b")
        self.assertEqual(set(x[0] for x in results), {"a", "b", "c"})

    def test_rrf_dedupe(self):
        self.assertEqual(rrf([["a", "a"]]), [("a", 1/61)])


if __name__ == "__main__":
    unittest.main()
