"""Deterministic fingerprints for research datasets, not source authentication."""
import hashlib
import json
from scripts.uf1cash_holdout_integrity import validate

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()

def manifest(rows,train_end,calibration_end,evaluation_end):
    """Bind complete supplied row content to the declared temporal split."""
    split=validate(rows,train_end,calibration_end,evaluation_end)
    index={}
    for row in rows:
        key=(row["sport"],row["eventId"],row["recordId"])
        try:
            index[key]=_digest(row)
        except (TypeError,ValueError) as exc:
            raise ValueError("Dataset must contain finite JSON-compatible values") from exc
    fingerprints={}
    for name,events in split["partitions"].items():
        entries=[]
        for event in events:
            for record in event["recordIds"]:
                key=(event["sport"],event["eventId"],record)
                entries.append([*key,index[key]])
        fingerprints[name]={"rows":len(entries),"sha256":_digest(sorted(entries))}
    return {"schema":"UF1CASH_RESEARCH_CONTENT_MANIFEST_V1",
            "timestampManifestSha256":split["declaredTimestampManifestSha256"],
            "partitionContent":fingerprints,
            "datasetSha256":_digest({"cutoffs":split["cutoffsUTC"],"partitions":fingerprints}),
            "sourceAuthenticated":False,"modelTrained":False,"walletMutated":False}
