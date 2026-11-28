"""Research-only temporal partition validation for historical forecast evaluation."""
from datetime import datetime
from collections import defaultdict

def stamp(value):
    if not isinstance(value,str):
        raise ValueError("Timestamp required")
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("Timezone required")
    return t

def validate(rows, train_end, calibration_end, evaluation_end):
    """Partition by event start; exclude unresolved labels at each boundary.

    Declared timestamps are not independently authenticated.
    No fitting, odds, betting decisions or wallet mutations.
    """
    a,b,c=map(stamp,(train_end,calibration_end,evaluation_end))
    if not a<b<c:
        raise ValueError("Cutoffs must increase strictly")
    if not isinstance(rows,list) or not rows or len(rows)>100000:
        raise ValueError("Invalid dataset size")
    groups=defaultdict(list)
    seen=set()
    for row in rows:
        sport,event,record=(row.get(k) for k in ("sport","eventId","recordId"))
        if not all(isinstance(x,str) and x.strip() for x in (sport,event,record)):
            raise ValueError("Missing identity")
        identity=(sport,event,record)
        if identity in seen:
            raise ValueError("Duplicate observation")
        seen.add(identity)
        feature,start,result=map(stamp,(row["featuresAt"],row["startsAt"],row["resultAt"]))
        if not feature<start<=result:
            raise ValueError("Invalid feature/result chronology")
        groups[(sport,event)].append((start,result,record))
    parts={k:[] for k in ("train","calibration","holdout","excluded")}
    for key,group in sorted(groups.items()):
        starts={x[0] for x in group}
        if len(starts)!=1:
            raise ValueError("Inconsistent event start")
        start=next(iter(starts))
        final=max(x[1] for x in group)
        if start<a and final<a:
            part="train"
        elif a<=start<b and final<b:
            part="calibration"
        elif b<=start<c and final<c:
            part="holdout"
        else:
            part="excluded"
        parts[part].append({"sport":key[0],"eventId":key[1],"recordIds":sorted(x[2] for x in group)})
    if any(not parts[k] for k in ("train","calibration","holdout")):
        raise ValueError("All three partitions require eligible events")
    return {"schema":"UF1CASH_TEMPORAL_PARTITIONS_V1","partitions":parts,
            "eventCounts":{k:len(v) for k,v in parts.items()},
            "sourceTimestampsAuthenticated":False,"modelTrained":False,
            "walletMutated":False}
