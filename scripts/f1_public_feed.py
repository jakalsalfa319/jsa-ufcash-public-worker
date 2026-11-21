#!/usr/bin/env python3
"""Read-only, no-auth F1 schedule intake via Jolpica. NO betting odds or model predictions."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.request import Request, urlopen

BASE="https://api.jolpi.ca/ergast/f1"
USER_AGENT="UFCash-Research/1.0 (noncommercial R0 virtual testing)"


def schedule_from_response(payload, as_of=None):
    if not isinstance(payload,dict) or not isinstance(payload.get('MRData'),dict):
        raise ValueError('Invalid Jolpica payload')
    table=payload['MRData'].get('RaceTable')
    if not isinstance(table,dict) or 'Races' not in table:
        raise ValueError('Jolpica RaceTable missing')
    rows=table['Races']
    if not isinstance(rows,list): raise ValueError('Unexpected Jolpica race list')
    now=as_of or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None: raise ValueError('Timezone-aware as_of required')
    now=now.astimezone(dt.timezone.utc)
    result=[]
    for race in rows:
        try:
            date=race['date'];time=race['time']
            start=dt.datetime.fromisoformat(date+'T'+time.replace('Z','+00:00'))
            if not start.tzinfo: raise ValueError('Missing event time zone')
            r={'eventId':f"f1-{race['season']}-round-{int(race['round'])}",
               'sport':'F1', 'eventName':race['raceName'],
               'eventStartsUTC':start.astimezone(dt.timezone.utc).isoformat().replace('+00:00','Z'),
               'circuit':race.get('Circuit',{}).get('circuitName'),
               'status':'UPCOMING' if start>now else 'STARTED_OR_PAST',
               'eventSourceUrl':f"{BASE}/{race['season']}.json",
               'oddsAvailableFromThisSource':False,
               'modelProbabilityAvailableFromThisSource':False,
               'eligibleToFreezeAllInTicket':False}
            result.append(r)
        except (TypeError,KeyError,ValueError) as exc:
            raise ValueError('Incomplete F1 race information') from exc
    return {'schema':'UFCASH_F1_SOURCE_FEED_V1',
      'provider':'Jolpica F1 (read-only public API)',
      'sourceType':'RACE_SCHEDULE_NOT_BETTING_ODDS',
      'raceCount':len(result),'races':result,'simulatedBets':0,
      'note':'Schedule membership does not imply confirmed race outcome, odds, price availability or model edge.'}


def fetch_schedule(year):
    year=int(year)
    if not 1950<=year<=2100: raise ValueError('Invalid season')
    uri=f'{BASE}/{year}.json'
    req=Request(uri,headers={'User-Agent':USER_AGENT,'Accept':'application/json'})
    with urlopen(req,timeout=12) as response:
        if response.headers.get('Content-Length') and int(response.headers['Content-Length'])>300000:
            raise ValueError('Too large response')
        raw=response.read(300001)
    if len(raw)>300000: raise ValueError('Too large response')
    return schedule_from_response(json.loads(raw.decode('utf-8')))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--year',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    info=fetch_schedule(a.year)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(info,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'raceCount':info['raceCount'], 'futureRaces':sum(r['status']=='UPCOMING' for r in info['races']),
                      'betsPlaced':0}))

if __name__=='__main__':main()
