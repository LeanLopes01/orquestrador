# Implantação por scripts executados pelo usuário

Plano de 27/10/2026. **Não há pacote de implementação desta evolução ainda.** Nesta etapa existem o planejamento, o inventário de integrações e dois auxiliares de leitura/túnel. Não foram criados publicadores fictícios que anunciam instalação sem conter código validado.

## Disponível agora

| Arquivo | O que faz |
| --- | --- |
| `scripts/planejamento-jarvis/diagnosticar-servidor.cmd` | Abre PowerShell e SSH, consulta release/serviço/n8n/status pessoal; não modifica configuração |
| `scripts/planejamento-jarvis/abrir-n8n.cmd` | Abre túnel SSH na porta 5679; depois o usuário abre o painel no navegador |
| `scripts/planejamento-jarvis/acesso-servidor.ps1` | Implementação dos dois auxiliares, com parâmetros de servidor e validação local |

Os scripts usam o endereço já documentado `user@your-server-ip`. Não armazenam senha e não desabilitam verificação da chave SSH. Se SSH usar chave, pode não pedir senha de login; sudo continua podendo pedir a senha administrativa. Uma chave de host desconhecida deve ser conferida pelo usuário antes de aceitar.

No PowerShell, para outro endereço:

```powershell
.\scripts\planejamento-jarvis\acesso-servidor.ps1 -Acao Diagnostico -Servidor usuario@servidor
.\scripts\planejamento-jarvis\acesso-servidor.ps1 -Acao Painel -Servidor usuario@servidor
```

Estes scripts foram preparados para Windows/OpenSSH; nesta sessão só foi validada sua sintaxe e a opção local de validação. O diagnóstico remoto só acontecerá quando o usuário executá-lo.

## Contrato obrigatório dos futuros publicadores

Cada entrega de código virá com um `.cmd` de dois cliques e um script PowerShell versionado. Fluxo visível: validar localmente → mostrar versão/plano → enviar → pedir sudo pelo terminal → backup → aplicar → testar → confirmar ou reverter. Senhas não serão argumentos, variáveis de ambiente, arquivos de configuração ou logs.

| Script futuro | Artefatos e efeito previsto |
| --- | --- |
| `01-inventariar-servidor.cmd` | Inventário sanitizado de release, versões, recursos e workflows; retorno salvo localmente |
| `02-backup-validar.cmd` | Backup consistente do backend, n8n e chave; criptografia; restauração isolada e verificação |
| `03-publicar-core.cmd` | API/gateway, migrações, eventos e compatibilidade com apps antigos |
| `04-publicar-integracoes.cmd` | Workflows adaptados, registro de conectores e serviços opcionais; preservar OAuth existente |
| `05-publicar-site.cmd` | Build estático do frontend e configuração de acesso autenticado no servidor |
| `06-verificar-contas.cmd` | Seleção por conta/serviço; identidade e leitura real; não apagar autorização funcional |
| `07-ativar-entrega.cmd` | Habilitar flags/workflows validados e confirmar estado final |
| `08-reverter-entrega.cmd` | Voltar ao estado anterior da entrega específica, com controle de compatibilidade de banco |
| `empacotar-windows.cmd` | Compilar instalador e registrar hashes, dependências e assinatura; operação local |
| `compilar-android.cmd` | Builds principal/companion, testes, hashes e certificado; não faz upload nem ADB |
| `publicar-android-principal.cmd` | Publicação separada do APK principal compatível, quando houver entrega validada |

Nomes acima são a especificação de entrega, **não arquivos já implementados**. O APK S23 não participa de publicadores nem de upload nesta fase. Quando o telefone voltar, uma instalação separada validará modelo, applicationId, certificado e versão antes de `adb install -r`; nunca escolher “o primeiro dispositivo”.

## Pacote de release

```text
release/<id>/
  manifest.json
  SHA256SUMS
  backend.tar.gz
  frontend.tar.gz
  workflows/*.json
  migrations/
  install.sh
  verify.sh
  rollback.sh
  release-notes.md
  test-evidence.json
```

Manifesto inclui ID, base esperada, versões de API/schema, hashes, dependências/digests, migrações reversíveis ou não, checks e destinos permitidos. Pacotes por fase só contêm os componentes daquela fase. Nunca incluir `.env`, tokens, cache de navegador, DPAPI, bases pessoais ou chaves privadas. Artefatos Android têm manifesto separado; artefato local S23 é explicitamente excluído do pacote remoto.

PowerShell valida presença e hashes **antes** do envio. Transferir por SCP/SFTP para diretório temporário único do usuário SSH com permissão restrita, verificar novamente no servidor e só então executar instalador conhecido. O instalador verifica dono, caminho resolvido e arquivos do manifesto antes de executar como root. Não usar download remoto de script seguido de shell nem `latest` durante a instalação.

Não depender de um `.tar.gz` que “já está em /tmp” desde entrega anterior. Todos os arquivos necessários são enviados pelo script da entrega. Tratar paths Windows com espaços/acentos corretamente, sem interpolar senha ou comando livre. Se a base ativa não corresponder, abortar e preparar pacote compatível; não sobrescrever uma atualização mais nova.

## Sequência no servidor

1. Adquirir lock de implantação; conferir disco/RAM, serviço, versão ativa, volumes e topologia n8n.
2. Gerar backup consistente: SQLite com mecanismo de backup/checkpoint ou parada controlada; volume n8n e sua chave com consistência; diretório de configuração e ACLs. Guardar cópia criptografada fora do servidor conforme destino definido pelo usuário.
3. Restaurar em ambiente isolado, impedindo timers, webhooks e notificações de dispararem; validar contagens e decifragem de credencial sem imprimir valores.
4. Instalar release em diretório novo e executar testes de migração/compatibilidade. Não reaproveitar diretório ativo como staging.
5. Importar workflows por ID estável/prefixo, inicialmente inativos. Resolver credenciais existentes sem sobrescrever token OAuth. Atualizar catálogo somente após validar dependências.
6. Ativar backend/site de forma controlada; testar endpoints, sessão, gateway e UI. API antiga permanece disponível para S23 e outros clientes ainda não atualizados.
7. Ativar apenas os workflows aprovados no manifesto, garantindo um único agendador por rotina. Registrar IDs antigos/novos para rollback.
8. Exibir versão realmente ativa, testes, integrações ainda pendentes e local do relatório sanitizado.

Serviços complementares usam redes internas, limites de recursos e perfis opcionais. Não executar `docker compose down -v`, trocar a chave de criptografia n8n ou migrar banco n8n como efeito colateral de importar workflows. Não publicar 5678/5679, Postgres ou consoles administrativos em todas as interfaces por copiar o compose do template.

## Falha, repetição e reversão

Erro em comando encerra a fase e retorna exit code não zero. Repetir script retoma/verifica a mesma release sem duplicar credenciais, jobs ou workflows. Artefato já enviado só é reutilizado se hash e manifesto forem idênticos. Registro local contém etapa/resultado, nunca senha.

Antes de ativar, falha descarta staging e mantém serviço atual. Depois de ativar, desligar workflows novos, voltar release e restaurar estado compatível. Migrações preferem expansão aditiva; alterações destrutivas exigem janela e recuperação específica. Não restaurar banco antigo por cima de novas gravações silenciosamente: pausar escrita e preservar dados posteriores antes da decisão de recuperação. Rollback não desfaz efeitos externos já enviados; esses precisam de registro/idempotência/compensação própria.

## Critérios para liberar cada script

Validação de sintaxe PowerShell/Bash; caminhos/digests; ambiente descartável; deploy repetido; falta de espaço; arquivo incompleto/hash divergente; base diferente; timeout; indisponibilidade n8n; restauração; preservação de credenciais e pareamento; relatório final verdadeiro. Só disponibilizar publicador operacional quando os artefatos da fase existirem e esses checks pertinentes passarem.
