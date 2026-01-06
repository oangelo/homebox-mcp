# Home Assistant Add-on: Homebox MCP Server

## Sobre

Este addon expõe um servidor MCP (Model Context Protocol) para gerenciar o
inventário do Homebox. Ele permite que assistentes de IA (como Claude) listem,
criem, movam e busquem itens no seu inventário doméstico.

## Instalação

1. Adicione este repositório às suas fontes de add-ons do Home Assistant
2. Instale o add-on "Homebox MCP Server"
3. Configure as credenciais do Homebox
4. Inicie o add-on

## Configuração

### Opções

| Opção | Descrição | Obrigatório |
|-------|-----------|-------------|
| `homebox_url` | URL do servidor Homebox | Sim |
| `homebox_username` | Usuário do Homebox | Sim |
| `homebox_password` | Senha do Homebox | Sim |
| `log_level` | Nível de log (trace, debug, info, warning, error) | Não |

### Exemplo de Configuração

```yaml
homebox_url: "http://homeassistant.local:7745"
homebox_username: "admin@example.com"
homebox_password: "sua_senha_aqui"
log_level: "info"
```

### Encontrando a URL do Homebox

Se você tem o Homebox rodando como addon do Home Assistant:

1. Vá em **Configurações** → **Add-ons**
2. Clique no addon Homebox
3. Na aba "Informações", encontre o hostname interno
4. A URL será algo como: `http://dac2a4a9-homebox:7745`

Se o Homebox está rodando externamente:
- Use o IP ou hostname do servidor: `http://192.168.1.100:7745`

## Ferramentas MCP Disponíveis

### Localizações

- **homebox_list_locations**: Lista todas as localizações do inventário
- **homebox_get_location**: Obtém detalhes de uma localização
- **homebox_create_location**: Cria uma nova localização
- **homebox_update_location**: Atualiza uma localização
- **homebox_delete_location**: Remove uma localização

### Itens

- **homebox_list_items**: Lista itens com filtros opcionais
- **homebox_get_item**: Obtém detalhes completos de um item
- **homebox_search**: Busca flexível por itens
- **homebox_create_item**: Cria um novo item
- **homebox_update_item**: Atualiza campos de um item
- **homebox_move_item**: Move um item para outra localização
- **homebox_delete_item**: Remove um item

### Labels

- **homebox_list_labels**: Lista todas as labels
- **homebox_create_label**: Cria uma nova label
- **homebox_update_label**: Atualiza uma label
- **homebox_delete_label**: Remove uma label

### Estatísticas

- **homebox_get_statistics**: Obtém estatísticas do inventário

## Conectando ao Servidor MCP

### URL do Endpoint

O servidor MCP fica disponível via Ingress do Home Assistant:

```
https://seu-home-assistant/api/hassio_ingress/<ingress_token>/sse
```

Você pode encontrar a URL completa:

1. Vá em **Configurações** → **Add-ons** → **Homebox MCP Server**
2. Na aba lateral, clique em "ABRIR INTERFACE WEB"
3. Copie a URL da barra de endereços

### Configurando no Claude Desktop

Adicione ao seu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "homebox": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://seu-home-assistant/api/hassio_ingress/TOKEN/sse"
      ]
    }
  }
}
```

### Testando com MCP Inspector

```bash
npx @anthropic/mcp-inspector https://seu-home-assistant/api/hassio_ingress/TOKEN/sse
```

## Exemplos de Uso

### Listar todos os itens

```
Usuário: Liste todos os itens do meu inventário
Claude: [usa homebox_list_items]
```

### Criar um novo item

```
Usuário: Adicione um "Furadeira Bosch" na garagem
Claude: [usa homebox_list_locations para encontrar "Garagem"]
Claude: [usa homebox_create_item com name="Furadeira Bosch" e location_id=...]
```

### Mover um item

```
Usuário: Mova a furadeira para o escritório
Claude: [usa homebox_search para encontrar "furadeira"]
Claude: [usa homebox_list_locations para encontrar "Escritório"]
Claude: [usa homebox_move_item]
```

### Buscar itens

```
Usuário: Onde estão minhas ferramentas?
Claude: [usa homebox_search com query="ferramenta"]
```

## Solução de Problemas

### Erro de Autenticação

Verifique se:
- O username e password estão corretos
- O usuário existe no Homebox
- O Homebox está acessível na URL configurada

### Erro de Conexão

Verifique se:
- A URL do Homebox está correta
- O addon Homebox está rodando
- Não há firewall bloqueando a conexão

### Logs

Para ver os logs do addon:

1. Vá em **Configurações** → **Add-ons** → **Homebox MCP Server**
2. Clique na aba "Log"

Ou via linha de comando:

```bash
ha addons logs homebox-mcp
```

## Suporte

Para problemas ou sugestões:
- Abra uma issue no [repositório GitHub](https://github.com/oangelo/homebox-mcp)
