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

| Opção              | Descrição                                         | Obrigatório |
| ------------------ | ------------------------------------------------- | ----------- |
| `homebox_url`      | URL do servidor Homebox                           | Sim         |
| `homebox_token`    | API Token do Homebox                              | Sim         |
| `mcp_auth_enabled` | Ativar autenticação no endpoint MCP               | Não         |
| `mcp_auth_token`   | Token Bearer para autenticação MCP                | Não         |
| `log_level`        | Nível de log (trace, debug, info, warning, error) | Não         |

### Exemplo de Configuração

```yaml
homebox_url: "http://dac2a4a9-homebox:7745"
homebox_token: "SEU_TOKEN_API_HOMEBOX"
mcp_auth_enabled: false
mcp_auth_token: ""
log_level: "info"
```

### Criando o API Token do Homebox

1. Acesse o Homebox
2. Vá em **Profile** (ícone de usuário)
3. Clique em **API Tokens**
4. Clique em **Create Token**
5. Copie o token gerado

## Autenticação MCP (OAuth)

O addon suporta autenticação Bearer token opcional para proteger o endpoint MCP.

### Recomendação

1. **Primeiro**, teste a conexão com `mcp_auth_enabled: false`
2. **Depois** que tudo funcionar, ative a autenticação:
   - Defina um token seguro em `mcp_auth_token`
   - Ative `mcp_auth_enabled: true`

### Configuração com Autenticação

```yaml
homebox_url: "http://dac2a4a9-homebox:7745"
homebox_token: "SEU_TOKEN_API_HOMEBOX"
mcp_auth_enabled: true
mcp_auth_token: "MEU_TOKEN_SEGURO_PARA_MCP"
log_level: "info"
```

### Configuração no Claude.ai

Quando a autenticação está ativada, configure no Claude.ai:

| Campo | Valor |
|-------|-------|
| **URL do servidor** | `https://seu-dominio.com/sse` |
| **ID do Cliente OAuth** | *Deixe em branco* |
| **Segredo do Cliente OAuth** | `MEU_TOKEN_SEGURO_PARA_MCP` ← Cole seu token aqui |

**Importante**: O token vai no campo **Segredo do Cliente OAuth**, não no ID do Cliente.

### Gerando um Token Seguro

O dashboard do addon tem um botão para gerar tokens seguros automaticamente:

1. Acesse a página web do addon
2. Na seção "Gerar Token Seguro", clique em **Gerar**
3. Clique em **Copiar**
4. Cole o token em `mcp_auth_token` nas configurações do addon
5. Cole o mesmo token no campo **Segredo do Cliente OAuth** no Claude.ai

### Addon Homebox Recomendado

Este MCP foi desenvolvido para funcionar com o addon
[homebox-ingress-ha-addon](https://github.com/Oddiesea/homebox-ingress-ha-addon).

Para instalar:

1. Adicione o repositório: `https://github.com/Oddiesea/homebox-ingress-ha-addon`
2. Instale o addon **Homebox**
3. Inicie e configure seu inventário

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

O servidor MCP expõe um endpoint SSE (Server-Sent Events) na porta 8099.

### Acesso Local (Rede Interna)

Na mesma rede do Home Assistant:

```
http://homeassistant.local:8099/sse
```

Ou pelo IP:

```
http://192.168.X.X:8099/sse
```

### Acesso Externo via Cloudflare Tunnel (Recomendado)

Para expor o MCP na internet de forma segura (necessário para Claude.ai web),
use o [addon Cloudflared](https://github.com/homeassistant-apps/app-cloudflared).

#### 1. Instalar o addon Cloudflared

1. Adicione o repositório ao Home Assistant:
   ```
   https://github.com/homeassistant-apps/app-cloudflared
   ```
2. Instale o addon **Cloudflared**

#### 2. Configurar no Cloudflare

1. Acesse [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
2. Vá em **Networks** → **Tunnels** → **Create a tunnel**
3. Escolha **Cloudflared** e dê um nome ao tunnel
4. Copie o token gerado

#### 3. Configurar o addon Cloudflared

Configure o addon para expor a porta 8099 do MCP:

```yaml
additional_hosts:
  - hostname: mcp.seudominio.com
    service: http://homeassistant:8099
```

Ou se não tiver domínio próprio, use um subdomínio gratuito do Cloudflare:

```yaml
additional_hosts:
  - hostname: mcp-homebox.seudominio.workers.dev
    service: http://homeassistant:8099
```

#### 4. URL Final para Claude.ai

Após configurado, use no Claude.ai:

```
https://mcp.seudominio.com/sse
```

### Acesso via Ingress (alternativa)

O Ingress do HA requer autenticação por sessão, o que dificulta acesso externo.
Use apenas para acesso local via navegador:

```
https://seu-home-assistant/api/hassio_ingress/<ingress_token>/sse
```

### Configurando no Claude Desktop

Adicione ao seu `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "homebox": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.seudominio.com/sse"]
    }
  }
}
```

### Configurando no Claude.ai Web (Experimental)

1. Acesse as configurações de MCP no Claude.ai
2. Adicione um novo servidor MCP
3. Cole a URL: `https://mcp.seudominio.com/sse`
4. OAuth: deixe desabilitado (não é necessário)

### Testando a Conexão

#### Via terminal (curl)

```bash
# Teste local
curl -N "http://homeassistant.local:8099/sse"

# Teste via Cloudflare Tunnel
curl -N "https://mcp.seudominio.com/sse"
```

Se funcionar, você verá:

```
event: endpoint
data: /messages/?session_id=...
```

#### Via MCP Inspector

```bash
npx @anthropic/mcp-inspector https://mcp.seudominio.com/sse
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
