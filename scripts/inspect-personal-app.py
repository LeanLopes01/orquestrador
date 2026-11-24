"""Inspect only integration/navigation labels, without logging personal reports."""
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('serial', choices=['RQCX8093BJY', 'ZF52343HP4'])
args = parser.parse_args()
adb = Path('C:/Users/leanl/AppData/Local/Android/sdk/platform-tools/adb.exe')
prefix = [str(adb), '-s', args.serial]
remote = '/sdcard/jarvis-connections-window.xml'
subprocess.run(prefix + ['shell', 'uiautomator', 'dump', remote], check=True, capture_output=True)
raw = subprocess.check_output(prefix + ['shell', 'cat', remote])
tree = ET.fromstring(raw)
wanted = re.compile(r'Conexões|Connections|More|Mais|Google A|Google B|Outlook|Notion|Pessoal|Configuração|Suas contas|Aguardando configuração|precisa receber|não foi liberado|Atualizar|Tentar novamente|Pausada|Editar preferências', re.I)
nodes = []
for node in tree.iter('node'):
    label = node.get('text') or node.get('content-desc') or ''
    if wanted.search(label):
        nodes.append({k: node.get(k) for k in ['text', 'content-desc', 'bounds', 'clickable']})
print(json.dumps({'serial': args.serial, 'nodes': nodes}, ensure_ascii=True))
