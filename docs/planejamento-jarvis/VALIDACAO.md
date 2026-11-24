# Validação da entrega — 28/10/2026

## Pacotes finais

O manifesto [release.json](../../artifacts/server/release.json) seleciona a atualização `20261028T111636Z-evolution`. Os scripts leem esse manifesto; não é necessário escolher um dos arquivos antigos da pasta.

| Artefato | SHA-256 |
|---|---|
| Pacote completo do servidor | `5deeb35479ca41239dada1734f68d7fcbf3e5652af09ba2af45d64e82447abc1` |
| Backend contido no pacote | `d09628235354dbe339645963ad2217d71b15eaa52e5d964e12e79252b99d7699` |
| Instalador Windows 0.3.0 | `d5d3f8fb43322547725873e9fb7dbc172e4dfe01d78e3ee9b25c112b710acb00` |

O publicador verifica os hashes no PC e no Linux. O instalador do PC verifica seu hash antes de alterar a inicialização do helper. Os manifestos [Android](../../artifacts/android/primary.json) e [S23 local](../../artifacts/android/companion-local.json) registram os hashes de cada APK.

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Backend local com as alterações | 310 testes passaram |
| Backend extraído do pacote final, sobre a base real do servidor | 293 testes passaram; quatro avisos de dependências, nenhuma falha |
| Pontes Node, produção, catálogo, estado cifrado, restrição de rede e arquivos | 19 testes passaram |
| Interface Playwright, navegação e layouts | 36 testes passaram |
| Flutter | Análise sem problemas e 42 testes passaram |
| Compilação Android arm64 | APK principal e companion gerados |
| Certificado Android | Igual ao aplicativo anterior; preservada a atualização sem apagar dados |
| Windows | Build de produção e instalador NSIS gerados |
| Bash e PowerShell | Scripts de implantação/restauração e scripts PowerShell passaram na análise de sintaxe |
| Integridade do upload | Hash do bundle e backend conferidos; 75 workflows; arquivos do adaptador conferidos contra os fontes; nenhum APK companion no upload |
| n8n 2.44.6 local | Credencial e workflow importados/publicados; chamada anônima retornou 403 e chamada autenticada do relógio retornou 200 com o horário de São Paulo |

As quantidades de testes do backend diferem porque o pacote parte da release efetivamente instalada no servidor, com os arquivos revisados sobrepostos. Ele não substitui indiscriminadamente o servidor pelo checkout local, que contém outros trabalhos.

O relatório automático do pacote está em [validation.json](../../artifacts/server/validation.json). Os registros locais ficam em `.local/evolution/backend-tests.log`, `packaged-backend-tests.log`, `node-tests-final.log` e `n8n-test.log`. O último ambiente descartável do n8n é indicado por `.local/evolution/n8n-last-sandbox.txt` e contém `server.log` e `result.json`.

O teste do n8n usa banco, credenciais fictícias e porta próprios. Ele não acessa suas contas. A verificação do relógio não comprova funcionamento real de todos os provedores. O teste espera tanto a inicialização quanto o registro assíncrono do webhook; o publicador também espera esse registro antes de trocar o backend.

## Estado da implantação

- **Servidor:** consulta SSH em 28/10 confirmou `/opt/jarvis/releases/20261024T011920Z-personal-runtime`, control ativo e n8n saudável. Nenhum pacote foi enviado ou instalado por esta sessão.
- **Windows:** instalador final disponível; a migração da inicialização e a instalação ocorrem quando você abre o script.
- **Motorola:** atualizado para 1.8.0, build 27; início do aplicativo conferido sem registro de crash naquele teste.
- **S23:** APK somente local; aparelho não atualizado e não testado fisicamente.
- **Google, Notion e demais contas:** exigem verificação de recursos reais após a publicação e autorização. Não foram usados tokens pessoais nos testes locais.

## Reproduzir e publicar

Execute os comandos abaixo na raiz do projeto para repetir a validação local. Eles não publicam no servidor:

```powershell
npm test
python scripts/validate-evolution.py
node scripts/test-n8n-catalog.mjs
```

O último comando usa a instalação descartável já preparada em `.local/n8n-validation` e pode demorar alguns minutos na primeira inicialização. Não inclua essa instalação de teste no upload.

Para publicar, siga [ENTREGA.md](ENTREGA.md), começando por [atualizar-jarvis-servidor.cmd](../../scripts/atualizar-jarvis-servidor.cmd). O teste do backend, o smoke de voz e a restauração isolada do backup no Linux só acontecem quando esse script for executado. O teste de upgrade pelo instalador Android aguarda uma versão posterior à build 27.

As pendências da fase avançada estão explícitas no final de [ENTREGA.md](ENTREGA.md); este relatório não declara essas funcionalidades concluídas.
