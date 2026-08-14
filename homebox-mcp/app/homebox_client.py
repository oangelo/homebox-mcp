"""HTTP client for the Homebox API.

Homebox v0.26.0 introduced a breaking API change ("entity merge"): the
separate ``/items`` and ``/locations`` endpoints were removed and replaced by a
unified ``/entities`` API, and ``/labels`` became ``/tags``. See:
https://homebox.software/en/advanced/entity-merge-upgrade/

To keep working against every Homebox version, this client auto-detects which
API the server speaks on first use and transparently routes each call to the
right endpoints, normalizing the new "entity" objects back to the item/location
shape the rest of the addon (and the MCP tools) already expect.
"""

import logging
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)

# Number of entities to request per page when listing. Home inventories are
# small, so a single large page avoids paginating in the common case.
_ENTITIES_PAGE_SIZE = 10000


class HomeboxClient:
    """Async HTTP client for interacting with the Homebox API."""

    def __init__(self, config: Config):
        """Initialize the Homebox client.

        Args:
            config: Configuration object with Homebox connection details.
        """
        self.config = config
        self.base_url = config.api_base_url
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None
        # API flavor: None = not detected yet, "entities" = v0.26.0+, "legacy" = older.
        self._api_mode: str | None = None
        # Cached entity-type ids (entities mode only), resolved lazily.
        self._item_type_id: str | None = None
        self._location_type_id: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if self._token is None:
            if not self.config.homebox_token:
                raise ValueError("Homebox API token not configured. Please set homebox_token in addon settings.")
            self._token = self.config.homebox_token
            logger.info("Using configured API token for Homebox authentication")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for authenticated requests."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request to the Homebox API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (without base URL).
            **kwargs: Additional arguments to pass to httpx.

        Returns:
            JSON response data.
        """
        await self._ensure_authenticated()
        client = await self._get_client()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        response = await client.request(method, url, headers=headers, **kwargs)

        # Handle authentication errors
        if response.status_code == 401:
            logger.error("Authentication failed. Please check your Homebox API token.")
            raise ValueError("Invalid or expired Homebox API token. Please generate a new token in Homebox settings.")

        response.raise_for_status()

        if response.status_code == 204:
            return None

        return response.json()

    # =========================================================================
    # API mode detection (legacy /items vs new /entities)
    # =========================================================================

    async def _get_api_mode(self) -> str:
        """Detect which Homebox API flavor the server speaks.

        Probes the ``/entities`` endpoint introduced in Homebox v0.26.0. If it
        exists, the modern unified API is used; otherwise we fall back to the
        legacy ``/items`` / ``/locations`` / ``/labels`` endpoints.

        Returns:
            Either "entities" (v0.26.0+) or "legacy".
        """
        if self._api_mode is None:
            await self._ensure_authenticated()
            client = await self._get_client()
            url = f"{self.base_url}/entities"
            response = await client.request(
                "GET", url, headers=self._get_headers(), params={"pageSize": 1}
            )

            if response.status_code == 401:
                raise ValueError(
                    "Invalid or expired Homebox API token. Please generate a new token in Homebox settings."
                )

            if response.status_code == 404:
                self._api_mode = "legacy"
            else:
                response.raise_for_status()
                self._api_mode = "entities"

            logger.info("Detected Homebox API mode: %s", self._api_mode)

        return self._api_mode

    async def _get_entity_type_id(self, is_location: bool) -> str | None:
        """Resolve an entity-type id for items or locations (entities mode).

        In the unified model, whether an entity behaves as a container
        (location) or a regular item is determined by its entity type's
        ``isLocation`` flag. Homebox seeds default types on migration; we pick
        the first matching one and cache it.

        Args:
            is_location: True to resolve a location type, False for an item type.

        Returns:
            The entity-type id, or None if none could be resolved (the server
            may then apply its own default).
        """
        cached = self._location_type_id if is_location else self._item_type_id
        if cached is not None:
            return cached

        types = await self._request("GET", "/entity-types")
        match = next(
            (t for t in (types or []) if bool(t.get("isLocation")) == is_location),
            None,
        )
        type_id = match.get("id") if match else None

        if is_location:
            self._location_type_id = type_id
        else:
            self._item_type_id = type_id

        if type_id is None:
            logger.warning(
                "No entity type found with isLocation=%s; the server default will be used.",
                is_location,
            )
        return type_id

    # =========================================================================
    # Normalization helpers (entities mode -> legacy item/location shape)
    # =========================================================================

    @staticmethod
    def _normalize_item(entity: dict[str, Any]) -> dict[str, Any]:
        """Map an entity object to the legacy item shape expected by the tools."""
        parent = entity.get("parent") or {}
        tags = entity.get("tags") or []
        normalized = {
            "id": entity.get("id"),
            "name": entity.get("name"),
            "description": entity.get("description", ""),
            "quantity": entity.get("quantity", 1),
            "location": {"id": parent.get("id"), "name": parent.get("name")},
            "labels": [{"id": t.get("id"), "name": t.get("name")} for t in tags],
            "insured": entity.get("insured", False),
            "archived": entity.get("archived", False),
        }
        # Preserve extra detail fields (serial number, price, etc.) for get_item.
        for key in (
            "assetId",
            "serialNumber",
            "modelNumber",
            "manufacturer",
            "purchasePrice",
            "notes",
            "createdAt",
            "updatedAt",
            "imageId",
        ):
            if key in entity:
                normalized[key] = entity[key]
        return normalized

    async def _list_entities(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """List entities (entities mode), returning the raw item array."""
        query: dict[str, Any] = {"pageSize": _ENTITIES_PAGE_SIZE}
        query.update(params)
        response = await self._request("GET", "/entities", params=query)
        if isinstance(response, dict) and "items" in response:
            return response["items"]
        return response or []

    # =========================================================================
    # Locations
    # =========================================================================

    async def get_locations(self) -> list[dict[str, Any]]:
        """Get all locations.

        Returns:
            List of location objects.
        """
        if await self._get_api_mode() == "legacy":
            return await self._request("GET", "/locations")

        # The plain (unfiltered) entities list excludes locations entirely
        # by default on the Homebox server side, for backward compatibility
        # with the old /items endpoint's behavior — there is no client-side
        # way to recover them from that call. ?isLocation=true is required
        # to get location entities back (and is also what makes the server
        # populate itemCount on each result).
        return await self._list_entities({"isLocation": True})

    async def get_location_tree(self) -> list[dict[str, Any]]:
        """Get the complete location hierarchy as a nested tree.

        Returns:
            List of root locations (no parent), each with a nested
            ``children`` array. Every node has id, name, description,
            item_count, children.
        """
        locations = await self.get_locations()

        if await self._get_api_mode() == "legacy":
            # The legacy /locations list doesn't include parent info (a
            # long-standing Homebox limitation), so each location's full
            # record must be fetched individually to learn its parent.
            parent_of: dict[str, str | None] = {}
            for loc in locations:
                detail = await self.get_location(loc["id"])
                parent = detail.get("parent")
                parent_of[loc["id"]] = parent.get("id") if parent else None
        else:
            # Entities mode: get_locations() already eager-loads each
            # entity's direct parent, no extra requests needed.
            parent_of = {
                loc["id"]: (loc.get("parent") or {}).get("id") for loc in locations
            }

        nodes: dict[str, dict[str, Any]] = {
            loc["id"]: {
                "id": loc["id"],
                "name": loc.get("name"),
                "description": loc.get("description", ""),
                "item_count": loc.get("itemCount", 0),
                "children": [],
            }
            for loc in locations
        }

        roots: list[dict[str, Any]] = []
        for loc_id, node in nodes.items():
            parent_id = parent_of.get(loc_id)
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    async def get_location(self, location_id: str) -> dict[str, Any]:
        """Get a specific location by ID.

        Args:
            location_id: The location UUID.

        Returns:
            Location object (with parent/children when available).
        """
        if await self._get_api_mode() == "legacy":
            return await self._request("GET", f"/locations/{location_id}")

        # EntityOut already exposes parent, children and itemCount.
        return await self._request("GET", f"/entities/{location_id}")

    async def create_location(
        self,
        name: str,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new location.

        Args:
            name: Location name.
            description: Optional description.
            parent_id: Optional parent location ID for hierarchy.

        Returns:
            Created location object.
        """
        data: dict[str, Any] = {"name": name}
        if description:
            data["description"] = description
        if parent_id:
            data["parentId"] = parent_id

        if await self._get_api_mode() == "legacy":
            return await self._request("POST", "/locations", json=data)

        type_id = await self._get_entity_type_id(is_location=True)
        if type_id:
            data["entityTypeId"] = type_id
        return await self._request("POST", "/entities", json=data)

    async def update_location(
        self,
        location_id: str,
        name: str | None = None,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Update a location.

        Args:
            location_id: The location UUID.
            name: New name (optional).
            description: New description (optional).
            parent_id: New parent location ID (optional).

        Returns:
            Updated location object.
        """
        # Fetch current location to preserve fields not provided.
        current = await self.get_location(location_id)
        current_parent_id = (
            current.get("parent", {}).get("id") if current.get("parent") else None
        )

        data: dict[str, Any] = {
            "name": name if name is not None else current.get("name", ""),
            "description": (
                description if description is not None else current.get("description", "")
            ),
            "parentId": current_parent_id,
        }

        # If parent_id is explicitly provided, use it (empty string clears parent).
        if parent_id is not None:
            data["parentId"] = parent_id or None

        if await self._get_api_mode() == "legacy":
            return await self._request("PUT", f"/locations/{location_id}", json=data)

        # Preserve the entity type so the location keeps behaving as a container.
        current_type_id = (
            current.get("entityType", {}).get("id") if current.get("entityType") else None
        )
        if current_type_id:
            data["entityTypeId"] = current_type_id
        return await self._request("PUT", f"/entities/{location_id}", json=data)

    async def delete_location(self, location_id: str) -> None:
        """Delete a location.

        Args:
            location_id: The location UUID.
        """
        if await self._get_api_mode() == "legacy":
            await self._request("DELETE", f"/locations/{location_id}")
        else:
            await self._request("DELETE", f"/entities/{location_id}")

    # =========================================================================
    # Items
    # =========================================================================

    async def get_items(
        self,
        location_id: str | None = None,
        label_id: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get items with optional filters.

        Args:
            location_id: Filter by location ID.
            label_id: Filter by label ID.
            search: Search term for name/description.

        Returns:
            List of item objects.
        """
        if await self._get_api_mode() == "legacy":
            params: dict[str, str] = {}
            if location_id:
                params["locations"] = location_id
            if label_id:
                params["labels"] = label_id
            if search:
                params["q"] = search

            response = await self._request("GET", "/items", params=params)

            # The API returns {"items": [...]} wrapper
            if isinstance(response, dict) and "items" in response:
                return response["items"]
            return response

        # Entities mode: locations -> parentIds, labels -> tags, search -> q.
        params_e: dict[str, Any] = {}
        if location_id:
            params_e["parentIds"] = [location_id]
        if label_id:
            params_e["tags"] = [label_id]
        if search:
            params_e["q"] = search
        # Explicit for clarity: the server already excludes locations from
        # results when this is omitted (see get_locations), but spelling it
        # out here documents that behavior instead of relying on it silently.
        params_e["isLocation"] = False

        entities = await self._list_entities(params_e)
        return [self._normalize_item(e) for e in entities]

    async def get_item(self, item_id: str) -> dict[str, Any]:
        """Get a specific item by ID.

        Args:
            item_id: The item UUID.

        Returns:
            Item object with full details.
        """
        if await self._get_api_mode() == "legacy":
            return await self._request("GET", f"/items/{item_id}")

        entity = await self._request("GET", f"/entities/{item_id}")
        return self._normalize_item(entity)

    async def create_item(
        self,
        name: str,
        location_id: str,
        description: str | None = None,
        quantity: int = 1,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new item.

        Args:
            name: Item name.
            location_id: Location ID where the item will be stored.
            description: Optional description.
            quantity: Item quantity (default: 1).
            labels: Optional list of label IDs.

        Returns:
            Created item object.
        """
        if await self._get_api_mode() == "legacy":
            data: dict[str, Any] = {
                "name": name,
                "locationId": location_id,
                "quantity": quantity,
            }
            if description:
                data["description"] = description
            if labels:
                data["labelIds"] = labels
            return await self._request("POST", "/items", json=data)

        data = {
            "name": name,
            "parentId": location_id,
            "quantity": quantity,
        }
        if description:
            data["description"] = description
        if labels:
            data["tagIds"] = labels
        type_id = await self._get_entity_type_id(is_location=False)
        if type_id:
            data["entityTypeId"] = type_id
        entity = await self._request("POST", "/entities", json=data)
        return self._normalize_item(entity)

    async def update_item(
        self,
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
        """Update an item.

        Args:
            item_id: The item UUID.
            name: New name (optional).
            description: New description (optional).
            quantity: New quantity (optional).
            location_id: New location ID (optional).
            labels: New list of label IDs (optional).
            insured: Insurance status (optional).
            archived: Archive status (optional).
            asset_id: Asset ID (optional).
            serial_number: Serial number (optional).
            model_number: Model number (optional).
            manufacturer: Manufacturer (optional).
            purchase_price: Purchase price (optional).
            notes: Notes (optional).

        Returns:
            Updated item object.
        """
        if await self._get_api_mode() == "legacy":
            return await self._update_item_legacy(
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

        # Entities mode: read the raw entity to preserve untouched fields.
        current = await self._request("GET", f"/entities/{item_id}")
        current_parent = current.get("parent") or {}
        current_type = current.get("entityType") or {}
        current_tags = current.get("tags") or []

        data: dict[str, Any] = {
            "id": item_id,
            "name": name if name is not None else current.get("name", ""),
            "description": (
                description if description is not None else current.get("description", "")
            ),
            "quantity": quantity if quantity is not None else current.get("quantity", 1),
            "parentId": location_id if location_id is not None else current_parent.get("id"),
        }
        if current_type.get("id"):
            data["entityTypeId"] = current_type["id"]

        # Tags (labels)
        if labels is not None:
            data["tagIds"] = labels
        elif current_tags:
            data["tagIds"] = [tag["id"] for tag in current_tags]

        # Optional fields
        if insured is not None:
            data["insured"] = insured
        if archived is not None:
            data["archived"] = archived
        if asset_id is not None:
            data["assetId"] = asset_id
        if serial_number is not None:
            data["serialNumber"] = serial_number
        if model_number is not None:
            data["modelNumber"] = model_number
        if manufacturer is not None:
            data["manufacturer"] = manufacturer
        if purchase_price is not None:
            data["purchasePrice"] = purchase_price
        if notes is not None:
            data["notes"] = notes

        entity = await self._request("PUT", f"/entities/{item_id}", json=data)
        return self._normalize_item(entity)

    async def _update_item_legacy(
        self,
        item_id: str,
        name: str | None,
        description: str | None,
        quantity: int | None,
        location_id: str | None,
        labels: list[str] | None,
        insured: bool | None,
        archived: bool | None,
        asset_id: str | None,
        serial_number: str | None,
        model_number: str | None,
        manufacturer: str | None,
        purchase_price: float | None,
        notes: str | None,
    ) -> dict[str, Any]:
        """Update an item against the legacy ``/items`` endpoint."""
        # First get the current item to preserve existing values
        current = await self._request("GET", f"/items/{item_id}")

        data: dict[str, Any] = {
            "id": item_id,
            "name": name if name is not None else current.get("name", ""),
            "description": (
                description if description is not None else current.get("description", "")
            ),
            "quantity": quantity if quantity is not None else current.get("quantity", 1),
            "locationId": (
                location_id
                if location_id is not None
                else current.get("location", {}).get("id", "")
            ),
        }

        # Handle labels
        if labels is not None:
            data["labelIds"] = labels
        elif current.get("labels"):
            data["labelIds"] = [label["id"] for label in current["labels"]]

        # Optional fields
        if insured is not None:
            data["insured"] = insured
        if archived is not None:
            data["archived"] = archived
        if asset_id is not None:
            data["assetId"] = asset_id
        if serial_number is not None:
            data["serialNumber"] = serial_number
        if model_number is not None:
            data["modelNumber"] = model_number
        if manufacturer is not None:
            data["manufacturer"] = manufacturer
        if purchase_price is not None:
            data["purchasePrice"] = purchase_price
        if notes is not None:
            data["notes"] = notes

        return await self._request("PUT", f"/items/{item_id}", json=data)

    async def delete_item(self, item_id: str) -> None:
        """Delete an item.

        Args:
            item_id: The item UUID.
        """
        if await self._get_api_mode() == "legacy":
            await self._request("DELETE", f"/items/{item_id}")
        else:
            await self._request("DELETE", f"/entities/{item_id}")

    async def move_item(self, item_id: str, location_id: str) -> dict[str, Any]:
        """Move an item to a different location.

        Args:
            item_id: The item UUID.
            location_id: The new location UUID.

        Returns:
            Updated item object.
        """
        return await self.update_item(item_id, location_id=location_id)

    # =========================================================================
    # Labels / Tags
    # =========================================================================

    async def get_labels(self) -> list[dict[str, Any]]:
        """Get all labels (tags in the modern API).

        Returns:
            List of label objects.
        """
        if await self._get_api_mode() == "legacy":
            return await self._request("GET", "/labels")
        return await self._request("GET", "/tags")

    async def get_label(self, label_id: str) -> dict[str, Any]:
        """Get a specific label by ID.

        Args:
            label_id: The label UUID.

        Returns:
            Label object.
        """
        if await self._get_api_mode() == "legacy":
            return await self._request("GET", f"/labels/{label_id}")
        return await self._request("GET", f"/tags/{label_id}")

    async def create_label(
        self,
        name: str,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Create a new label (tag in the modern API).

        Args:
            name: Label name.
            description: Optional description.
            color: Optional color (hex code).

        Returns:
            Created label object.
        """
        data: dict[str, Any] = {"name": name}
        if description:
            data["description"] = description
        if color:
            data["color"] = color

        if await self._get_api_mode() == "legacy":
            return await self._request("POST", "/labels", json=data)
        return await self._request("POST", "/tags", json=data)

    async def update_label(
        self,
        label_id: str,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Update a label (tag in the modern API).

        Fetches the current label first and merges in the requested changes.
        Homebox's tag-update endpoint (``repo.TagUpdate``) takes a full
        replacement object where ``name`` is required even when it isn't
        changing, so sending only the fields the caller passed causes a
        422 Unprocessable Entity.

        Args:
            label_id: The label UUID.
            name: New name (optional).
            description: New description (optional).
            color: New color (optional).

        Returns:
            Updated label object.
        """
        current = await self.get_label(label_id)
        data: dict[str, Any] = {
            "id": label_id,
            "name": name if name is not None else current.get("name", ""),
            "description": (
                description if description is not None else current.get("description", "")
            ),
            "color": color if color is not None else current.get("color", ""),
        }
        icon = current.get("icon")
        if icon:
            data["icon"] = icon

        if await self._get_api_mode() == "legacy":
            return await self._request("PUT", f"/labels/{label_id}", json=data)

        # Tags mode also supports a parent (nested tags); preserve it so it
        # isn't silently cleared by this full-replacement update.
        parent_id = current.get("parentId") or (current.get("parent") or {}).get("id")
        if parent_id:
            data["parentId"] = parent_id
        return await self._request("PUT", f"/tags/{label_id}", json=data)

    async def delete_label(self, label_id: str) -> None:
        """Delete a label (tag in the modern API).

        Args:
            label_id: The label UUID.
        """
        if await self._get_api_mode() == "legacy":
            await self._request("DELETE", f"/labels/{label_id}")
        else:
            await self._request("DELETE", f"/tags/{label_id}")

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_statistics(self) -> dict[str, Any]:
        """Get inventory statistics.

        Returns:
            Statistics object with counts and totals.
        """
        # Unchanged across API versions.
        return await self._request("GET", "/groups/statistics")
