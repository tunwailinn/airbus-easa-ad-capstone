import unittest

from full_corpus_pipeline.e5_query_router import (
    classify_intent,
    extract_ad_numbers,
    extract_publication_ids,
    route_query,
)


class E5QueryRouterTests(unittest.TestCase):
    def test_extracts_exact_ad_and_revision(self):
        self.assertEqual(
            extract_ad_numbers("What does EASA AD 2012-0175R2 require?"),
            ("2012-0175R2",),
        )

    def test_known_document_mode(self):
        route = route_query("When must the inspection in AD 2006-0047 be done?")
        self.assertEqual(route.mode, "known_document")
        self.assertEqual(route.ad_numbers, ("2006-0047",))
        self.assertEqual(route.intent, "required_action_compliance")
        self.assertIn("Compliance", route.preferred_sections)

    def test_multi_document_mode(self):
        route = route_query("Compare AD 2006-0047 with EASA AD 2006-0077.")
        self.assertEqual(route.mode, "multi_document")
        self.assertEqual(route.ad_numbers, ("2006-0047", "2006-0077"))

    def test_discovery_mode_without_identifier(self):
        route = route_query("Which AD requires this inspection within 500 flight cycles?")
        self.assertEqual(route.mode, "discovery")
        self.assertEqual(route.ad_numbers, ())
        self.assertEqual(route.intent, "required_action_compliance")

    def test_conditional_intent_precedes_generic_compliance(self):
        self.assertEqual(
            classify_intent(
                "Under AD 2020-0001, what action is required if the crack is found, "
                "and what applies unless the repair was previously accomplished?"
            ),
            "conditional_multi_passage",
        )

    def test_reference_publication_intent_and_sb_identifier(self):
        question = "Which Service Bulletin A320-53-1234 is referenced by the AD?"
        route = route_query(question)
        self.assertEqual(route.intent, "referenced_publication")
        self.assertEqual(route.publication_ids, ("A320-53-1234",))

    def test_applicability_intent(self):
        route = route_query("Which aircraft models are affected by EASA AD 2010-0271?")
        self.assertEqual(route.intent, "applicability")
        self.assertIn("Applicability", route.preferred_sections)

    def test_identity_intent(self):
        route = route_query("What is the effective date of AD 2008-0066?")
        self.assertEqual(route.intent, "identity_lifecycle")


if __name__ == "__main__":
    unittest.main()
