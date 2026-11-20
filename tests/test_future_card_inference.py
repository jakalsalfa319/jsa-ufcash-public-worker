"""Future-event research: no invented fights, no hindsight, no pickle bypass."""
from __future__ import annotations
import copy
import datetime as dt
import importlib.util
import unittest
from unittest.mock import patch

from scripts.future_card_inference import (
    SCHEMA,TRUSTED_SHA,canonical,card_url,valid_card,verified_bouts,forecast
)
from scripts.precision_lab import FEATURES,RATINGS

HAS_PANDAS=importlib.util.find_spec("pandas") is not None
ASOF=dt.datetime(2031,5,8,12,0,tzinfo=dt.timezone.utc)
OFFICIAL="https://www.ufc.com/event/ufc-fight-night-may-20-2031"


def card():
    base={name:2.0 for name in FEATURES}
    ratings={name:.5 for name in RATINGS}
    return {
      "schema":SCHEMA,
      "eventDate":"2031-05-20",
      "startsAtUTC":"2031-05-20T18:00:00Z",
      "featuresCapturedAtUTC":"2031-05-08T09:00:00Z",
      "reviewStatus":"REVIEWED",
      "reviewedAtUTC":"2031-05-08T10:00:00Z",
      "officialEventUrl":OFFICIAL,
      "featureSource":{"date":"2031-05-08T08:00:00Z",
           "description":"Synthetic prior-fight model features solely for regression tests"},
      "bouts":[{"red":"Fighter One","blue":"Fighter Two","status":"UPCOMING",
        "winner":None,"redFeatures":base.copy(),"blueFeatures":base.copy(),
        "ratings":ratings.copy()}],
    }


def sample_html():
    return '<ul><li><p>Fighter One</p><p>Featherweight Bout</p><p>Fighter Two</p></li></ul>'


class FutureCardSourceTests(unittest.TestCase):
    def test_legitimate_future_card_contract(self):
        c=card()
        self.assertEqual(valid_card(c,ASOF,list(FEATURES)+list(RATINGS)),OFFICIAL)
        self.assertTrue(verified_bouts(sample_html(),c["bouts"]))

    def test_reject_mismatched_names_and_page_wide_name_mentions(self):
        c=card()
        with self.assertRaisesRegex(ValueError,"EXACT same-bout"):
            verified_bouts('<li>Fighter One vs Someone Else</li><li>Fighter Two vs Another</li>',c["bouts"])

    def test_reject_historical_event_and_future_result_leakage(self):
        c=card();c["eventDate"]="2026-11-21"
        with self.assertRaisesRegex(ValueError,"Historical"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))
        c=card();c["bouts"][0]["winner"]="Fighter Two"
        with self.assertRaisesRegex(ValueError,"Known outcomes"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))

    def test_reject_untrusted_url_userinfo_and_redirect_host(self):
        for url in ("http://www.ufc.com/event/abc",
                    "https://ufc.com.evil.test/event/abc",
                    "https://evil.test@ufc.com.evil.test/event/abc",
                    "https://ufc.com@evil.test/event/abc",
                    "https://www.ufc.com/news/something"):
            with self.assertRaises(ValueError,msg=url):
                card_url(url)

    def test_reject_wrong_feature_keys_and_nonfinite_numbers(self):
        c=card();c["bouts"][0]["redFeatures"]["outcome"]=1
        with self.assertRaisesRegex(ValueError,"disallowed"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))
        c=card();c["bouts"][0]["blueFeatures"]["n_fights"]=float("nan")
        with self.assertRaisesRegex(ValueError,"Non-finite"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))

    def test_reject_old_or_post_event_feature_snapshot(self):
        c=card();c["featuresCapturedAtUTC"]="2031-02-20T12:00:00Z"
        with self.assertRaisesRegex(ValueError,"older"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))
        c=card();c["featuresCapturedAtUTC"]="2031-05-21T12:00:00Z"
        with self.assertRaisesRegex(ValueError,"Future event"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))

    def test_reject_duplicate_or_reversed_same_fighter_pair(self):
        c=card();d=copy.deepcopy(c["bouts"][0])
        d["red"],d["blue"]=d["blue"],d["red"]
        c["bouts"].append(d)
        with self.assertRaisesRegex(ValueError,"Repeated"):
            valid_card(c,ASOF,list(FEATURES)+list(RATINGS))

    def test_accents_normalize_without_identity_guessing(self):
        self.assertEqual(canonical("Jiří Procházka"),canonical("Jiri Prochazka"))
        self.assertNotEqual(canonical("Fighter One"),canonical("Fighter Two"))

    def test_missing_official_html_cannot_run_model(self):
        fake={"manifest":{"schema":"JSA_FRONTIER_FITTED_CHECKPOINT_V1",
            "originalFeatureNames":list(FEATURES)+list(RATINGS),
            "ensembleWeights":[.4,.2,.2,.2],"gateThreshold":.65}, "models":{}}
        with self.assertRaisesRegex(ValueError,"official event HTML"):
            forecast(card(),fake,TRUSTED_SHA,ASOF,None,None)

    @unittest.skipUnless(HAS_PANDAS,"Pandas/NumPy not installed in lightweight step")
    def test_output_research_only_and_mask_short_history(self):
        import numpy as np
        c=card()
        c["bouts"][0]["redFeatures"]["n_fights"]=2
        fake={"manifest":{"schema":"JSA_FRONTIER_FITTED_CHECKPOINT_V1",
            "originalFeatureNames":list(FEATURES)+list(RATINGS),
            "ensembleWeights":[.4,.2,.2,.2],"gateThreshold":.65,
            "symmetricPlattSlope":1.0},"models":{}}
        with patch("scripts.model_checkpoint.combine",return_value=np.array([.83])):
            output=forecast(c,fake,TRUSTED_SHA,ASOF,sample_html(),"1"*64)
        self.assertFalse(output["predictions"][0]["eligible"])
        self.assertIsNone(output["predictions"][0]["probabilityRed"])
        self.assertFalse(output["predictions"][0]["passesFrozenResearchGate"])
        self.assertFalse(output["featureContentsIndependentlyAudited"])
        self.assertFalse(output["moneyWagered"])
        self.assertFalse(output["fightResultsVerified"])
        self.assertEqual(len(output["snapshotSha256"]),64)


if __name__=="__main__":
    unittest.main()
