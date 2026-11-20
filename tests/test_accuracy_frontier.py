"""Accuracy Frontier deterministic guardrails, including 2025-only model selection."""
import importlib.util
import math
import unittest

from scripts.accuracy_frontier import (
    CANDIDATES, CONFIDENCE_GRID, INTERACTIONS,
    choose_family, choose_gate,
)


class FrontierGuards(unittest.TestCase):
    def test_all_families_are_predeclared(self):
        self.assertEqual(CANDIDATES,(
            "frozen_v1","recent_logistic","time_decay_logistic",
            "nonlinear_ensemble","elo_blend"))
        self.assertIn(.75,CONFIDENCE_GRID)
        self.assertEqual(len(INTERACTIONS),6)

    def test_family_chosen_on_supplied_validation_truth_only(self):
        true=[1]*55+[0]*45
        probs={
            "frozen_v1":[.88]*55+[.12]*45,
            "recent_logistic":[.73]*55+[.27]*45,
            "time_decay_logistic":[.71]*55+[.29]*45,
            "nonlinear_ensemble":[.72]*55+[.28]*45,
            "elo_blend":[.69]*55+[.31]*45,
        }
        chosen,stats=choose_family(probs,true)
        self.assertEqual(chosen,"frozen_v1")
        self.assertEqual(len(stats),len(CANDIDATES))

    def test_inconsistent_family_contract_rejected(self):
        with self.assertRaisesRegex(ValueError,"contract"):
            choose_family({"recent_logistic":[.8]*50},[1]*50)

    def test_predefined_threshold_requires_useful_coverage(self):
        prob=[.9]*45+[.51]*55
        outcome=[1]*40+[0]*5+[1]*28+[0]*27
        t,score=choose_gate(prob,outcome)
        self.assertIn(t,CONFIDENCE_GRID)
        self.assertGreaterEqual(score["selected"],35)
        self.assertGreaterEqual(score["coverage"],.2)

    def test_insufficient_gate_data_rejected(self):
        with self.assertRaisesRegex(ValueError,"No threshold"):
            choose_gate([.98]*10,[1]*10)

    @unittest.skipUnless(importlib.util.find_spec("numpy"),"NumPy not yet installed")
    def test_matchup_interactions_preserve_corner_symmetry(self):
        import numpy as np
        from scripts.accuracy_frontier import interactions
        names=["c_sdiff","c_td15","c_ctrl","win_rate","p_elo32",
            "c_tddef","e_adj_net","p_glicko","fights_2y","days_since"]
        x=np.array([[.2,.4,-.1,.03,.7,.4,-.2,.08,1,12],
                    [-.12,.2,.03,-.07,-.3,.1,.4,-.11,0,15]])
        aa=interactions(x,names)
        bb=interactions(-x,names)
        np.testing.assert_allclose(aa,-bb,atol=1e-12)

    @unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("pandas"),"Pandas/NumPy unavailable")
    def test_time_decay_weight_has_no_future_training(self):
        import pandas as pd
        from scripts.accuracy_frontier import time_decay
        dates=pd.Series(pd.to_datetime(["2019-01-01","2024-12-31"]))
        w=time_decay(dates,"2025-01-01")
        self.assertLess(w[0],w[1])
        self.assertLessEqual(w[1],1)
        with self.assertRaisesRegex(ValueError,"future dates"):
            time_decay(pd.Series(pd.to_datetime(["2025-02-01"])),"2025-01-01")


if __name__=="__main__":
    unittest.main()
