import unittest
from scripts.elo_challenger import Elo, build_history


def row(i, date, a, b, winner):
    return {"fight_id":str(i), "date":date, "r_id":a, "b_id":b, "winner":winner}


class EloChallengerTests(unittest.TestCase):
    def test_rating_symmetry_and_fair_coin(self):
        e = Elo()
        self.assertAlmostEqual(e.prob("a","b"), 0.5)
        e.rate_day([{"a":"a","b":"b","winner":1}])
        self.assertAlmostEqual(e.rating["a"]-1500, 12.0)
        self.assertAlmostEqual(e.rating["b"]-1500, -12.0)
        self.assertAlmostEqual(e.prob("a","b")+e.prob("b","a"), 1.0)

    def test_same_day_pre_update_probabilities(self):
        e=Elo()
        events=[
            {"a":"a","b":"b","winner":1},
            {"a":"a","b":"c","winner":0}
        ]
        predictions=e.rate_day(events)
        self.assertEqual([round(x[1],4) for x in predictions],[.5,.5])

    def test_future_bouts_never_seen(self):
        rows=[
            row(1,"2026-10-01","a","b",1),
            row(2,"2026-11-21","a","b",0)
        ]
        e,m=build_history(rows,"2026-11-21")
        self.assertEqual(m["fightResultsBeforeEvent"],1)
        self.assertEqual(e.count["a"],1)

    def test_duplicate_fight_id_blocks_result(self):
        items=[row(1,"2026-10-01","a","b",1),row(1,"2026-10-02","a","b",0)]
        with self.assertRaisesRegex(ValueError,"Duplicate fight id"):
            build_history(items,"2026-11-21")

    def test_eligible_holdout_requires_three_prior_bouts_each(self):
        rows=[
            row(1,"2023-01-01","a","b",1),
            row(2,"2023-02-01","a","b",0),
            row(3,"2023-03-01","a","b",1),
            row(4,"2024-01-01","a","b",1)
        ]
        _,m=build_history(rows,"2026-11-21")
        self.assertEqual(m["eligible"],1)
        self.assertEqual(m["fightResultsBeforeEvent"],4)

    def test_no_fake_perfect_accuracy_when_no_eligible_cases(self):
        _,metrics=build_history([row(1,"2024-02-01","x","y",1)],"2026-11-21")
        self.assertEqual(metrics["eligible"],0)
        self.assertIsNone(metrics["accuracy"])


if __name__=="__main__":
    unittest.main()
