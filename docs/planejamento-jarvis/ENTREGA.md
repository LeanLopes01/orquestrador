# Jarvis — entrega de 28/10/2026

Esta entrega tem código e artefatos compilados. **O servidor ainda não recebeu alterações:** a publicação será feita quando você abrir o script indicado abaixo. O Motorola conectado foi atualizado para **1.8.0, compilação 27**, preservando a assinatura e o pareamento. O APK companion do S23 está somente no PC e não faz parte do upload.

Os resultados dos testes, hashes dos pacotes finais e limites de validação estão em [VALIDACAO.md](VALIDACAO.md).

## Começar

1. Abra [atualizar-jarvis-servidor.cmd](../../scripts/atualizar-jarvis-servidor.cmd). Ele confere o hash local, envia o pacote por SSH, confere novamente no Linux e pede a senha do `sudo` no terminal. Não precisa informar senha no chat. Mantenha a janela aberta até a conclusão.
2. Abra [instalar-jarvis-pc.cmd](../../scripts/instalar-jarvis-pc.cmd). Ele guarda o antigo início automático, encerra o helper de forma normal, remove o início no login do Windows e abre o instalador. Se houver tarefa ativa, a instalação para para você terminar/cancelar essa tarefa. Depois abra **Jarvis** pelo menu Iniciar.
3. Para acessar pelo navegador remoto, abra [parear-navegador.cmd](../../scripts/parear-navegador.cmd) e siga a sequência: gerar código → informar no [site do Jarvis](https://your-jarvis-api.example.com/) → voltar ao terminal → escolher o ID do navegador para conceder permissões. A sessão usa cookie HttpOnly/Secure, dura sete dias e pode ser encerrada em **Sair**.
4. Abra o [n8n pelo túnel SSH](../../scripts/planejamento-jarvis/abrir-n8n.cmd) e siga [CONTAS.md](CONTAS.md) para as contas existentes; [CATALOGO.md](CATALOGO.md) e [OPERACOES.md](OPERACOES.md) cobrem as demais integrações.
5. Execute [verificar-conta-jarvis.cmd](../../scripts/verificar-conta-jarvis.cmd), selecione a conta e confira o resultado. O script oferece habilitar o runtime pessoal **dos serviços verificados**. Para conceder acesso ao PC, use [autorizar-dispositivo-jarvis.cmd](../../scripts/autorizar-dispositivo-jarvis.cmd).

Não use os publicadores antigos de outubro para instalar esta entrega. O novo pacote exige a base `20261024T011920Z-personal-runtime`, que foi consultada no servidor por SSH somente leitura. Se essa base mudar, o publicador recusa a atualização.

Se aparecer **ATUALIZACAO ADIADA**, existe uma execução pendente no Jarvis. O atualizador mostra o ID antes de enviar o pacote. Abra **Projetos**, confira essa execução e espere a conclusão ou cancele-a se não quiser continuar esse trabalho; então execute o atualizador novamente. Essa proteção não cancela tarefas automaticamente. O servidor também repete a verificação antes de parar serviços, mesmo se a consulta inicial pelo PC estiver indisponível. Uma recusa nessa etapa não exige restauração do backup.

## O que está implementado

| Parte | Entrega |
|---|---|
| Interface | Central HUD, telemetria real, navegação, conexões, busca no catálogo, rotinas, atualizações e manutenção das telas Projects/RAG/contexto/ingestão/relatórios |
| Windows | Instalador Tauri 0.3.0, Node empacotado e servidor loopback de produção; sem dependência de Vite em execução |
| Ciclo de vida | Helper/RAG iniciados pelo aplicativo; fechamento normal aguarda tarefa ativa; monitoramento do processo pai; início automático anterior tem backup e migração por script |
| Site | Mesmo frontend servido pelo backend existente, pareamento e autorização independentes; RAG remoto passa pelo servidor e depende do PC conectado |
| Google | Verificação e disponibilidade por serviço; uma falha de Gmail não esconde Drive/Calendar já verificados |
| Notion pessoal | API 2025-09-03, descoberta e consulta de data sources, schema e paginação, verificação com consulta real |
| Catálogo | 75 workflows protegidos: 71 adaptadores nativos e quatro pontes MCP; registro no servidor; credenciais cifradas no n8n; cache cifrado por conexão |
| Execução do catálogo | Habilitar/pausar, preparar argumentos concretos, confirmar chamada, vínculo ao dispositivo, prazo de cinco minutos, resultado persistido e bloqueio de repetição da mesma chamada |
| Arquivos dos templates | Protocolo File Bridge adaptado internamente, sem serviço público; arquivos cifrados, limite de 10 MB por arquivo e 200 MB no cache, expiração em 24 horas |
| Android | Histórico com filtros, persistência antes do ACK/cursor, recuperação depois de falha, acesso também em paisagem, status parcial de conexões |
| Atualização Android | Canal principal autenticado, hash SHA-256, conferência da assinatura e do versionCode, instalador normal do Android; S23 sem publicação |
| Implantação | Upload, verificação de base/hash, backup cifrado, verificação de restauração do SQLite n8n em pasta isolada, importação preservando credenciais e workflows já configurados, testes do backend, smoke de voz e procedimento de rollback |

A interface web remota não abre os serviços `localhost` do celular. Contexto em disco, ingestão e runner de relatórios local ainda usam a instalação Windows. As consultas RAG remotas já têm caminho autenticado pelo servidor. Informações não medidas não são substituídas por números de demonstração.

## Conectar um dos 75 adaptadores

1. Depois da publicação, encontre no n8n o workflow **Jarvis catalog · NOME**. Cada conector tem ID estável e uma credencial **Jarvis · NOME**, do tipo **Jarvis · Conta protegida**.
2. Abra essa credencial. Preserve **Chave do estado local**: ela foi gerada no servidor e cifra tokens renovados/cache. No campo **Configuração da conta (JSON)**, preencha os nomes de campos indicados para esse conector em [OPERACOES.md](OPERACOES.md). O guia [CATALOGO.md](CATALOGO.md) explica onde obtê-los no provedor. Não coloque segredos no workflow, no pedido ao Jarvis ou nos argumentos de ferramentas.
3. Se o serviço tem domínio próprio, cadastre sua origem em **Origens adicionais permitidas**, por exemplo `https://cloud.seudominio.com`. Para um serviço de sua rede, cadastre origem e porta exatas e ative **Permitir rede privada nessas origens**. Isso não autoriza URLs arbitrárias. `localhost` do contêiner n8n não é o Windows.
4. Salve a credencial. No workflow, confira que o nó **Connector** aponta para ela. Publique mudanças feitas no editor. O importador preserva workflows de catálogo já existentes, incluindo o mapeamento de suas credenciais.
5. No Jarvis, vá a **Contas e integrações**, escolha o conector e clique em **Habilitar após configurar**. Essa ação libera a preparação de chamadas; não é um selo de conta verificada.
6. Escolha uma operação de leitura e argumentos de um recurso conhecido. Os contratos e exemplos de chaves estão em [OPERACOES.md](OPERACOES.md). Revise a chamada preparada e confirme. Confira a identidade/recurso retornado. Só depois use operações de escrita.
7. Em falha de rede/tempo limite, use **Consultar resultado sem repetir**. O estado `unknown` significa que o provedor pode ter processado a chamada; repetir com outro plano pode duplicar uma escrita. A mesma chamada não é reenviada automaticamente.

Todas as chamadas do catálogo exigem confirmação nesta entrega. As ferramentas de voz existentes de Google/Notion continuam no gateway pessoal e respeitam suas permissões; os 75 conectores não são inseridos automaticamente no prompt de voz.

### Reutilizar Google e Notion existentes

Para um workflow Google, abra **Connector**, ative **Usar OAuth Google existente** e selecione **Jarvis Google A** ou **Jarvis Google B** no campo OAuth2. O nó aproveita o token e a renovação existentes sem copiar segredos para JSON. Preserve a conta lógica escolhida. Para automações de escrita, crie uma credencial separada com os escopos necessários; as credenciais pessoais atuais são de leitura e não devem ganhar permissões indiscriminadamente.

Para o workflow Notion, ative **Usar Notion existente** e selecione **Jarvis Notion**. Compartilhe a página/base original com a integração. O conector geral oferece busca/leitura de páginas; a ferramenta pessoal de tarefas ainda depende de uma data source com propriedades compatíveis. Checklist solto em uma página não vira uma base de tarefas automaticamente.

Não altere tokens em **Chave do estado local**. Se mudar esse valor, o cache anterior deixa de poder ser aberto; a mensagem do nó explica a incompatibilidade. Não apague a credencial original para resolver um problema de escopo.

## Android e S23

O Motorola `moto g(8) power lite` foi atualizado por `adb install -r`. Antes, foi guardado o APK 1.7.0 em `.local/evolution/android-backup/`. O aplicativo instalado e os dois APKs novos têm o mesmo certificado SHA-256:

```text
37c1213cd775b299a35f9b9f8768942f739e4787d44aa3b7b81d864e3b9b7125
```

O certificado existente é Android Debug e foi preservado para permitir atualização sem apagar dados. Os manifestos com hashes estão em [artifacts/android](../../artifacts/android/). A distribuição atual continua pessoal.

No app, abra **Atualizações** e o ícone **Versão do aplicativo**. Depois de publicar o servidor, esse painel consulta o canal principal. O download só é oferecido se o versionCode publicado for maior que o instalado. Na primeira atualização por esse caminho, o Android pode pedir autorização para o Jarvis instalar pacotes; a instalação sempre pede confirmação.

O [APK companion 1.8.0](../../artifacts/android/jarvis-s23-companion-1.8.0-27.apk) fica local. Nenhum script desta entrega envia esse arquivo ao servidor ou ao S23. Seu app anterior continua compatível com a API. O teste no aparelho S23 fica pendente até ele voltar a estar disponível.

O transporte de eventos continua usando a conexão do aplicativo e a recuperação existente em segundo plano. **FCM/ntfy não foi ativado**; não há promessa de aviso instantâneo com o aplicativo suspenso pelo Android. A central permite recuperar o histórico depois.

## Backup e restauração

O publicador para n8n/control para capturar um backup consistente. O n8n volta para importar os conectores; o control permanece parado até a ativação do backend. A primeira instalação pode levar vários minutos pela publicação dos 75 workflows e pelos testes; mantenha a janela aberta. Não começa com chamada de voz ou job de projeto ativo. Os arquivos ficam em `/var/backups/jarvis-evolution/VERSAO`, cifrados; a chave fica separada em `/var/lib/jarvis-backup-keys/VERSAO.key`, acessível por root. Para recuperar em outro disco/servidor, é necessário preservar **backup e chave**. Não deixe a única cópia no mesmo disco em uso.

O script descriptografa o backup n8n numa pasta temporária isolada e executa `PRAGMA quick_check` antes de instalar conectores. Isso acontece **quando você executar o publicador**; não foi executado remotamente nesta sessão.

Use [restaurar-jarvis-servidor.cmd](../../scripts/restaurar-jarvis-servidor.cmd) para voltar ao backup desta entrega. Ele solicita `RESTAURAR` porque volta contas, workflows e dados ao momento do backup. Os dados atuais de control são preservados numa pasta `before-restore`; não são mesclados automaticamente. O n8n também volta ao estado do backup. O `jarvis-deploy` mantém seu rollback de release em falha de teste/smoke.

## Limites e pendências explícitas

- Nenhum consentimento OAuth pode ser dado pelo pacote. A leitura de recursos conhecidos nas suas contas deve ser confirmada depois da publicação e autorização. Testes locais não comprovam acesso a suas contas.
- O catálogo inteiro foi empacotado e os contratos JS foram validados; não foram feitos testes reais contra todos os 75 provedores. APIs externas, escopos, planos pagos, campos e disponibilidade de MCP podem exigir ajustes específicos.
- `email-imap-smtp` usa a ponte interna IMAP/SMTP com TLS obrigatório. Cadastre também as origens de e-mail na credencial, por exemplo `imaps://imap.exemplo.com:993,smtp://smtp.exemplo.com:587`. O provedor pode exigir senha de aplicativo ou desabilitar autenticação por senha. Não foram enviados e-mails de teste para terceiros.
- `config-backup` opera sobre o armazenamento isolado do conector, não sobre credenciais e configuração do Jarvis central. Use o backup do publicador para o sistema completo.
- Overlay/wake word no Windows, animação ligada ao áudio, novas pipelines locais de mídia/3D e transporte push alternativo da fase avançada não foram implementados nesta entrega. Os recursos existentes de voz, modelos, RAG, browser e projetos foram preservados; copiar os templates não torna recursos exclusivos de macOS compatíveis com Windows.
- Fechar o aplicativo aguarda uma tarefa ativa. Em crash da janela, o processo local tenta encerrar de forma normal e repete depois se há trabalho em andamento; não mata o projeto para simular desligamento instantâneo.

Este arquivo diferencia o que está pronto do que ainda exige publicação, credenciais, aparelho disponível ou desenvolvimento adicional. O plano original continua em [PLANO.md](PLANO.md), com esta entrega como referência de estado.
