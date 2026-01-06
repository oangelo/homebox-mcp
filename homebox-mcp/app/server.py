"""Homebox MCP Server - Main entry point."""

import logging
import sys

from fastmcp import FastMCP

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


if __name__ == "__main__":
    logger.info(f"Starting Homebox MCP Server on {config.server_host}:{config.server_port}")
    logger.info(f"Connecting to Homebox at: {config.homebox_url}")

    # Run the server with SSE transport for Home Assistant Ingress
    mcp.run(
        transport="sse",
        host=config.server_host,
        port=config.server_port,
    )
