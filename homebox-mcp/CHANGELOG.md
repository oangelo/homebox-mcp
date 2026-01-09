# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.2.2] - 2026-01-09

### Alterado

- Campo `homebox_username` renomeado para `homebox_email` (Homebox usa email para login)
- Dashboard agora mostra instruções claras para configuração do Cloudflare Tunnel
- Endereço interno (`http://homeassistant:8099`) exibido para configuração do túnel
- Instruções sobre adicionar `/sse` ao endereço do túnel para Claude.ai

### Corrigido

- Correção da API FastMCP: `sse_app()` → `http_app(transport="sse")`

## [0.2.1] - 2026-01-06

### Adicionado

- Opção de autenticação via Token ou Credenciais (email/senha)
- Novo campo `auth_method` nas configurações (credentials | token)
- Novo campo `homebox_token` para autenticação via token

## [0.2.0] - 2026-01-06

### Adicionado

- Dashboard web de status na página inicial do addon
- Exibe status de conexão com o Homebox
- Mostra contagem de localizações, itens e labels
- Exibe uptime do servidor
- Mostra endpoint MCP para fácil configuração
- Lista de ferramentas disponíveis no dashboard
- API endpoint `/api/status` para consulta programática
- Auto-refresh a cada 30 segundos

## [0.1.1] - 2026-01-06

### Adicionado

- Porta 8099 exposta diretamente para facilitar conexão externa
- Suporte a conexão direta via `http://SEU_IP:8099/sse`

### Corrigido

- Removido parâmetro `description` deprecated do FastMCP
- Removido pinning de versões de pacotes Alpine

## [0.1.0] - 2026-01-06

### Adicionado

- Servidor MCP inicial com suporte SSE
- Integração com API do Homebox v1
- Ferramentas para gerenciamento de localizações:
  - `homebox_list_locations`
  - `homebox_get_location`
  - `homebox_create_location`
  - `homebox_update_location`
  - `homebox_delete_location`
- Ferramentas para gerenciamento de itens:
  - `homebox_list_items`
  - `homebox_get_item`
  - `homebox_search`
  - `homebox_create_item`
  - `homebox_update_item`
  - `homebox_move_item`
  - `homebox_delete_item`
- Ferramentas para gerenciamento de labels:
  - `homebox_list_labels`
  - `homebox_create_label`
  - `homebox_update_label`
  - `homebox_delete_label`
- Ferramenta de estatísticas:
  - `homebox_get_statistics`
- Autenticação automática com renovação de token
- Configuração via opções do addon Home Assistant
- Suporte a arquiteturas: amd64, aarch64, armv7
