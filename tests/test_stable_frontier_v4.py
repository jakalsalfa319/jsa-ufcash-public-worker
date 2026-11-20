import importlib.util
import unittest
import copy

has_numpy=importlib.util.find_spec("numpy") is not None


def fixture():
    components={"schema":"JSA_FRONTIER_COMPONENTS_V1",
                "sourceModel":"2025 H2 selected Frontier v2 from 2012-2024 prior-fight data",
                "periods":{}}
    cases={"schema":"JSA_FRONTIER_CASES_V1","model":"nonlinear_ensemble",
           "selection2025":[],"development2026":[]}
    counts={"cal":139,"dev":146,"test":266}
    for period,n in counts.items():
        ids=["id-"+period+"-"+str(i) for i in range(n)]
        dates=[("2025-04-" if period=="cal" else
                 "2025-08-" if period=="dev" else "2026-08-")+f"{1+i%25:02d}" for i in range(n)]
        probs=[.72 if i%3 else .40 for i in range(n)]
        component={"recent_logistic":probs,
             "xgboost":[min(.95,x+.04) for x in probs],
             "catboost":[max(.05,x-.03) for x in probs],
             "hist_boost":[.50+(i%4)*.08 for i in range(n)]}
        y=[int(i%5!=0) for i in range(n)]
        components["periods"][period]={"fightIds":ids,"dates":dates,"outcomeA":y,"raw":component}
        if period!="cal":
            table="selection2025" if period=="dev" else "development2026"
            cases[table]=[{"id":id,"winnerA":z,"probabilities":{"nonlinear_ensemble":p}}
                          for id,z,p in zip(ids,y,probs)]
    return components,cases


@unittest.skipUnless(has_numpy,"NumPy unavailable during dependency-free GitHub check")
class StableFrontierTests(unittest.TestCase):
    def test_fixed_three_models_and_weights(self):
        from scripts.stable_frontier_v4 import WEIGHTS
        self.assertEqual(WEIGHTS,{"recent_logistic":.4,"xgboost":.3,"catboost":.3})
        self.assertEqual(sum(WEIGHTS.values()),1.0)
        self.assertNotIn("hist_boost",WEIGHTS)

    def test_corner_swap_complements_probability(self):
        import numpy as np
        from scripts.stable_frontier_v4 import blend
        data,cases=fixture();p=data["periods"]["dev"]
        origin=blend(p)
        changed=copy.deepcopy(p)
        for k,v in changed["raw"].items():
            changed["raw"][k]=[1-t for t in v]
        mirror=blend(changed)
        np.testing.assert_allclose(origin+mirror,1,atol=1e-12)

    def test_matching_same_fights_is_mandatory(self):
        from scripts.stable_frontier_v4 import valid_source
        raw,cases=fixture()
        self.assertTrue(valid_source(raw,cases))
        cases["development2026"][0]["winnerA"]^=1
        with self.assertRaisesRegex(ValueError,"same-fight"):
            valid_source(raw,cases)

    def test_no_future_data_in_early_2025_calibration(self):
        from scripts.stable_frontier_v4 import valid_source
        raw,cases=fixture()
        raw["periods"]["cal"]["dates"][12]="2025-08-15"
        with self.assertRaisesRegex(ValueError,"Calibration contaminated"):
            valid_source(raw,cases)

    def test_null_probability_is_rejected(self):
        from scripts.stable_frontier_v4 import valid_source
        raw,cases=fixture()
        raw["periods"]["dev"]["raw"]["xgboost"][3]=None
        with self.assertRaises((TypeError,ValueError)):
            valid_source(raw,cases)

    def test_no_2026_labels_used_for_policy(self):
        from scripts.stable_frontier_v4 import audit
        raw,cases=fixture()
        a=audit(raw,cases)
        self.assertFalse(a["noPolicyPromotion"] is False)
        self.assertEqual(a["sameFight2026"]["stableV4"]["eligible"],266)
        for row in cases["development2026"]:
            row["winnerA"]=1-row["winnerA"]
        for i,y in enumerate(raw["periods"]["test"]["outcomeA"]):
            raw["periods"]["test"]["outcomeA"][i]=1-y
        b=audit(raw,cases)
        self.assertEqual(a["validation2025H2"],b["validation2025H2"])
        self.assertEqual(a["reproducibilitySignaturesSha256"],b["reproducibilitySignaturesSha256"])
        self.assertFalse(b["betsPlaced"])

    def test_evaluate_whole_cohort_and_filtered_separately(self):
        from scripts.stable_frontier_v4 import audit
        raw,cases=fixture()
        out=audit(raw,cases)
        self.assertEqual(out["sameFight2026"]["stableV4"]["selected"],266)
        self.assertGreater(out["selective2026AtOriginal65"]["stableV4"]["selected"],0)
        self.assertFalse(out["accuracy99_9Verified"])


if __name__=="__main__":
    unittest.main()
