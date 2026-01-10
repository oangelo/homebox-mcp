"""Homebox MCP Server - Main entry point."""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
import uvicorn

from config import config
from homebox_client import HomeboxClient
from tools import register_tools


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests using Bearer or Basic auth."""

    async def dispatch(self, request, call_next):
        # Skip auth for dashboard pages (protected by HA auth)
        if request.url.path in ["/", "/api/status"]:
            return await call_next(request)

        # If auth is disabled, allow all requests
        if not config.mcp_auth_enabled:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        # Log headers for debugging (only on /sse endpoint)
        if request.url.path == "/sse":
            logger.info(f"Auth request to {request.url.path}")
            logger.info(f"Authorization header: {auth_header[:50] if auth_header else 'MISSING'}...")

        if not auth_header:
            return Response(
                content="Missing Authorization header",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="MCP"'},
            )

        token = None
        
        # Try Bearer token first
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.debug("Using Bearer authentication")
        
        # Try Basic auth (client_id:client_secret)
        elif auth_header.startswith("Basic "):
            import base64
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                # Format is client_id:client_secret, we use client_secret as the token
                parts = decoded.split(":", 1)
                if len(parts) == 2:
                    # Use the secret (second part) as the token
                    token = parts[1]
                    logger.debug("Using Basic authentication (client_secret)")
                else:
                    token = decoded
                    logger.debug("Using Basic authentication (single value)")
            except Exception as e:
                logger.error(f"Failed to decode Basic auth: {e}")
        
        if not token:
            return Response(
                content="Invalid Authorization header format",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="MCP"'},
            )

        if token != config.mcp_auth_token:
            logger.warning(f"Invalid token received (length: {len(token)})")
            return Response(
                content="Invalid token",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="MCP"'},
            )

        logger.debug("Authentication successful")
        return await call_next(request)

# Configure logging
log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Homebox Inventory")

# Create the Homebox client
client = HomeboxClient(config)

# Register all tools
register_tools(mcp, client)

# Track connected clients
connected_clients: set[str] = set()
server_start_time = datetime.now()


@mcp.resource("homebox://info")
async def get_server_info() -> str:
    """Informações sobre o servidor MCP do Homebox."""
    return f"""# Homebox MCP Server

Servidor MCP conectado ao Homebox em: {config.homebox_url}

## Ferramentas Disponíveis

### Localizações
- homebox_list_locations - Lista todas as localizações
- homebox_get_location - Detalhes de uma localização
- homebox_create_location - Cria nova localização
- homebox_update_location - Atualiza localização
- homebox_delete_location - Remove localização

### Itens
- homebox_list_items - Lista itens (com filtros)
- homebox_get_item - Detalhes de um item
- homebox_search - Busca por itens
- homebox_create_item - Cria novo item
- homebox_update_item - Atualiza item
- homebox_move_item - Move item para outra localização
- homebox_delete_item - Remove item

### Labels
- homebox_list_labels - Lista todas as labels
- homebox_create_label - Cria nova label
- homebox_update_label - Atualiza label
- homebox_delete_label - Remove label

### Estatísticas
- homebox_get_statistics - Estatísticas do inventário
"""


async def get_status_data() -> dict[str, Any]:
    """Get status data for the dashboard."""
    status = {
        "homebox_url": config.homebox_url,
        "homebox_connected": False,
        "homebox_error": None,
        "locations_count": 0,
        "items_count": 0,
        "labels_count": 0,
        "server_uptime": str(datetime.now() - server_start_time).split(".")[0],
        "mcp_endpoint": "/sse",
        "mcp_auth_enabled": config.mcp_auth_enabled,
    }

    try:
        # Test connection and get counts
        locations = await client.get_locations()
        status["locations_count"] = len(locations)
        status["homebox_connected"] = True

        items = await client.get_items()
        status["items_count"] = len(items)

        labels = await client.get_labels()
        status["labels_count"] = len(labels)

    except Exception as e:
        status["homebox_connected"] = False
        status["homebox_error"] = str(e)
        logger.error(f"Error connecting to Homebox: {e}")

    return status


async def homepage(request):
    """Serve the status dashboard."""
    status = await get_status_data()

    connection_status = "✅ Conectado" if status["homebox_connected"] else "❌ Desconectado"
    connection_class = "connected" if status["homebox_connected"] else "disconnected"
    error_html = ""
    if status["homebox_error"]:
        error_html = f'<p class="error">Erro: {status["homebox_error"]}</p>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homebox MCP Server</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 2.5rem;
            font-weight: 300;
            color: #00d9ff;
            text-shadow: 0 0 30px rgba(0, 217, 255, 0.3);
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #8892b0;
            font-size: 1.1rem;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}
        .card-title {{
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #8892b0;
            margin-bottom: 12px;
        }}
        .card-value {{
            font-size: 2.5rem;
            font-weight: 600;
            color: #00d9ff;
        }}
        .card-value.connected {{
            color: #00ff88;
        }}
        .card-value.disconnected {{
            color: #ff4757;
        }}
        .status-card {{
            grid-column: 1 / -1;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }}
        .status-item {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .status-label {{
            font-size: 0.85rem;
            color: #8892b0;
        }}
        .status-value {{
            font-size: 1.1rem;
            color: #e8e8e8;
            word-break: break-all;
        }}
        .error {{
            background: rgba(255, 71, 87, 0.2);
            border: 1px solid rgba(255, 71, 87, 0.5);
            border-radius: 8px;
            padding: 12px;
            margin-top: 15px;
            color: #ff6b7a;
        }}
        .endpoint-box {{
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 12px;
            padding: 24px;
            margin-top: 30px;
        }}
        .endpoint-box h3 {{
            color: #00d9ff;
            margin-bottom: 20px;
            font-weight: 500;
        }}
        .endpoint-section {{
            margin-bottom: 10px;
        }}
        .endpoint-label {{
            font-size: 0.9rem;
            color: #e8e8e8;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .endpoint-url {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 12px 15px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.9rem;
            color: #00ff88;
            word-break: break-all;
        }}
        .endpoint-hint {{
            margin-top: 8px;
            color: #8892b0;
            font-size: 0.85rem;
        }}
        .info-box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 15px;
            font-size: 0.9rem;
            color: #e8e8e8;
        }}
        .info-box code {{
            background: rgba(0, 217, 255, 0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.85rem;
            color: #00d9ff;
        }}
        .tools-section {{
            margin-top: 30px;
        }}
        .tools-section h3 {{
            color: #00d9ff;
            margin-bottom: 20px;
            font-weight: 500;
        }}
        .tools-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
        }}
        .tool-item {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 15px;
        }}
        .tool-name {{
            font-family: 'Fira Code', 'Consolas', monospace;
            color: #00d9ff;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }}
        .tool-desc {{
            color: #8892b0;
            font-size: 0.85rem;
        }}
        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #8892b0;
            font-size: 0.9rem;
        }}
        footer a {{
            color: #00d9ff;
            text-decoration: none;
        }}
        footer a:hover {{
            text-decoration: underline;
        }}
        .refresh-btn {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.4);
            transition: transform 0.3s ease;
        }}
        .refresh-btn:hover {{
            transform: scale(1.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📦 Homebox MCP Server</h1>
            <p class="subtitle">Model Context Protocol para gerenciamento de inventário</p>
        </header>

        <div class="cards">
            <div class="card status-card">
                <div class="card-title">Status da Conexão</div>
                <div class="card-value {connection_class}">{connection_status}</div>
                {error_html}
                <div class="status-grid">
                    <div class="status-item">
                        <span class="status-label">Homebox URL</span>
                        <span class="status-value">{status["homebox_url"]}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Uptime do Servidor</span>
                        <span class="status-value">{status["server_uptime"]}</span>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">📍 Localizações</div>
                <div class="card-value">{status["locations_count"]}</div>
            </div>

            <div class="card">
                <div class="card-title">📦 Itens</div>
                <div class="card-value">{status["items_count"]}</div>
            </div>

            <div class="card">
                <div class="card-title">🏷️ Labels</div>
                <div class="card-value">{status["labels_count"]}</div>
            </div>
        </div>

        <div class="endpoint-box">
            <h3>🔌 Configuração do MCP</h3>
            
            <div class="endpoint-section">
                <div class="endpoint-label">🔐 Autenticação MCP</div>
                <div class="endpoint-url" style="color: {'#00ff88' if status['mcp_auth_enabled'] else '#ff6b7a'};">
                    {'🔒 ATIVADA' if status['mcp_auth_enabled'] else '🔓 DESATIVADA - Endpoint aberto'}
                </div>
            </div>
            
            <div class="info-box" style="margin-top: 20px; background: rgba(0, 217, 255, 0.1); border-color: rgba(0, 217, 255, 0.3);">
                <strong>🎲 Gerador de Token</strong>
                <p style="margin-top: 10px; color: #8892b0;">Gere um token seguro e copie para as configurações do addon:</p>
                <div style="margin: 15px 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <button onclick="generateToken()" style="background: #00d9ff; color: #1a1a2e; border: none; border-radius: 8px; padding: 12px 20px; cursor: pointer; font-weight: bold;">🎲 Gerar Token</button>
                    <input type="text" id="generatedToken" readonly placeholder="Clique em Gerar" style="flex: 1; min-width: 200px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 12px; color: #00ff88; font-family: monospace;">
                    <button onclick="copyToken()" style="background: rgba(255,255,255,0.1); color: #e8e8e8; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 12px 20px; cursor: pointer;">📋 Copiar</button>
                </div>
                <p style="color: #8892b0; font-size: 0.9rem;">Após copiar, cole nas <strong>configurações do addon</strong> → campo <code>mcp_auth_token</code></p>
            </div>
            
            {'<div class="info-box" style="margin-top: 15px; background: rgba(0, 255, 136, 0.1); border-color: rgba(0, 255, 136, 0.3);"><strong>✅ Token configurado</strong><p style="margin-top: 8px; color: #8892b0;">Use o mesmo token no Claude.ai → campo <strong>Segredo do Cliente OAuth</strong></p></div>' if status['mcp_auth_enabled'] and config.mcp_auth_token else ('<div class="info-box" style="margin-top: 15px; background: rgba(255, 200, 50, 0.1); border-color: rgba(255, 200, 50, 0.3);"><strong>⚠️ Token não configurado</strong><p style="margin-top: 8px; color: #8892b0;">Gere um token acima e configure em <code>mcp_auth_token</code> nas opções do addon.</p></div>' if status['mcp_auth_enabled'] else '<div class="info-box" style="margin-top: 15px; background: rgba(255, 107, 122, 0.1); border-color: rgba(255, 107, 122, 0.3);"><strong>⚠️ Autenticação desativada</strong><p style="margin-top: 8px; color: #8892b0;">Recomendado: ative <code>mcp_auth_enabled</code> e configure um token.</p></div>')}
            
            <div class="endpoint-section" style="margin-top: 20px;">
                <div class="endpoint-label">📍 Endereço Interno (para configurar Cloudflare Tunnel)</div>
                <div class="endpoint-url">http://homeassistant:8099</div>
                <p class="endpoint-hint">
                    Use este endereço no Cloudflare Tunnel → Additional hosts → Service
                </p>
            </div>
            
            <div class="endpoint-section" style="margin-top: 20px;">
                <div class="endpoint-label">🌐 Endereço para Claude.ai</div>
                <div class="endpoint-url">https://seu-dominio.com<span style="color: #00ff88;">/sse</span></div>
                <p class="endpoint-hint">
                    Após configurar o túnel, use o endereço do seu domínio + <strong>/sse</strong> no Claude.ai
                </p>
            </div>
            
            <div class="info-box" style="margin-top: 20px;">
                <strong>📋 Passos para configurar:</strong>
                <ol style="margin: 10px 0 0 20px; color: #8892b0;">
                    <li>Clique em <strong>🎲 Gerar Token</strong> acima e copie</li>
                    <li>Nas configurações do addon: ative <code>mcp_auth_enabled</code> e cole o token em <code>mcp_auth_token</code></li>
                    <li>Configure Cloudflare Tunnel → <code>http://homeassistant:8099</code></li>
                    <li>No Claude.ai:
                        <ul style="margin-top: 5px;">
                            <li>URL: <code>https://seu-dominio.com/sse</code></li>
                            <li>ID do Cliente OAuth: <code>mcp</code> (ou qualquer texto)</li>
                            <li>Segredo do Cliente OAuth: <strong>cole o token</strong></li>
                        </ul>
                    </li>
                </ol>
            </div>
        </div>

        <div class="tools-section">
            <h3>🛠️ Ferramentas Disponíveis</h3>
            <div class="tools-grid">
                <div class="tool-item">
                    <div class="tool-name">homebox_list_locations</div>
                    <div class="tool-desc">Lista todas as localizações</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_list_items</div>
                    <div class="tool-desc">Lista itens com filtros</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_search</div>
                    <div class="tool-desc">Busca por itens</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_create_item</div>
                    <div class="tool-desc">Cria novo item</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_move_item</div>
                    <div class="tool-desc">Move item para outra localização</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_list_labels</div>
                    <div class="tool-desc">Lista todas as labels</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_create_location</div>
                    <div class="tool-desc">Cria nova localização</div>
                </div>
                <div class="tool-item">
                    <div class="tool-name">homebox_get_statistics</div>
                    <div class="tool-desc">Estatísticas do inventário</div>
                </div>
            </div>
        </div>

        <footer>
            <p>
                <a href="https://github.com/oangelo/homebox-mcp" target="_blank">GitHub</a> · 
                Desenvolvido para uso com <a href="https://github.com/Oddiesea/homebox-ingress-ha-addon" target="_blank">Homebox</a>
            </p>
        </footer>
    </div>

    <button class="refresh-btn" onclick="location.reload()" title="Atualizar">↻</button>

    <script>
        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
        
        // Generate a secure random token (client-side)
        function generateToken() {{
            const array = new Uint8Array(32);
            crypto.getRandomValues(array);
            const token = Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
            document.getElementById('generatedToken').value = token;
        }}
        
        // Copy token to clipboard
        function copyToken() {{
            const input = document.getElementById('generatedToken');
            if (!input.value) {{
                alert('Gere um token primeiro!');
                return;
            }}
            navigator.clipboard.writeText(input.value).then(() => {{
                alert('Token copiado!\\n\\nAgora cole nas configurações do addon:\\n→ mcp_auth_token\\n\\nE também no Claude.ai:\\n→ Segredo do Cliente OAuth');
            }});
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(html)


async def api_status(request):
    """API endpoint for status data."""
    status = await get_status_data()
    return JSONResponse(status)


# Create custom Starlette app with MCP mounted and auth middleware
app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/api/status", api_status),
        Mount("/", app=mcp.http_app(transport="sse")),
    ],
    middleware=[
        Middleware(BearerAuthMiddleware),
    ],
)


if __name__ == "__main__":
    logger.info(f"Starting Homebox MCP Server on {config.server_host}:{config.server_port}")
    logger.info(f"Connecting to Homebox at: {config.homebox_url}")
    logger.info(f"Dashboard available at: http://{config.server_host}:{config.server_port}/")
    logger.info(f"MCP SSE endpoint at: http://{config.server_host}:{config.server_port}/sse")

    if config.mcp_auth_enabled:
        logger.info("MCP Authentication: ENABLED - Bearer token required")
    else:
        logger.warning("MCP Authentication: DISABLED - Endpoint is open to anyone")

    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level=config.log_level.lower(),
    )
