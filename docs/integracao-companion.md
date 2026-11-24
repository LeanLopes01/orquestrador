# Integração Jarvis e S23 FE — 20/10/2026

## O que foi implementado

- S23 FE (`SM-S711B`, serial USB `RQCX8093BJY`): APK companion 1.5.0 (19), instalado por atualização, preservando o pareamento. Motorola não recebe esse APK.
- Companion tem Reports, AI limits, Projects, rotinas e voz. O listener Android e o controlador Dart bloqueiam mensagens WhatsApp/Instagram nesse modo. `work_access` é separado de `master` no servidor.
- Projects no site e no celular usam as mesmas conversas e execuções do Jarvis. O servidor persiste os dados no SQLite existente. O helper executa no BATCOMPUTADOR em cópias de trabalho.
- Novo pedido, aprovação e despacho verificam se o processo local está em execução. Quando indisponível, novos pedidos são recusados, sem fila para execução automática posterior. Repetir a mesma requisição recupera a conversa existente.
- Progresso inclui estado, atualização e trechos limitados de stdout/stderr com remoção de padrões de segredos. Atualizações intermediárias usam `job_progress`; apenas o resultado final recebe ACK e reenvio durável.
- `check_coding_agents` também consulta pedidos salvos no servidor. O histórico continua consultável quando o PC estiver offline; os dados salvos não provam atividade atual.
- Finalização, plano pronto e perguntas usam os eventos já existentes. O celular mostra notificação e anúncio conforme suas configurações de áudio. Tocar um report abre sua leitura pelo fluxo existente.

## Como usar

1. Inicie `iniciar-ui.cmd` no PC principal e mantenha o processo aberto. O helper Jarvis Desktop precisa estar conectado.
2. Abra `http://127.0.0.1:1420/#projects` ou Projects no S23 FE.
3. Envie um objetivo. A conversa aparece nos dois dispositivos. O planejador pode responder, fazer perguntas ou propor um plano.
4. Aprovar um plano inicia as tarefas de sua versão/hash. Aplicar os resultados ao projeto original é uma decisão separada; a ponte web não expõe aplicação automática.
5. Pergunte por voz pelo progresso. O Jarvis deve consultar os dados e mencionar dúvidas, aprovações pendentes e resultados verificados.

Fechar apenas a aba não encerra o processo local. Para ficar indisponível a novos pedidos, encerre `iniciar-ui.cmd` com Ctrl+C. Uma tarefa já aceita pode terminar; a verificação é feita antes de cada novo despacho.

## Papéis e publicação

- Samsung: `931e18105a3641f98948555713e79641`, companion com `work_access`, sem master.
- PC principal: `79652afcd37f48148e028142965d4caf`, desktop com acesso a Projects.
- Motorola mantém seu pareamento e papel existentes.
- Publicação concluída pelo script de ativação no SSH; release ativa `20261021T005253Z-companion`. Os scripts de publicação registram essa entrega e não devem ser repetidos como se fossem um atualizador genérico.
- O deploy original executa testes, smoke test e rollback. Não basta executar `jarvis-control work` antes de publicar: a versão anterior não conhece esse comando.

## Validação realizada

- Backend: 163 testes passaram, incluindo papel companion, rejeição offline, persistência de progresso, remoção de segredos e consulta de dados salvos com PC offline. O teste de transporte acompanha atualizações intermediárias pelo WebSocket antes da conclusão.
- UI: cinco testes de navegação/contexto, mais teste de Projects com falha offline, preservação de texto, reuso do request ID e layout móvel.
- Flutter: 28 testes gerais, teste dedicado companion, análise estática sem problemas e build release ARM64. Versão instalada confirmada por ADB.
- LiveKit: simulação `SR_jpByZ7catsQS`, sete de nove cenários concluídos; o cenário novo de progresso passou. Dois cenários existentes terminaram por timeout de geração (recusa de pedido nocivo e música). A suíte completa não está verde.
- Debugger em áudio: a frase de progresso foi transcrita e chamou `check_coding_agents`. A resposta apareceu depois do retorno do comando do debugger; latência de voz ainda precisa de acompanhamento.
- Esses testes não provam compilação ou sucesso de testes Unity no DiceVTT.

## Para tornar o aplicativo completo

1. **Unity real:** executor de EditMode/PlayMode/build, timeout, logs e XML de resultados; hoje os agentes produzem alterações e reports, mas não há pipeline Unity integrado.
2. **Contexto versionado:** C# e símbolos do projeto, hash/commit por trecho, controle de frescor e orçamento em tokens. O grafo atual lê notas e wikilinks; não comprova que o banco LightRAG representa o código atual.
3. **Políticas efetivas:** aplicar orçamento, escolha de modelos, caminhos autorizados e limites de tentativa ao executor. Os campos do protótipo continuam sendo preferências locais.
4. **Revisão de mudanças:** integrar diffs e evidências reais às telas de revisão, unificando rascunhos locais e Projects. Confirmar Git versus Plastic antes de automatizar integração.
5. **Instalador:** empacotar a ponte local e o helper com o Tauri, início/parada explícitos, atualização, assinatura e backup. A interface atual é operacional pelo servidor Vite/preview, não como executável nativo independente.
6. **Confiabilidade de voz e celular:** medir latência real, testar reconexão após reinício e notificações com o aparelho bloqueado, além dos testes automatizados.

## Estado da ativação

Servidor ativo, acessos do S23 FE e PC confirmados, APK instalado e helper atualizado. Motorola preservado na versão 1.4.0 (23); Samsung na versão 1.5.0 (19).

Teste real enviado pelo S23 FE concluiu a leitura de `ProjectSettings/ProjectVersion.txt`, respondendo Unity **6000.3.10f1**, sem alterar o projeto. A primeira execução levou aproximadamente cinco minutos, incluindo a cópia isolada inicial. A continuação na mesma conversa terminou em cerca de 17 segundos.

O primeiro teste revelou que o helper não enviava snapshots dos jobs ativos: o celular permanecia em “Aguardando progresso” até o resultado final. Corrigido o envio periódico a cada três segundos e acrescentada a contagem de arquivos durante a preparação da cópia. A segunda execução confirmou progresso recebido pelo servidor antes de concluir. O CLI do Antigravity pode emitir texto somente ao terminar; ausência de stdout durante esse intervalo não equivale a travamento. Na tela do celular, toque no cartão “Coordenador” para expandir os detalhes.

ADB confirmou as duas respostas e os cartões `completed` na tela Projects do S23 FE, além da notificação real do primeiro resultado no canal de agentes. O aparelho estava em Não perturbe, com interrupção suprimida; suas configurações não foram alteradas.

Teste real de indisponibilidade: após encerrar o preview identificado, um novo pedido recebeu HTTP 503 `orchestrator_offline`, sem criar conversa (contagem permaneceu em um). O preview foi reiniciado e o runtime voltou a informar `online: true`.

Evidências locais: `.local/live-progress-evidence.json`, `.local/smoke-final.json`, `.local/offline-evidence.json` e `.local/s23-completed.xml`. O preview está em execução em `http://127.0.0.1:1420/#projects`; fechar a aba não encerra esse processo.
