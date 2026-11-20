"""Tests for predeclared v3 specialist residual, 2025-only model gate.

Do not require NumPy during the dependency-free initial GitHub preflight;
tests run fully again after pinned upstream ML requirements are installed.
"""
import importlib.util
import unittest

numpy_available=importlib.util.find_spec("numpy") is not None

def sample(i,year=2025,month=8):
    """Synthetic former fighting statistics, not user data or a real fight."""
    p=.70 if i%3 else .42
    return {
        "id":f"case-{year}-{i}",
        "date":f"{year}-{month:02d}-{1+i%25:02d}",
        "winnerA":int((i%4)!=0),
        "fighters":["Fighter A"+str(i),"Fighter B"+str(i)],
        "fights":[5+i%9,4+i%7],
        "daysSince":[90+i%150,200+i%270],
        "probabilities":{
            "nonlinear_ensemble":p,
            "recent_logistic":min(.95,p+.05),
            "time_decay_logistic":max(.05,p-.04),
            "frozen_v1":max(.05,p-.08),
            "elo_blend":.55,
        },
        "preFightStyle":{
            "strikeDiff":[1+i%5,3+i%2],
            "takedowns15":[2+i%3,1+i%2],
            "takedownDefense":[.7,.5],
            "control":[3+i%4,1+i%3]
        }
    }

def full_cases():
    valid=[sample(i,year=2025,month=8 if i<72 else 11) for i in range(146)]
    development=[sample(i,year=2026,month=(1,4,7,10)[i%4]) for i in range(266)]
    return {"schema":"JSA_FRONTIER_CASES_V1",
            "model":"nonlinear_ensemble",
            "selection2025":valid,
            "development2026":development}


@unittest.skipUnless(numpy_available,"NumPy not installed in initial dependency-free check")
class SpecialistTests(unittest.TestCase):
    def test_specialist_reverses_fighter_corners_exactly(self):
        import copy
        import numpy as np
        from scripts.frontier_specialists import meta_features,logit,sigmoid
        x=sample(8)
        flipped=copy.deepcopy(x)
        flipped["fights"].reverse();flipped["daysSince"].reverse()
        for pair in flipped["preFightStyle"].values():pair.reverse()
        for k,p in flipped["probabilities"].items():flipped["probabilities"][k]=1-p
        np.testing.assert_allclose(meta_features(x),-meta_features(flipped),atol=1e-12)
        w=np.array([.02,-.07,.03,.4,-.1,.07,.05,-.01,.06,.04])
        a=float(sigmoid(logit(x["probabilities"]["nonlinear_ensemble"])+meta_features(x)@w))
        b=float(sigmoid(logit(flipped["probabilities"]["nonlinear_ensemble"])+meta_features(flipped)@w))
        self.assertAlmostEqual(a+b,1,12)

    def test_regularized_fit_remains_finite_and_small(self):
        import numpy as np
        from scripts.frontier_specialists import fit_residual,predict,NAMES
        rows=[sample(i) for i in range(60)]
        weights=fit_residual(rows)
        self.assertEqual(weights.shape,(len(NAMES),))
        self.assertTrue(np.all(np.isfinite(weights)))
        self.assertLess(float(np.linalg.norm(weights)),4)
        p=predict(rows,weights)
        self.assertTrue(np.all((p>0)&(p<1)))

    def test_no_training_with_future_fight(self):
        from scripts.frontier_specialists import check_rows
        rows=[sample(i,year=2026) for i in range(80)]
        with self.assertRaisesRegex(ValueError,"wrong-year"):
            check_rows(rows,2025)

    def test_missing_pre_fight_style_causes_failure(self):
        from scripts.frontier_specialists import check_rows
        x=[sample(i) for i in range(80)]
        del x[4]["preFightStyle"]
        with self.assertRaisesRegex(ValueError,"style evidence"):
            check_rows(x,2025)

    def test_source_cohorts_must_match_versioned_record(self):
        from scripts.frontier_specialists import experiment
        data=full_cases()
        data["selection2025"].pop()
        with self.assertRaisesRegex(ValueError,"cohort sizes"):
            experiment(data)

    def test_2026_labels_never_affect_2025_model_gate(self):
        from scripts.frontier_specialists import experiment
        data=full_cases()
        out=experiment(data)
        for row in data["development2026"]:
            row["winnerA"]=1-row["winnerA"]
        altered=experiment(data)
        self.assertEqual(out["validationPassed"],altered["validationPassed"])
        self.assertEqual(out["candidateWeights"],altered["candidateWeights"])
        self.assertFalse(out["selectedModelForLiveBetting"])
        self.assertEqual(out["2026Challenger"]["eligible"],266)

    def test_specialist_keeps_unchanged_if_gate_fails(self):
        from scripts.frontier_specialists import experiment
        data=full_cases()
        result=experiment(data)
        if not result["validationPassed"]:
            self.assertEqual(result["2026Challenger"]["correct"],
                             result["2026Baseline"]["correct"])
        self.assertFalse(result["accuracy99_9Proven"])
        self.assertEqual(result["quarterly"]["Q4"]["n"],66)


if __name__=="__main__":
    unittest.main()
