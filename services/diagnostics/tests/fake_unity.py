"""Imita a CLI da Unity nos testes: escreve log, relatórios e XML conforme o método pedido."""

import sys
import time
from pathlib import Path

args = sys.argv[1:]


def value(flag: str) -> str | None:
    return args[args.index(flag) + 1] if flag in args else None


log = Path(value("-logFile"))
project = Path(value("-projectPath"))
(project / "Library" / "PackageCache").mkdir(parents=True, exist_ok=True)  # "importação"
# Linhas reais de uma execução que licencia normalmente (não podem virar "licença indisponível").
text = ["[Licensing::Module] LicensingClient has failed validation; ignoring",
        "[Licensing::Module] Error: Access token is unavailable; failed to update",
        "[Licensing::Client] Successfully resolved entitlement details",
        "Built from 'x' branch; Version is '6000.3.10f1'"]
method = value("-executeMethod")

if "-runTests" in args:
    mode = (project / "Assets" / "modo_testes.txt").read_text().strip()
    xml = Path(value("-testResults"))
    if mode == "sem-xml":
        log.write_text("\n".join(text))
        sys.exit(2)
    cases = {"zero": "", "falha": '<test-case fullname="Suite.Quebra" result="Failed"><failure><message>esperado 1'
                                   '</message></failure></test-case><test-case fullname="Suite.Ok" result="Passed"/>'}[mode]
    total, failed = (0, 0) if mode == "zero" else (2, 1)
    xml.write_text(f'<test-run total="{total}" passed="{total - failed}" failed="{failed}" skipped="0" '
                   f'inconclusive="0" result="{"Failed" if failed else "Passed"}">{cases}</test-run>')
    log.write_text("\n".join(text))
    sys.exit(1 if failed else 0)

if method is None:  # importação/compilação
    if (project / "Assets" / "quebrado.txt").exists():
        text += ["[ScriptCompilation] Requested script compilation because: x",
                 "Assets\\Scripts\\A.cs(3,1): error CS1002: ; expected", "*** Tundra build failed (1 s)"]
        log.write_text("\n".join(text))
        sys.exit(1)
    text += ["[ScriptCompilation] Requested script compilation because: x", "*** Tundra build success (1 s)"]
    log.write_text("\n".join(text))
    sys.exit(0)

report = Path(args[args.index("-executeMethod") + 3])
if method == "Ok.Run":
    report.write_text("RESULTADO: OK\nnota  tudo certo", encoding="utf-8")
    code = 0
elif method == "Falha.Run":
    report.write_text("RESULTADO: 1 FALHA(S)\nFALHA PV atual não espelhou (1 campo(s))", encoding="utf-8")
    code = 1
elif method == "Trava.Run":
    time.sleep(60)
    code = 0
elif method == "Licenca.Run":
    text.append("No valid Unity Editor license found. Please activate your license.")
    code = 1
else:  # Sem.Relatorio
    code = 1
log.write_text("\n".join(text))
sys.exit(code)
