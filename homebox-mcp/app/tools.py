"""MCP Tools for Homebox inventory management."""

from typing import Any

from fastmcp import FastMCP

from homebox_client import HomeboxClient


def register_tools(mcp: FastMCP, client: HomeboxClient) -> None:
    """Register all Homebox tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
        client: The Homebox API client.
    """

    # =========================================================================
    # Location Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_locations() -> list[dict[str, Any]]:
        """Lista todas as localizações do inventário.

        Retorna a lista completa de localizações cadastradas no Homebox,
        incluindo informações de hierarquia (parent_id) para localizações
        aninhadas.

        Returns:
            Lista de localizações com id, name, description e parent_id.
        """
        locations = await client.get_locations()
        return [
            {
                "id": loc.get("id"),
                "name": loc.get("name"),
                "description": loc.get("description", ""),
                "parent_id": loc.get("parent", {}).get("id") if loc.get("parent") else None,
                "item_count": loc.get("itemCount", 0),
            }
            for loc in locations
        ]

    @mcp.tool()
    async def homebox_get_location(location_id: str) -> dict[str, Any]:
        """Obtém detalhes de uma localização específica.

        Args:
            location_id: ID (UUID) da localização.

        Returns:
            Detalhes completos da localização.
        """
        return await client.get_location(location_id)

    @mcp.tool()
    async def homebox_create_location(
        name: str,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Cria uma nova localização no inventário.

        Use esta ferramenta para criar novos locais onde itens podem ser
        armazenados, como cômodos, armários, gavetas, etc.

        Args:
            name: Nome da localização (obrigatório).
            description: Descrição opcional da localização.
            parent_id: ID da localização pai para criar hierarquia.
                       Por exemplo, "Gaveta 1" pode ser filha de "Cômoda".

        Returns:
            Localização criada com todos os campos.
        """
        return await client.create_location(name, description, parent_id)

    @mcp.tool()
    async def homebox_update_location(
        location_id: str,
        name: str | None = None,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Atualiza uma localização existente.

        Args:
            location_id: ID (UUID) da localização a atualizar.
            name: Novo nome (opcional).
            description: Nova descrição (opcional).
            parent_id: Novo ID da localização pai (opcional).

        Returns:
            Localização atualizada.
        """
        return await client.update_location(location_id, name, description, parent_id)

    @mcp.tool()
    async def homebox_delete_location(location_id: str) -> str:
        """Remove uma localização do inventário.

        ATENÇÃO: A localização não pode ter itens ou sub-localizações.

        Args:
            location_id: ID (UUID) da localização a remover.

        Returns:
            Mensagem de confirmação.
        """
        await client.delete_location(location_id)
        return f"Localização {location_id} removida com sucesso."

    # =========================================================================
    # Item Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_items(
        location_id: str | None = None,
        label_id: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista itens do inventário com filtros opcionais.

        Use esta ferramenta para obter uma lista de itens. Você pode filtrar
        por localização, label ou fazer uma busca textual.

        Args:
            location_id: Filtrar por localização específica (UUID).
            label_id: Filtrar por label específica (UUID).
            search: Termo de busca no nome/descrição dos itens.

        Returns:
            Lista de itens com id, name, location, quantity, etc.
        """
        items = await client.get_items(location_id, label_id, search)
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "location": {
                    "id": item.get("location", {}).get("id"),
                    "name": item.get("location", {}).get("name"),
                },
                "labels": [
                    {"id": label.get("id"), "name": label.get("name")}
                    for label in item.get("labels", [])
                ],
                "insured": item.get("insured", False),
                "archived": item.get("archived", False),
            }
            for item in items
        ]

    @mcp.tool()
    async def homebox_get_item(item_id: str) -> dict[str, Any]:
        """Obtém detalhes completos de um item específico.

        Use esta ferramenta quando precisar de todas as informações de um
        item, incluindo campos como número de série, fabricante, preço, etc.

        Args:
            item_id: ID (UUID) do item.

        Returns:
            Detalhes completos do item incluindo todos os campos.
        """
        return await client.get_item(item_id)

    @mcp.tool()
    async def homebox_search(query: str) -> list[dict[str, Any]]:
        """Busca flexível por itens no inventário.

        Realiza uma busca textual em nomes e descrições de itens.

        Args:
            query: Termo de busca (nome, descrição, etc).

        Returns:
            Lista de itens que correspondem à busca.
        """
        items = await client.get_items(search=query)
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "location": {
                    "id": item.get("location", {}).get("id"),
                    "name": item.get("location", {}).get("name"),
                },
            }
            for item in items
        ]

    @mcp.tool()
    async def homebox_create_item(
        name: str,
        location_id: str,
        description: str | None = None,
        quantity: int = 1,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Cria um novo item no inventário.

        Use esta ferramenta para adicionar novos itens ao inventário.

        Args:
            name: Nome do item (obrigatório).
            location_id: ID (UUID) da localização onde o item será armazenado.
            description: Descrição do item (opcional).
            quantity: Quantidade do item (padrão: 1).
            labels: Lista de IDs (UUIDs) de labels a associar ao item.

        Returns:
            Item criado com todos os campos.
        """
        return await client.create_item(name, location_id, description, quantity, labels)

    @mcp.tool()
    async def homebox_update_item(
        item_id: str,
        name: str | None = None,
        description: str | None = None,
        quantity: int | None = None,
        location_id: str | None = None,
        labels: list[str] | None = None,
        insured: bool | None = None,
        archived: bool | None = None,
        asset_id: str | None = None,
        serial_number: str | None = None,
        model_number: str | None = None,
        manufacturer: str | None = None,
        purchase_price: float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Atualiza campos de um item existente.

        Use esta ferramenta para modificar qualquer campo de um item.
        Apenas os campos fornecidos serão atualizados.

        Args:
            item_id: ID (UUID) do item a atualizar (obrigatório).
            name: Novo nome do item.
            description: Nova descrição.
            quantity: Nova quantidade.
            location_id: Novo ID da localização (move o item).
            labels: Nova lista de IDs de labels.
            insured: Status de seguro (true/false).
            archived: Status de arquivado (true/false).
            asset_id: ID do ativo/patrimônio.
            serial_number: Número de série.
            model_number: Número do modelo.
            manufacturer: Fabricante.
            purchase_price: Preço de compra.
            notes: Notas/observações.

        Returns:
            Item atualizado com todos os campos.
        """
        return await client.update_item(
            item_id=item_id,
            name=name,
            description=description,
            quantity=quantity,
            location_id=location_id,
            labels=labels,
            insured=insured,
            archived=archived,
            asset_id=asset_id,
            serial_number=serial_number,
            model_number=model_number,
            manufacturer=manufacturer,
            purchase_price=purchase_price,
            notes=notes,
        )

    @mcp.tool()
    async def homebox_move_item(item_id: str, location_id: str) -> dict[str, Any]:
        """Move um item para outra localização.

        Atalho conveniente para mudar a localização de um item.

        Args:
            item_id: ID (UUID) do item a mover.
            location_id: ID (UUID) da nova localização.

        Returns:
            Item atualizado com a nova localização.
        """
        return await client.move_item(item_id, location_id)

    @mcp.tool()
    async def homebox_delete_item(item_id: str) -> str:
        """Remove um item do inventário.

        ATENÇÃO: Esta ação é permanente.

        Args:
            item_id: ID (UUID) do item a remover.

        Returns:
            Mensagem de confirmação.
        """
        await client.delete_item(item_id)
        return f"Item {item_id} removido com sucesso."

    # =========================================================================
    # Label Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_labels() -> list[dict[str, Any]]:
        """Lista todas as labels/etiquetas do inventário.

        Labels são usadas para categorizar e organizar itens.

        Returns:
            Lista de labels com id, name, description e color.
        """
        labels = await client.get_labels()
        return [
            {
                "id": label.get("id"),
                "name": label.get("name"),
                "description": label.get("description", ""),
                "color": label.get("color", ""),
                "item_count": label.get("itemCount", 0),
            }
            for label in labels
        ]

    @mcp.tool()
    async def homebox_create_label(
        name: str,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Cria uma nova label/etiqueta.

        Labels são úteis para categorizar itens (ex: "Eletrônicos",
        "Ferramentas", "Documentos").

        Args:
            name: Nome da label (obrigatório).
            description: Descrição da label (opcional).
            color: Cor em formato hexadecimal (ex: "#FF5733").

        Returns:
            Label criada com todos os campos.
        """
        return await client.create_label(name, description, color)

    @mcp.tool()
    async def homebox_update_label(
        label_id: str,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Atualiza uma label existente.

        Args:
            label_id: ID (UUID) da label a atualizar.
            name: Novo nome (opcional).
            description: Nova descrição (opcional).
            color: Nova cor em formato hexadecimal (opcional).

        Returns:
            Label atualizada.
        """
        return await client.update_label(label_id, name, description, color)

    @mcp.tool()
    async def homebox_delete_label(label_id: str) -> str:
        """Remove uma label do inventário.

        Os itens associados não serão removidos, apenas perderão a label.

        Args:
            label_id: ID (UUID) da label a remover.

        Returns:
            Mensagem de confirmação.
        """
        await client.delete_label(label_id)
        return f"Label {label_id} removida com sucesso."

    # =========================================================================
    # Statistics Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_get_statistics() -> dict[str, Any]:
        """Obtém estatísticas do inventário.

        Retorna contagens e totais úteis para ter uma visão geral do
        inventário.

        Returns:
            Estatísticas incluindo contagem de itens, localizações,
            labels e valor total.
        """
        return await client.get_statistics()
