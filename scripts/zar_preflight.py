#!/usr/bin/env python3
"""No-money future UFCash paper readiness gate. No external odds, predictions or wagers generated."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

def assess(watchlist: dict, today: dt.date | None = None) -> dict:
    today = today or dt.datetime.now(dt.timezone.utc).date()
    if watchlist.get('schema') != 'UFCASH_FUTURE_EVENT_WATCHLIST_V1':
        raise ValueError('Unknown watchlist schema')
    when = dt.date.fromisoformat(watchlist['eventDate'])
    u = urlparse(watchlist['officialCardUrl'])
    if u.scheme != 'https' or u.hostname not in ('www.ufc.com', 'ufc.com') or not u.path.startswith('/event/'):
        raise ValueError('Official UFC event URL required')
    rows = watchlist.get('fights')
    if not isinstance(rows,list) or not rows:
        raise ValueError('Missing matchups')
    seen, statuses = set(), []
    for fight in rows:
        red, blue = fight['red'], fight['blue']
        if not isinstance(red,str) or not isinstance(blue,str) or not red.strip() or not blue.strip() or red.casefold()==blue.casefold():
            raise ValueError('Invalid fighter names')
        key = tuple(sorted([red.casefold(),blue.casefold()]))
        if key in seen: raise ValueError('Duplicate matchup')
        seen.add(key)
        missing = []
        if fight.get('modelPRed') is None: missing.append('SHA_VERIFIED_PRE_FIGHT_MODEL_PROBABILITY')
        if fight.get('quote') is None: missing.append('SOURCE_TIMESTAMPED_FRESH_REFERENCE_QUOTE')
        statuses.append({'red':red,'blue':blue,'status':'NO_PAPER_ORDER','missingProof':missing,
                         'sourceDataMayNeedIndependentVerification':True})
    return {'schema':'UFCASH_ZAR_PREFLIGHT_V1', 'eventDate':when.isoformat(),
            'eventName':watchlist.get('eventName'), 'isFutureDate':when>today,
            'stage':'WATCHLIST_ONLY' if when>today else 'ARCHIVED_EVENT_DATE',
            'recordedFights':len(rows),'paperDecisions':0,'realBetsPlaced':0,
            'virtualStartingBankrollZAR':watchlist.get('virtualBankrollZAR'),
            'modelAndOddsProvenanceAudited':False,
            'note':'No paper bets created from a watchlist; only genuinely pre-event, separately verified inputs can be frozen by scripts.paper_forward.',
            'fights':statuses}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    report=assess(json.loads(a.input.read_text(encoding='utf-8')))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'stage':report['stage'],'eventDate':report['eventDate'],
          'paperDecisions':report['paperDecisions'],'recordedFights':report['recordedFights']},indent=2))

if __name__=='__main__':main()
