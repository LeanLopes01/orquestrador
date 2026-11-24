#!/bin/bash
# Run with sudo; credentials stay in the existing server state directory.
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Execute com sudo.'; exit 1; }
expected=/opt/jarvis/releases/20261022T223448Z-planner-routing
target=/opt/jarvis/releases/20261023T205950Z-personal-connections
active=$(readlink -f /opt/jarvis/current)
if [ "$active" != "$target" ]; then
    [ "$active" = "$expected" ] || { echo 'A release mudou. Rever o pacote antes de publicar.'; exit 1; }
    jarvis-deploy /tmp/jarvis-backend-20261023T205950Z-personal-connections.tar.gz 414ff5d70977fe2f02d6c3b5d177b34ea719a1dba649b68e39b488fc1bf07ef2
fi
# The user asked for both phones. Grant only the existing master and the known
# Samsung companion, never every paired app or a desktop. Do not change roles.
runuser -u jarvis-control -- env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/jarvis/current/src \
    /opt/jarvis/current/.venv/bin/python - <<'PY'
from jarvis_control.store import Store
store = Store('/var/lib/jarvis-control/control.db')
samsung = '931e18105a3641f98948555713e79641'
devices = [d for d in store.devices() if d.kind == 'app' and store.device_active(d.id)]
masters = [d.id for d in devices if store.profile(d.id).master]
assert len(masters) == 1 and samsung in [d.id for d in devices], 'Conferir os pareamentos antes de liberar.'
for device_id in {samsung, *masters}:
    assert store.set_personal_access(device_id, True)
    assert store.can_personal(device_id)
    print('Conexoes liberadas para', device_id)
assert store.integrations.view()['runtime_enabled'] is False
store.close()
PY
curl -fsS http://127.0.0.1:8090/v1/health
echo
echo 'Backend publicado. Atualize a tela Conexoes nos dois celulares.'
echo 'Autorizacoes Google/Microsoft/Notion e ferramentas de consulta ainda pendentes.'
