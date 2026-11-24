"""Package the inspected server baseline plus reviewed source overlays. Never an env/token."""
import hashlib
import io
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JARVIS = Path('C:/J.A.R.V.I.S/jarvis')
BASE = '20261024T011920Z-personal-runtime'
OVERLAY = [
    'src/jarvis_control/integrations.py', 'src/jarvis_control/personal.py', 'src/jarvis_control/web.py',
    'src/jarvis_control/extensions.py', 'src/jarvis_control/browser.py', 'src/jarvis_control/releases.py',
    'src/jarvis_control/orchestrator.py', 'src/coding_agents.py',
    'src/jarvis_desktop/orchestrator_runtime.py', 'src/jarvis_desktop/agent_hook.py',
    'src/jarvis_desktop/hooks_setup.py', 'src/jarvis_desktop/agy_setup.py', 'src/jarvis_desktop/coding.py',
    'src/jarvis_desktop/outbox.py', 'src/jarvis_desktop/actions.py',
    'tests/test_evolution.py', 'tests/test_personal_gateway.py', 'tests/test_personal_integrations.py',
    'tests/test_planner_routing.py', 'tests/test_orchestration.py', 'tests/test_coding.py',
    'tests/test_hooks_capture.py', 'tests/test_agy_rule.py',
    'deploy/n8n/build.py', 'deploy/n8n/workflows/notion.json',
]


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-evolution'
    out = ROOT / 'artifacts/server'
    out.mkdir(parents=True, exist_ok=True)
    contents = {}
    with tarfile.open(ROOT / '.local/evolution/server-baseline.tar.gz') as archive:
        for member in archive:
            if member.isfile():
                assert not member.name.startswith('/') and '..' not in Path(member.name).parts
                contents[member.name] = (archive.extractfile(member).read(), member.mode)
    baseline = json.loads((ROOT / '.local/evolution/baseline/manifest.json').read_text(encoding='utf-8'))
    for rel in OVERLAY:
        if rel in contents and 'jarvis/' + rel in baseline:
            assert hashlib.sha256(contents[rel][0]).hexdigest() == baseline['jarvis/' + rel], f'Server base differs: {rel}'
        contents[rel] = ((JARVIS / rel).read_bytes(), 0o644)
    for path in (ROOT / 'dist').rglob('*'):
        if path.is_file():
            contents['deploy/web/' + path.relative_to(ROOT / 'dist').as_posix()] = (path.read_bytes(), 0o644)
    snapshot = json.loads((ROOT / 'docs/planejamento-jarvis/catalogo-n8n-claw.json').read_text(encoding='utf-8'))
    public = {'revision': snapshot['revision'], 'entries': []}
    for entry in snapshot['entries']:
        m = entry['manifest']
        public['entries'].append({'id':entry['id'],'source':entry['source'],'name':m['name'],
            'description':m['description'],'category':m['category'],'fields':m.get('credentials_required',[]),
            'tools':[t if isinstance(t,str) else t['name'] for t in m['tools']]})
    contents['deploy/web/catalog.json'] = (json.dumps(public, ensure_ascii=False).encode(), 0o644)
    contents['deploy/catalog/registry.json'] = ((ROOT / 'deploy/evolution/registry.json').read_bytes(), 0o644)
    apk = ROOT / 'artifacts/android/jarvis-primary-1.8.0-27.apk'
    assert apk.exists(), 'Build the primary APK first'
    mobile = {'version':'1.8.0','build':27,'channel':'primary','sha256':sha(apk),
        'size':apk.stat().st_size,'certificate_sha256':'37c1213cd775b299a35f9b9f8768942f739e4787d44aa3b7b81d864e3b9b7125',
        'changelog':'Histórico de atualizações, recuperação de eventos, conexões parciais e atualização de APK com verificação de hash e assinatura.'}
    contents['deploy/mobile/primary.json'] = (json.dumps(mobile,ensure_ascii=False).encode(),0o644)
    package = out / f'jarvis-backend-{version}.tar.gz'
    with tarfile.open(package, 'w:gz') as archive:
        for name,(data,mode) in sorted(contents.items()):
            info=tarfile.TarInfo(name);info.mode=mode;info.size=len(data)
            archive.addfile(info,io.BytesIO(data))
        archive.add(apk,arcname='deploy/mobile/jarvis-primary.apk')
    release={'version':version,'base_release':BASE,'package':package.name,'sha256':sha(package),'overlay':OVERLAY}
    payload=ROOT / '.local/evolution/payload'
    payload.mkdir(parents=True,exist_ok=True)
    (payload/'release.json').write_text(json.dumps(release,indent=2),encoding='utf-8')
    bundle=out/f'jarvis-update-{version}.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        archive.add(package,arcname=package.name)
        archive.add(payload/'release.json',arcname='release.json')
        for name in ['install.sh','rollback.sh','registry.json','workflows','n8n-nodes']:
            archive.add(ROOT/'deploy/evolution'/name,arcname=name)
        archive.add(JARVIS/'deploy/n8n/workflows/notion.json',arcname='notion.json')
    release.update(bundle=bundle.name,bundle_sha256=sha(bundle))
    (out/'release.json').write_text(json.dumps(release,indent=2),encoding='utf-8')
    (ROOT/'artifacts/android/primary.json').write_text(json.dumps(mobile,indent=2,ensure_ascii=False),encoding='utf-8')
    companion=ROOT/'artifacts/android/jarvis-s23-companion-1.8.0-27.apk'
    if companion.exists():
        (ROOT/'artifacts/android/companion-local.json').write_text(json.dumps({**mobile,'channel':'companion','published':False,'sha256':sha(companion),'size':companion.stat().st_size},indent=2),encoding='utf-8')
    # Human-readable checksum file contains no absolute paths or credentials.
    (out/'SHA256SUMS').write_text(f'{release["bundle_sha256"]}  {bundle.name}\n{release["sha256"]}  {package.name}\n')
    print(json.dumps(release,indent=2))


if __name__ == '__main__':
    main()
