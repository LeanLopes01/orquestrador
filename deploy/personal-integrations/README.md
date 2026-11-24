# n8n do Jarvis: credenciais e proxy de leitura

Instância dedicada, ligada somente ao loopback do servidor (porta 5679). O volume
`jarvis-integrations_n8n_data` contém o banco e a chave de criptografia: preservar
ambos. Nunca usar `docker compose down -v` nem recriar a chave.

O n8n aqui só guarda e renova as autorizações. Cada conta tem um workflow
`Jarvis proxy <conta>`: webhook protegido pelo segredo do gateway, allowlist de rotas
somente leitura e uma credencial fixa. Quem decide o que consultar, e se a sessão
pode consultar, é o `jarvis-control` (`src/jarvis_control/personal.py`). Os workflows
são gerados por `deploy/n8n/build.py` no repositório do Jarvis; não editar no painel.

| Arquivo | Uso |
| --- | --- |
| `compose.yaml` | Serviço n8n, versão fixada por digest |
| `setup-n8n.sh` | Como `lean`: aplica o compose, cria o segredo, importa esqueletos de credencial ausentes e os workflows. Repetível; nunca sobrescreve credencial existente |
| `backup-n8n.sh` | Como `lean`: backup criptografado (gpg) e `--verify ARQUIVO` para testar a restauração |
| `publish-runtime.sh` | Com sudo: grava `/etc/jarvis/personal.env` e publica a release do runtime |
| `secrets/gateway.secret` | Segredo entre `jarvis-control` e n8n (0600). Não copiar para fora do servidor |

## 1. Abrir o painel pelo PC

```sh
ssh -N -L 5679:127.0.0.1:5679 user@your-server-ip
```

Abrir `http://localhost:5679` no navegador do PC e criar o proprietário (e-mail e
senha só seus). A porta local precisa ser **5679**: é a do callback registrado.

Callback OAuth (Google e Microsoft): `http://localhost:5679/rest/oauth2-credential/callback`.
Os dois aceitam `http://localhost` sem HTTPS. O login é feito no navegador do PC
pelo túnel; o n8n não fica exposto na internet. Renovações de token são
servidor→provedor e não usam o callback.

## 2. Google (contas A e B)

1. Em [console.cloud.google.com](https://console.cloud.google.com/), criar um projeto
   (ex.: "Jarvis pessoal") e ativar **Google Calendar API**, **Google Drive API** e
   **Gmail API**.
2. **Google Auth Platform → Branding/Audience:** tipo **External** para contas
   pessoais (`@gmail.com`); **Internal** só se as duas contas forem do mesmo Google
   Workspace. Adicionar as duas contas como usuários de teste.
3. **Data access (escopos):** `openid`, `email`, `calendar.readonly`,
   `drive.readonly`, `gmail.readonly`.
4. **Clients → Create client → Web application.** Redirect URI autorizado:
   `http://localhost:5679/rest/oauth2-credential/callback`. Guardar Client ID e
   Client secret (não colar no chat).
5. **Status do app:** em *Testing*, o refresh token desses escopos expira em
   7 dias e o Jarvis passará a mostrar "Autorização expirada". Para uso contínuo,
   colocar em *In production*; sem verificação do Google, o login mostra o aviso de
   app não verificado ("Avançado → continuar"), aceitável para uso próprio.
   Confirmar as regras atuais em
   [Google OAuth](https://developers.google.com/identity/protocols/oauth2) antes.
6. No n8n, abrir **Credentials → Jarvis Google A**: colar Client ID/secret,
   conferir o escopo (já preenchido; A inclui Gmail, B não) e clicar em
   **Connect my account**. Na tela do Google, escolher **a conta certa**. Repetir em
   **Jarvis Google B** com a outra conta. O mesmo cliente OAuth serve às duas.

Para mudar o Gmail de conta: no app, desmarcar Gmail na conta atual e marcar na
outra; no n8n, mover `https://www.googleapis.com/auth/gmail.readonly` do escopo de
uma credencial para a outra e reconectar ambas; depois rodar a verificação.

## 3. Outlook

1. Em [entra.microsoft.com](https://entra.microsoft.com/) → **App registrations →
   New registration**. Tipos de conta: incluir **contas pessoais Microsoft** se for
   Outlook.com/Hotmail; se for conta institucional, a organização pode exigir
   consentimento do administrador.
2. Redirect URI, plataforma **Web**: `http://localhost:5679/rest/oauth2-credential/callback`.
3. **Certificates & secrets → New client secret.** Guardar o *Value*.
4. **API permissions → Microsoft Graph → Delegated:** `openid`, `email`,
   `offline_access`, `User.Read`, `Mail.Read`. Nada de `Mail.Send` ou `ReadWrite`.
5. No n8n, **Jarvis Outlook**: colar Application (client) ID e o secret, **Connect
   my account**. As URLs usam `/common`; com conta só institucional, pode-se trocar
   `common` pelo ID do tenant.

## 4. Notion

1. Em [notion.so/profile/integrations](https://www.notion.so/profile/integrations),
   criar uma integração **interna** com capacidade **Read content** apenas.
2. Em cada base de tarefas: **⋯ → Connections → adicionar a integração**. O Jarvis
   lê somente as bases compartilhadas (até cinco) e descobre título, status, prazo e
   projeto pelos nomes e tipos reais das propriedades.
3. No n8n, **Jarvis Notion**: colar o *Internal Integration Secret*.

## 5. Verificar e ligar

Pelo PC: `scripts\verificar-conexoes-pessoais.cmd` (pede a senha sudo). Equivale a:

```sh
sudo jarvis-control personal-verify      # identidade + cada serviço selecionado
sudo jarvis-control personal-status      # estado, serviços verificados, identidade
sudo jarvis-control personal-runtime on  # só depois de conferir as identidades
```

Uma conta só fica **Conectada** quando a identidade e cada serviço selecionado
respondem. Se depois outra identidade aparecer na mesma credencial, a conta vai para
erro (`identity_changed`) e não é usada. Para recomeçar uma conta:
`sudo jarvis-control personal-mark CONTA disconnected`, reconectar no n8n e verificar.

## 6. Backup depois de autorizar

```sh
bash backup-n8n.sh                          # para o n8n ~10 s; pede a senha do gpg
bash backup-n8n.sh --verify backups/ARQUIVO # restaura num contêiner descartável
```

Guardar a senha do gpg fora do servidor. O procedimento foi testado em 24/10/2026
antes das credenciais reais (4 workflows, 5 credenciais decifradas na restauração).

## Desligar, pausar, revogar

- **Pausar** (app, tela Conexões): o Jarvis para de usar a conta; a autorização
  continua no provedor.
- **Desligar tudo:** `sudo jarvis-control personal-runtime off` (as ferramentas
  somem nas próximas sessões; chamadas em sessões abertas passam a ser recusadas).
- **Revogar de verdade:** remover o acesso no provedor
  ([Google](https://myaccount.google.com/connections),
  [Microsoft](https://account.live.com/consent/Manage), integração no Notion), apagar
  a credencial no n8n se não for reconectar, e marcar
  `sudo jarvis-control personal-mark CONTA disconnected`.

Referências: [Docker](https://docs.n8n.io/hosting/installation/docker/),
[credenciais Google](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service/),
[Microsoft](https://docs.n8n.io/integrations/builtin/credentials/microsoft/),
[criptografia](https://docs.n8n.io/hosting/configuration/configuration-examples/encryption-key/).
