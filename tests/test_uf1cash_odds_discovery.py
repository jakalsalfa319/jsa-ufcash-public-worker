"""The Odds API connector: no secrets in URLs/logs and no fake bet eligibility."""
import io,json,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from scripts.uf1cash_odds_discovery import inspect,map_sports,normalize_events,get_api_json

NOW="2026-11-22T12:00:00Z"

def catalog():
    return [
      {"key":"mma_mixed_martial_arts","group":"MMA","title":"MMA","active":True,"has_outrights":False},
      {"key":"rugbyunion_northern_hemisphere","title":"Rugby Union","active":True,"has_outrights":False},
      {"key":"cricket_world_cup","title":"Cricket World Cup","active":True,"has_outrights":False},
      {"key":"formula1_2026","title":"Formula 1","active":True,"has_outrights":True},
      {"key":"baseball_mlb","title":"Baseball","active":True,"has_outrights":False},
    ]
def sample():
    return [{"id":"fictional-fixture","commence_time":"2026-12-01T18:00:00Z",
      "bookmakers":[{"key":"fictional","markets":[{"key":"h2h",
      "last_update":"2026-11-22T11:40:00Z",
      "outcomes":[{"name":"Fighter A","price":2.15},{"name":"Fighter B","price":1.83}]}]}]}]
class TestOddsDiscovery(unittest.TestCase):
    def test_empty_key_stays_disconnected(self):
        a=inspect(None,clock=NOW)
        self.assertEqual(a["status"],"NOT_CONNECTED_KEY_REQUIRED")
        self.assertEqual(a["events"],[])
        self.assertEqual(a["realBets"],0)
    def test_discovery_is_dynamic(self):
        v=map_sports(catalog())
        self.assertEqual(v["UFC"][0]["providerKey"],"mma_mixed_martial_arts")
        self.assertTrue(v["F1"][0]["hasOutrights"])
        self.assertEqual(v["HORSE_RACING"],[])
    def test_inactive_sport_never_selected(self):
        z=catalog();z[0]["active"]=False
        self.assertEqual(map_sports(z)["UFC"],[])
    def test_unknown_unrelated_sport_excluded(self):
        a=map_sports(catalog())
        self.assertFalse(any("baseball" in str(v) for v in a.values()))
    def test_invalid_catalog_rejected(self):
        with self.assertRaisesRegex(ValueError,"Invalid provider key"):
            map_sports([{"key":"x/y","active":True}])
    def test_event_price_values_redacted(self):
        result=normalize_events("mma_mixed_martial_arts","h2h",sample(),NOW)
        self.assertTrue(result[0]["hasPriceObservation"])
        self.assertFalse(result[0]["qualifiedForVirtualWager"])
        self.assertNotIn("2.15",json.dumps(result))
        self.assertNotIn("Fighter A",json.dumps(result))
    def test_future_market_timestamp_blocked(self):
        x=sample();x[0]["bookmakers"][0]["markets"][0]["last_update"]="2026-11-22T13:00:00Z"
        with self.assertRaisesRegex(ValueError,"time inconsistent"):
            normalize_events("mma_mixed_martial_arts","h2h",x,NOW)
    def test_provider_key_absent_not_assumed(self):
        with patch("scripts.uf1cash_odds_discovery.get_api_json",return_value=([],{})):
            o=inspect("some-private-key",max_requests=2,clock=NOW)
        self.assertEqual(o["status"],"CONNECTED_METADATA_ONLY")
        self.assertEqual(o["events"],[])
        self.assertEqual(o["providerRequestsChargedUpperBound"],0)
    def test_no_charged_calls_when_zero_budget(self):
        with patch("scripts.uf1cash_odds_discovery.get_api_json",return_value=(catalog(),{})) as f:
            o=inspect("some-private-key",max_requests=0,clock=NOW)
        self.assertEqual(f.call_count,1)
        self.assertEqual(o["providerRequestsChargedUpperBound"],0)
    def test_mock_live_feed_never_creates_bets(self):
        def fake(url,key,params=None):
            if url=="/sports/":return catalog(),{}
            return sample(),{}
        with patch("scripts.uf1cash_odds_discovery.get_api_json",side_effect=fake):
            o=inspect("some-private-key",max_requests=1,clock=NOW)
        self.assertEqual(o["providerRequestsChargedUpperBound"],1)
        self.assertEqual(o["realBets"],0)
        self.assertEqual(o["eligibleSelections"],0)
        self.assertNotIn("some-private-key",json.dumps(o))
    def test_quota_cap_enforced(self):
        with patch("scripts.uf1cash_odds_discovery.get_api_json",return_value=(catalog(),{})):
            with self.assertRaisesRegex(ValueError,"Maximum of 5"):inspect("some-private-key",max_requests=100,clock=NOW)
    def test_no_querystring_for_key(self):
        with self.assertRaisesRegex(ValueError,"Invalid endpoint path"):
            get_api_json("/sports/?apiKey=unsafe","some-private-key")
    def test_reject_bad_data_in_fixtures(self):
        with self.assertRaisesRegex(ValueError,"Expected provider event"):
            normalize_events("rugbyunion_x","h2h",{},NOW)

if __name__=="__main__":unittest.main()
