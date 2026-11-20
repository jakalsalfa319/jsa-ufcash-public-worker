import datetime as dt
import importlib.util
import unittest

HAS_PANDAS=importlib.util.find_spec("pandas") is not None


def example_table():
    import pandas as pd
    from scripts.precision_lab import FEATURES,RATINGS
    row={"date":pd.Timestamp("2031-05-20"),"outcome":"UPCOMING",
        "winner":None,"r_name":"Example Red","b_name":"Example Blue","card_pos":1}
    row.update({"r_"+f:4. for f in FEATURES})
    row.update({"b_"+f:3. for f in FEATURES})
    row.update({k:.5 for k in RATINGS})
    row["r_n_fights"]=8.
    row["b_n_fights"]=7.
    return pd.DataFrame([row])


def params(table=None):
    from scripts.prepare_future_card import draft
    return draft(example_table() if table is None else table,
       "2031-05-20","2031-05-20T18:00:00Z",
       "https://www.ufc.com/event/ufc-fight-night-may-20-2031",
       dt.datetime(2031,5,8,12,0,tzinfo=dt.timezone.utc),
       "a"*64)


@unittest.skipUnless(HAS_PANDAS,"Pandas not installed in dependency-free test stage")
class DraftBuilderTests(unittest.TestCase):
    def test_complete_draft_never_claims_review_or_results(self):
        from scripts.future_card_inference import valid_card
        from scripts.precision_lab import FEATURES,RATINGS
        x=params()
        self.assertEqual(x["reviewStatus"],"DRAFT")
        self.assertIsNone(x["reviewedAtUTC"])
        self.assertEqual(len(x["bouts"]),1)
        self.assertEqual(x["bouts"][0]["winner"],None)
        self.assertFalse(x["featureSource"]["independentlyAudited"])
        self.assertEqual(x["missingOrInvalidFeatures"],[])
        with self.assertRaisesRegex(ValueError,"manually reviewed"):
            valid_card(x,dt.datetime(2031,5,8,12,0,tzinfo=dt.timezone.utc),list(FEATURES)+list(RATINGS))

    def test_null_source_stat_survives_as_null_not_zero(self):
        df=example_table()
        df.loc[0,"r_c_td15"]=float("nan")
        x=params(df)
        self.assertIsNone(x["bouts"][0]["redFeatures"]["c_td15"])
        self.assertEqual(len(x["missingOrInvalidFeatures"]),1)
        self.assertIn("c_td15",x["missingOrInvalidFeatures"][0]["missingOrInvalid"])

    def test_known_result_and_future_labels_rejected(self):
        from scripts.prepare_future_card import draft
        df=example_table();df.loc[0,"winner"]=1.0
        with self.assertRaisesRegex(ValueError,"known/recorded"):
            params(df)
        df=example_table();df.loc[0,"winner"]=2.0
        with self.assertRaisesRegex(ValueError,"known/recorded"):
            params(df)

    def test_duplicate_bout_pair_rejected(self):
        import pandas as pd
        df=example_table()
        df2=df.copy()
        df2.loc[0,"r_name"]="Example Blue";df2.loc[0,"b_name"]="Example Red"
        df2.loc[0,"card_pos"]=2
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            params(pd.concat([df,df2],ignore_index=True))

    def test_wrong_event_fails(self):
        df=example_table();df["date"]="2031-05-18"
        with self.assertRaisesRegex(ValueError,"Expected 1"):
            params(df)


if __name__=="__main__":
    unittest.main()
