"""Build authenticated, isolated workflows. Existing credentials are never emitted."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'deploy/evolution'


def main():
    entries = []
    output = DEST / 'workflows'
    output.mkdir(exist_ok=True)
    bundled = DEST / 'n8n-nodes/catalog-source'
    bundled.mkdir(exist_ok=True)
    for path in sorted((DEST / 'catalog-source').glob('*.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        slug, manifest = record['id'], record['manifest']
        ident = hashlib.sha256(slug.encode()).hexdigest()[:16]
        credential_id = 'jc' + ident
        workflow_id = 'jw' + ident
        tools = []
        for tool in manifest['tools']:
            name = tool if isinstance(tool, str) else tool['name']
            tools.append(name)
        entries.append({'id': slug, 'name': manifest.get('name', slug),
                        'tools': tools, 'workflow_id': workflow_id,
                        'credential_id': credential_id, 'type': record['type']})
        nodes = [
            {'id': 'entry', 'name': 'Request', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2,
             'position': [0, 0], 'webhookId': workflow_id,
             'parameters': {'httpMethod': 'POST', 'path': 'jarvis-catalog/' + slug,
                            'authentication': 'headerAuth', 'responseMode': 'lastNode', 'options': {}},
             'credentials': {'httpHeaderAuth': {'id': 'jarvisGatewayAuth', 'name': 'Jarvis gateway'}}},
            {'id': 'connector', 'name': 'Connector', 'type': 'CUSTOM.jarvisCatalog', 'typeVersion': 1,
             'position': [240, 0], 'parameters': {'template': slug, 'googleOAuth': False, 'notionAuth': False},
             'credentials': {'jarvisConnection': {'id': credential_id, 'name': 'Jarvis · ' + manifest.get('name', slug)}}},
        ]
        workflow = {'id': workflow_id, 'name': 'Jarvis catalog · ' + manifest.get('name', slug),
                    'active': False, 'nodes': nodes,
                    'connections': {'Request': {'main': [[{'node': 'Connector', 'type': 'main', 'index': 0}]]}},
                    'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'none',
                                 'saveDataErrorExecution': 'none', 'saveManualExecutions': False,
                                 'executionTimeout': 70}}
        (output / (slug + '.json')).write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding='utf-8')
        shutil.copy2(path, bundled / path.name)
    (DEST / 'registry.json').write_text(json.dumps({'version': 1, 'entries': entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(entries)} authenticated workflows and registry generated.')


if __name__ == '__main__':
    main()
