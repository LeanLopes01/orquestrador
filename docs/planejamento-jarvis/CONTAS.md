# Contas do Jarvis: conexão, diagnóstico e validação

Guia atualizado em 28/10/2026. Veja [ENTREGA.md](ENTREGA.md) para instalar o código implementado. Google/Notion já podem estar autorizados, conforme informado pelo usuário. **Não apagar nem recriar credenciais existentes para começar.** Foram feitas consultas SSH de somente leitura; contas reais ainda precisam de verificação após a publicação.

O [catálogo completo](CATALOGO.md) complementa este guia com os requisitos de cada uma das 75 integrações. Os campos daquele catálogo são dos templates; nesta implementação são guardados no n8n, sem usar a tabela de segredos em texto puro do n8n-claw.

## 1. Abrir o n8n existente

Executar no PC [abrir-n8n.cmd](../../scripts/planejamento-jarvis/abrir-n8n.cmd). O script abre um túnel SSH para o endereço documentado `user@your-server-ip`. Digitar a senha no terminal quando solicitado e manter a janela aberta.

Abrir **http://localhost:5679** no navegador do mesmo PC. Se já existe proprietário no n8n, usar seu login atual. O túnel não cria conta nem redefine senha. Se a porta estiver ocupada, o script falha em vez de encaminhar silenciosamente para destino incerto.

O callback configurado na instalação documentada é:

```text
http://localhost:5679/rest/oauth2-credential/callback
```

Copiar sempre a URL exibida na credencial real. Não confundir com `https://DOMINIO/webhook/oauth-callback`, usado pelo fluxo próprio do template n8n-claw: são implementações diferentes. Este plano preserva OAuth pelas credenciais nativas/genéricas do n8n. Login no celular requer callback HTTPS adequado ou iniciar a autorização no PC; `localhost` no celular não aponta para este PC.

## 2. Diagnóstico antes de reconectar

Executar [diagnosticar-servidor.cmd](../../scripts/planejamento-jarvis/diagnosticar-servidor.cmd). Consulta release, serviço, endpoint de saúde do n8n e `personal-status`. Não instala, não troca release, não ativa runtime e não lê arquivos de segredos. Pode pedir senha SSH e depois sudo. O status pode mostrar identificadores pessoais: não publicar a saída integral.

Interpretar em camadas:

| Resultado | Próxima verificação |
| --- | --- |
| SSH falha | Endereço, rede/VPN e usuário; não é problema Google |
| Serviço ausente/inativo | Confirmar instalação/release antes de qualquer pacote antigo |
| n8n indisponível | Contêiner, disco, volume e saúde do serviço |
| Comando `personal-status` inexistente | Runtime antigo; preparar release sobre a base ativa |
| Runtime `off` | Só ligar depois de verificar contas e permissões |
| `setup_required`/`authorizing` | Conferir credencial, workflow e configuração do gateway |
| `expired`/401 | Token revogado/expirado; reconectar a conta afetada |
| `identity_changed` | Conta diferente do cadastro; conferir identidade antes de redefinir vínculo |
| `no_shared_database` | Compartilhar base original Notion; verificar se é página/checklist ou data source |
| 403 do provedor | API/escopo/permissão do recurso; distinguir do 403 do gateway |
| 200 sem itens | Procurar recurso conhecido por ID; revisar filtros, conta, paginação e compartilhamento |
| Conectado no n8n, falha por voz | Gateway, serviço verificado, permissão do aparelho e ferramenta da sessão |

O comando de verificação abaixo já existe no código e **grava o estado da conexão**. Executá-lo depois de conferir release e credenciais; não faz parte do diagnóstico somente leitura:

```powershell
ssh -t user@your-server-ip "sudo jarvis-control personal-verify google_a"
ssh -t user@your-server-ip "sudo jarvis-control personal-verify google_b"
ssh -t user@your-server-ip "sudo jarvis-control personal-verify notion"
ssh -t user@your-server-ip "sudo jarvis-control personal-verify outlook"
```

Verificar apenas as contas utilizadas. Use [verificar-conta-jarvis.cmd](../../scripts/verificar-conta-jarvis.cmd), que permite selecionar uma conta, mostra a verificação por serviço e oferece ligar o runtime. Uma conta não configurada pode continuar em erro sem bloquear os serviços já verificados das demais.

Não executar `publicar-runtime-pessoal.cmd` ou outros publicadores antigos: foram feitos para releases específicas de outubro e podem depender de arquivos temporários já ausentes. Use [atualizar-jarvis-servidor.cmd](../../scripts/atualizar-jarvis-servidor.cmd), que verifica a base atual e os hashes do pacote antes de instalar.

## 3. Google A/B — conexão existente ou nova

1. No n8n, localizar **Jarvis Google A** e **Jarvis Google B** e conferir quais workflows as referenciam. Anotar apenas apelido, ID de credencial e conta esperada. Não exportar tokens.
2. No [Google Cloud Console](https://console.cloud.google.com/), escolher o projeto OAuth já usado. Habilitar Calendar API, Drive API e Gmail API conforme os serviços escolhidos. Não criar outro projeto se o existente estiver correto.
3. Em Google Auth Platform, conferir público do app e contas permitidas. Contas Gmail pessoais usam público externo; “Internal” só atende organizações Workspace elegíveis. Se estiver em teste, incluir cada usuário necessário.
4. Abrir o cliente OAuth do tipo **Web application**, conferir Client ID, secret válido e redirect URI exato mostrado pelo n8n. No cenário documentado, é a URL local da seção 1, acessível pelo túnel.
5. Configurar cada credencial com identidade (`openid email`) e apenas os serviços escolhidos. O cliente OAuth pode ser o mesmo; o token e o vínculo da conta A não podem sobrescrever os da B.
6. Clicar em conectar/reconectar somente na credencial necessária. No consentimento, escolher explicitamente a conta correta e conferir todos os escopos solicitados. Sessões de navegador separadas ajudam a evitar escolher a conta errada.
7. Rodar verificação da conta e testar um recurso conhecido. Registrar origem e horário, sem armazenar o conteúdo pessoal no relatório técnico.

| Serviço | Escopo inicial de leitura | Consulta de aceite |
| --- | --- | --- |
| Calendar | `https://www.googleapis.com/auth/calendar.readonly` | Evento conhecido em cada calendário habilitado, incluindo fuso e dia inteiro |
| Drive | `https://www.googleapis.com/auth/drive.readonly` | Buscar arquivo existente e abrir seu conteúdo; documentos Google exigem exportação |
| Gmail | `https://www.googleapis.com/auth/gmail.readonly` | Localizar e ler mensagem conhecida sem marcar como lida |
| Analytics | `https://www.googleapis.com/auth/analytics.readonly` | Listar propriedade GA4 autorizada e relatório de período conhecido |
| Ads | `https://www.googleapis.com/auth/adwords` | Listar conta/campanha acessível; escrita bloqueada por política do Jarvis |

Para Analytics, habilitar APIs de dados e administração usadas pelo conector e conceder acesso do usuário à propriedade GA4. Para Ads, habilitar API, informar developer token e customer ID; conta gerente pode exigir login-customer-id. Não presumir que o OAuth sozinho fornece acesso a propriedade, campanha ou nível de API. O escopo Ads é amplo: aplicar leitura no adaptador.

`drive.file` não oferece busca geral em todos os arquivos existentes. Aumentar escopos exige novo consentimento; editar a string no n8n sem reconectar não concede permissões ao token já emitido. Recursos compartilhados/Shared Drives e agendas secundárias precisam de descoberta e parâmetros próprios.

Em aplicativos externos no modo Testing, refresh tokens para esses acessos normalmente expiram em sete dias. Produção, verificação, políticas Workspace, revogação e outras condições também afetam validade; “publicado” não significa token eterno. Conferir [OAuth Google](https://developers.google.com/identity/protocols/oauth2) e [credenciais Google genéricas do n8n](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-generic/).

### Se autoriza, mas não lê

Conferir, nesta ordem: serviço selecionado no Jarvis → workflow ativo e apontando para a credencial certa → API habilitada → escopo concedido → identidade → acesso ao recurso → consulta sem filtros restritivos. Comparar a mesma operação diretamente no node e pelo gateway. Um retorno de autenticação correto não prova que `drive_search`, `drive_read` ou Calendar conseguem retornar dados.

O verificador atual pode reprovar a conta inteira quando só Gmail falha, mesmo que Drive funcione. A correção implementada mostra estado parcial e só libera os serviços verificados.

## 4. Notion — compartilhar os dados certos

1. Abrir o [painel de integrações Notion](https://www.notion.so/profile/integrations) e localizar a integração já usada no Jarvis. Confirmar workspace e capacidade de leitura. Criar outra somente se realmente necessário.
2. Na base original/página desejada, abrir menu de conexões e adicionar essa integração. Uma visualização vinculada pode não conceder acesso à base original; abrir a origem e compartilhar ali.
3. No n8n, localizar **Jarvis Notion** e conferir se o token é dessa integração. Usar apenas o campo de credencial, nunca o texto de um prompt. [Configuração no n8n](https://docs.n8n.io/integrations/builtin/credentials/notion/).
4. Selecionar uma tarefa conhecida e registrar seu link/ID, nome de propriedades e tipo real: base, data source, página ou bloco de checklist. Conferir status, prazo e responsável.
5. Verificar identidade e consultar esse recurso. Busca geral do Notion não equivale à busca de todo o texto de todos os blocos; descobrir página/base e depois ler conteúdo/propriedades com paginação.
6. Se a versão antiga encontra a integração, mas não encontra bases, inspecionar o formato real da resposta. Não trocar a versão da API isoladamente.

O gateway anterior usava `Notion-Version: 2022-06-28`. A nova release usa `2025-09-03` e acrescenta `data_sources`, descoberta das fontes de uma base, leitura de páginas/blocos e identificação explícita do schema de tarefas. A migração altera allowlist n8n, parser, consultas, verificação e testes na mesma release. A mudança de API de 2025 separou bancos de dados e fontes; bases com múltiplas fontes exigem atenção. [Guia oficial](https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03).

Se a fonte é só checklist numa página, o `notion_list_tasks` atual não basta. Isso deve aparecer como limitação suportada/pendente, não como “não há tarefas”. Validar filtros de concluído, prazo ausente e data de São Paulo com exemplos reais.

## 5. Outlook e Microsoft Teams

Para Outlook existente, preservar credencial e app registration. Para nova conexão:

1. Em [Microsoft Entra](https://entra.microsoft.com/), registrar aplicação que aceite o tipo de conta usado; Outlook.com/Hotmail precisa de suporte a contas pessoais.
2. Cadastrar callback Web mostrado no n8n. Criar client secret e guardar o **Value**, não o identificador do secret.
3. Configurar permissões delegadas: `openid`, `email`, `offline_access`, `User.Read`, `Mail.Read`. Organização pode exigir consentimento administrativo.
4. Em **Jarvis Outlook**, configurar cliente/tenant e autorizar. Verificar `/me` e leitura de mensagem conhecida.
5. Registrar expiração do client secret e procedimento de rotação. [Credenciais Microsoft no n8n](https://docs.n8n.io/integrations/builtin/credentials/microsoft/).

Teams é outro canal, com permissões e recursos próprios; Mail.Read não libera Teams. Antes de habilitar o adaptador, selecionar organização/equipe/canal, configurar credencial compatível com os nodes e mapear remetente autenticado para usuário autorizado do Jarvis. OAuth organizacional, disponibilidade de APIs e consentimento serão verificados no ambiente real.

## 6. Como conectar as demais entradas do catálogo

O [CATALOGO.md](CATALOGO.md) contém uma entrada por integração, com campos exigidos, instrução de obtenção/configuração, campos opcionais e ferramentas de referência. O fluxo implementado está detalhado em [ENTREGA.md](ENTREGA.md). As etapas de autorização são:

1. Instalar o conector adaptado e selecionar uma conta lógica/apelido; não ativar todas as ferramentas de escrita junto com leitura.
2. Abrir o painel oficial do provedor indicado no catálogo. Criar token ou autorização com os recursos necessários. Quando suportado, restringir ao projeto/base/repositório usado.
3. Cadastrar segredo no n8n. URL da instância precisa ser alcançável **pelo servidor**; `localhost` de um contêiner não é o PC Windows. Guardar só a referência de credencial no registro Jarvis.
4. Executar “Testar conexão”: identidade/workspace + uma leitura real de recurso conhecido. Se a integração apenas gera mídia, usar uma geração pequena e custo explícito; se só executa ações, validar em ambiente de teste.
5. Habilitar para os dispositivos escolhidos e testar pelo Jarvis. Registrar erro de escopo/recurso separadamente de token inválido.
6. Testar desconexão/revogação e reconexão. Pausar no Jarvis bloqueia uso, mas não revoga token no provedor.

Serviços sem autenticação também têm disponibilidade, limite e políticas próprias; “sem credencial” não garante uso ilimitado ou ausência de tráfego externo. Contratar planos e autorizar gastos não é parte deste planejamento.

Os manifestos são referências técnicas do template, não prova de compatibilidade atual. Campos/menu de provedor podem mudar; a fase de implementação verifica API e permissões antes de ativar cada conector. Há orientações específicas no catálogo para credenciais compartilhadas, endpoints MCP e serviços que dependem de terceiros.

## 7. Canais que não estão contados como contas nas 75 skills

| Canal | Passos para preparar a conexão | Teste de aceite |
| --- | --- | --- |
| Telegram | Criar/usar bot no BotFather; cadastrar token no n8n; configurar endpoint HTTPS e chat IDs permitidos; ligar remetente ao cadastro Jarvis | Mensagem do chat autorizado recebe resposta; outro chat é rejeitado |
| Slack | Criar app no workspace; configurar OAuth/event subscriptions conforme o adaptador; instalar no workspace; limitar canais e validar assinatura/event ID | Evento de canal autorizado cria uma única solicitação; resposta volta ao canal correto |
| Teams | Configurar aplicação/credencial Microsoft e node suportado; escolher equipe/canal; consentimentos e vínculo de remetente | Receber/responder no canal de teste sem liberar todas as pessoas do tenant |
| Discord | Criar aplicação e bot; token no serviço interno; permissões/intents exigidos pelo bridge; permitir apenas guilds/canais/usuários cadastrados | Mensagem permitida atravessa bridge→gateway; mensagem não permitida é recusada |
| WhatsApp | A adaptação do template exige canal Business/Cloud API, token, número, validação de webhook e mapeamento de mensagens; não usa a sessão pessoal do app por padrão | Recebimento e resposta de teste segundo permissões vigentes da conta |
| Paperclip / webhook próprio | Configurar endpoint autenticado, segredo por integração e mapeamento de eventos; validar identidade no servidor | Retry com mesmo ID não executa duas vezes |

As inscrições públicas e callbacks serão configurados depois que domínio/HTTPS existente forem verificados. O painel administrativo n8n pode continuar restrito ao túnel mesmo quando os endpoints de recepção específicos forem publicados.

## 8. Quando considerar uma conexão pronta

Checklist por conta: identidade correta; serviço autorizado; recurso conhecido lido; resultado mostra origem e horário; paginação funciona; token renovado quando aplicável; acesso negado a aparelho sem permissão; revogação efetiva; funcionamento com PC desligado. Para escrita, adicionar preview/aprovação, idempotência e verificação do efeito real. “Credencial salva” é apenas uma etapa.
