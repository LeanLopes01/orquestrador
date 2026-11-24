"""Fetch only the immutable workflows selected by the reviewed catalog."""
import concurrent.futures
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads((ROOT / 'docs/planejamento-jarvis/catalogo-n8n-claw.json').read_text(encoding='utf-8'))
DEST = ROOT / 'deploy/evolution/catalog-source'

def fetch(entry):
    manifest = entry['manifest']
    if manifest.get('type') == 'bridge':
        return {'id':entry['id'],'type':'bridge','manifest':manifest}
    url=entry['source'].replace('/manifest.json','/workflow.json')
    with urllib.request.urlopen(url,timeout=30) as response:
        raw=response.read()
    value=json.loads(raw)
    return {'id':entry['id'],'type':'native','source':url,'sha256':hashlib.sha256(raw).hexdigest(),'manifest':manifest,'workflow':value}

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        records=list(pool.map(fetch,SNAPSHOT['entries']))
    for record in records:
        (DEST / f'{record["id"]}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(records)} immutable source records fetched. No workflows executed.')
    for record in records:
        if record['type']=='bridge':
            print(record['id'],'BRIDGE',record['manifest'].get('bridge_config',record['manifest'].get('mcp',{})))
            continue
        wf=record['workflow'];items=[wf.get('sub',wf)] if isinstance(wf,dict) else wf
        print(record['id'],[(n['name'],n['type']) for item in items for n in item.get('nodes',[])])

if __name__=='__main__':main()
