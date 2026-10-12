import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from explanation_rules import build_reasons


class ExplanationTests(unittest.TestCase):
    def test_only_grounded_reasons(self):
        out = build_reasons(query="BOE-A-2015-10565 y cómputo de plazos", official_reference="BOE-A-2015-10565",
                            extracted_reference="BOE-A-2015-10565", matched_literal="cómputo de plazos",
                            passage="Norma sobre cómputo de plazos", selected_territory="ES",
                            instrument_territory="ES", legal_status="unknown")
        self.assertEqual([x['kind'] for x in out], ['exact_reference','literal_text','territory','unverified_validity'])

    def test_no_invented_match(self):
        out = build_reasons(query="otra cosa", official_reference="BOE-A-2015-10565",
                            extracted_reference="BOE-A-2015-10565", matched_literal="no existe",
                            passage="Texto de ejemplo", selected_territory="ES",
                            instrument_territory="CT", legal_status="vigente")
        self.assertEqual(out, [])


if __name__ == '__main__':
    unittest.main()
