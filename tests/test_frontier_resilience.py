import copy
import unittest
from scripts.frontier_resilience import (
    RULES, passes, score, select_rule, flags, diagnostic, validate, run, quarter
)


def fight(i, date, *, prob=.7, winner=1, experience=8,
          days=150, other=.72, old=.63):
    return {
        "id":f"fight-{date}-{i}","date":date,
        "fighters":[f"Red {i}",f"Blue {i}"],
        "winnerA":winner,
        "fights":[experience,experience],
        "daysSince":[days,days],
        "probabilities":{
            "nonlinear_ensemble":prob,
            "recent_logistic":other,
            "time_decay_logistic":other,
            "frozen_v1":old,
            "elo_blend":.6,
        },"elo32":.6,
    }


class FrontierResilienceTests(unittest.TestCase):
    def test_fixed_policy_catalog(self):
        self.assertEqual(len(RULES),5)
        self.assertEqual(RULES[0]["id"],"baseline_65")
        self.assertEqual(RULES[0]["confidence"],.65)

    def test_experienced_consensus_passes(self):
        x=fight(1,"2025-08-02")
        self.assertTrue(passes(x,RULES[0]))
        self.assertTrue(passes(x,RULES[2]))
        self.assertTrue(passes(x,RULES[3]))

    def test_low_experience_and_layoff_fail_risk_filters(self):
        x=fight(1,"2025-08-02",experience=3,days=900)
        self.assertFalse(passes(x,RULES[1]))
        self.assertFalse(passes(x,RULES[3]))
        self.assertFalse(passes(x,RULES[4]))
        self.assertTrue(flags(x)["limited_history"])
        self.assertTrue(flags(x)["long_layoff"])

    def test_disagreement_veto(self):
        x=fight(1,"2025-08-02",prob=.8,other=.43)
        self.assertFalse(passes(x,RULES[2]))
        self.assertFalse(passes(x,RULES[3]))
        self.assertTrue(flags(x)["large_model_spread"])
        self.assertTrue(flags(x)["different_favorite_than_old"] is False)

    def test_wrong_prediction_not_counted_correct(self):
        a=fight(1,"2025-08-02",prob=.7,winner=0)
        b=fight(2,"2025-08-02",prob=.8,winner=1)
        s=score([a,b],RULES[0])
        self.assertEqual(s["selected"],2)
        self.assertEqual(s["correct"],1)
        self.assertEqual(s["accuracy"],.5)

    def test_no_accepted_fights_not_100pct(self):
        a=fight(1,"2025-08-02",prob=.51)
        s=score([a],RULES[0])
        self.assertEqual(s["selected"],0)
        self.assertIsNone(s["accuracy"])

    def test_duplicate_fight_ids_rejected(self):
        a=fight(1,"2025-08-02")
        with self.assertRaisesRegex(ValueError,"duplicate fight ID"):
            validate([a,a],"2025")

    def test_year_and_fight_evidence_enforced(self):
        a=fight(1,"2025-08-02")
        a["date"]="2026-08-02"
        with self.assertRaisesRegex(ValueError,"Wrong time period"):
            validate([a],"2025")
        b=fight(2,"2025-08-02",experience=2)
        with self.assertRaisesRegex(ValueError,"prior-fight count"):
            validate([b],"2025")

    def test_policy_selection_is_validation_only(self):
        xs=[fight(i,"2025-10-01",prob=.7,winner=1) for i in range(65)]
        xs += [fight(i+65,"2025-10-02",prob=.55,winner=0) for i in range(40)]
        rule,reason,scores=select_rule(xs)
        self.assertIn(rule,RULES)
        self.assertEqual(len(scores),len(RULES))
        self.assertTrue(all(x["2025Selection"]["eligible"]==len(xs) for x in scores))

    def test_quarters(self):
        self.assertEqual(quarter("2026-01-02"),"Q1")
        self.assertEqual(quarter("2026-12-31"),"Q4")

    def test_all_validation_and_development_rows(self):
        val=[fight(i,"2025-07-04",winner=int(i%2==0)) for i in range(146)]
        months=("2026-01-01","2026-04-01","2026-07-01","2026-10-01")
        hold=[fight(i,months[i%4],winner=int(i%3!=0)) for i in range(266)]
        inp={"schema":"JSA_FRONTIER_CASES_V1","model":"nonlinear_ensemble",
             "selection2025":val,"development2026":hold}
        out=run(inp)
        self.assertEqual(out["development2026Count"],266)
        self.assertFalse(out["accuracy99_9Verified"])
        self.assertEqual(sum(x["riskAudit"]["n"] for x in out["quarterly2026"].values()),266)
        self.assertEqual(out["finalStatus"].split(".")[0],"NO AUTOMATIC POLICY PROMOTION")


if __name__ == "__main__":
    unittest.main()
