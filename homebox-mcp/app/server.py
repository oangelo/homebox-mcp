"""Homebox MCP Server - Main entry point."""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from config import config
from homebox_client import HomeboxClient
from tools import register_tools

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
            padding: 20px;
            margin-top: 30px;
        }}
        .endpoint-box h3 {{
            color: #00d9ff;
            margin-bottom: 15px;
            font-weight: 500;
        }}
        .endpoint-url {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 15px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.95rem;
            color: #00ff88;
            word-break: break-all;
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
            <h3>🔌 Endpoint MCP (SSE)</h3>
            <div class="endpoint-url">{config.homebox_url.replace("http://", "https://").replace(":7745", "")}/sse</div>
            <p style="margin-top: 10px; color: #8892b0; font-size: 0.9rem;">
                Use esta URL para conectar o Claude.ai ou Claude Desktop ao MCP.
            </p>
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
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
    return HTMLResponse(html)


async def api_status(request):
    """API endpoint for status data."""
    status = await get_status_data()
    return JSONResponse(status)


# Create custom Starlette app with MCP mounted
app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/api/status", api_status),
        Mount("/", app=mcp.http_app(transport="sse")),
    ]
)


if __name__ == "__main__":
    logger.info(f"Starting Homebox MCP Server on {config.server_host}:{config.server_port}")
    logger.info(f"Connecting to Homebox at: {config.homebox_url}")
    logger.info(f"Dashboard available at: http://{config.server_host}:{config.server_port}/")
    logger.info(f"MCP SSE endpoint at: http://{config.server_host}:{config.server_port}/sse")

    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level=config.log_level.lower(),
    )
