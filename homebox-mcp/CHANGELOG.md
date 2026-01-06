# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
