import datetime as dt
import unittest

from scripts.verify_official_results import (
    find_event_link,parse_event_fights,parse_fight_details,collect,safe_url
)
from scripts.card_integrity import PAIRS


def event_list():
    return '''<table><tr class="b-statistics__table-row">
    <td><a href="http://ufcstats.com/event-details/abcdef1234">UFC Fight Night: Prochazka vs Stirling</a></td>
    <td>Nov. 21, 2026</td></tr>
    <tr class="b-statistics__table-row">
    <td><a href="http://ufcstats.com/event-details/other1234">Another UFC event</a></td><td>Nov. 15, 2026</td>
    </tr></table>'''


def event_page(omitted=-1, replaced=-1):
    rows=[]
    for i,(a,b) in enumerate(PAIRS):
        if i==omitted:continue
        if i==replaced:b="New Replacement Fighter"
        rows.append('''<tr class="b-fight-details__table-row" data-link="http://ufcstats.com/fight-details/ID_'''+str(i)+'''">
          <td><p>W</p></td><td><p><a>'''+a+'''</a></p><p><a>'''+b+'''</a></p></td></tr>''')
    return ('<h2 class="b-content__title-highlight">UFC Fight Night: Prochazka vs Stirling</h2>'
         '<div>Nov. 21, 2026</div><table>'+''.join(rows)+'</table>')


def individual(i,result="W"):
    a,b=PAIRS[i]
    statuses={"W":("W","L"),"B":("L","W"),"D":("D","D"),"NC":("NC","NC")}[result]
    return '''<section>
    <div class="b-fight-details__person"><i class="b-fight-details__person-status">'''+statuses[0]+'''</i>
    <a class="b-fight-details__person-name">'''+a+'''</a></div>
    <div class="b-fight-details__person"><i class="b-fight-details__person-status">'''+statuses[1]+'''</i>
    <a class="b-fight-details__person-name">'''+b+'''</a></div></section>'''


class UFCStatsSourceTests(unittest.TestCase):
    def test_event_index_requires_exact_date_and_pair(self):
        self.assertEqual(find_event_link(event_list()),"http://ufcstats.com/event-details/abcdef1234")
        self.assertIsNone(find_event_link(event_list().replace("Nov. 21, 2026","Nov. 28, 2026")))
        self.assertIsNone(find_event_link(event_list().replace("Prochazka vs Stirling","Prochazka vs Someone Else")))

    def test_event_fight_links_exact(self):
        rows=parse_event_fights(event_page())
        self.assertEqual(len(rows),7)
        self.assertEqual(rows[0]["fighters"],list(PAIRS[0]))

    def test_result_winner_both_orientation(self):
        a,s,_=parse_fight_details(individual(0,"W"))
        self.assertEqual((a,s),(PAIRS[0][0],"COMPLETED"))
        a,s,_=parse_fight_details(individual(0,"B"))
        self.assertEqual((a,s),(PAIRS[0][1],"COMPLETED"))

    def test_draw_and_no_contest_not_wins(self):
        a,s,_=parse_fight_details(individual(0,"D"))
        self.assertEqual((a,s),("","DRAW"))
        a,s,_=parse_fight_details(individual(0,"NC"))
        self.assertEqual((a,s),("","NO_CONTEST"))

    def test_source_replacement_does_not_score(self):
        details={"http://ufcstats.com/fight-details/ID_"+str(i):individual(i)
                 for i in range(7)}
        results=collect(event_list(),event_page(replaced=2),details,
                        dt.datetime(2026,11,22,tzinfo=dt.timezone.utc),{})
        self.assertEqual(len(results),6)
        self.assertFalse(any(x["fighterA"]==PAIRS[2][0] for x in results))

    def test_missing_result_never_assumed_loss(self):
        details={"http://ufcstats.com/fight-details/ID_"+str(i):individual(i)
                 for i in range(7) if i!=4}
        results=collect(event_list(),event_page(),details,
                        dt.datetime(2026,11,22,tzinfo=dt.timezone.utc),{})
        self.assertEqual(len(results),6)

    def test_one_duplicate_event_rejected(self):
        self.assertIsNone(find_event_link(event_list()+event_list()))

    def test_bad_fight_name_blocks_parsing(self):
        bad=individual(0).replace("Navajo Stirling","Other Fighter")
        details={"http://ufcstats.com/fight-details/ID_0":bad}
        self.assertEqual(collect(event_list(),event_page(),details,
                      dt.datetime(2026,11,22,tzinfo=dt.timezone.utc),{}),[])

    def test_untrusted_host_rejected(self):
        with self.assertRaisesRegex(ValueError,"Outside UFCStats"):
            safe_url("https://ufcstats.com.evil.example/fight-details/x","/fight-details/")

    def test_incomplete_status_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Unresolved"):
            parse_fight_details(individual(0).replace(">W<",">?<"))

    def test_event_page_title_blocks_false_event(self):
        with self.assertRaisesRegex(ValueError,"identity"):
            parse_event_fights(event_page().replace("Prochazka vs Stirling","Not the same Event"))


if __name__=="__main__":
    unittest.main()
