"""HTTP client for the Homebox API."""

import logging
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)


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
            if self.config.use_token_auth:
                # Use pre-configured token
                self._token = self.config.homebox_token
                logger.info("Using configured token for Homebox authentication")
            else:
                # Login with credentials
                await self._login()

    async def _login(self) -> None:
        """Authenticate with the Homebox API using credentials."""
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/users/login",
            json={
                "username": self.config.homebox_username,
                "password": self.config.homebox_password,
            },
        )
        response.raise_for_status()
        data = response.json()
        self._token = data.get("token")
        logger.info("Successfully authenticated with Homebox using credentials")

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

        # Handle token expiration
        if response.status_code == 401:
            logger.info("Token expired, re-authenticating...")
            self._token = None
            await self._ensure_authenticated()
            headers = self._get_headers()
            response = await client.request(method, url, headers=headers, **kwargs)

        response.raise_for_status()

        if response.status_code == 204:
            return None

        return response.json()

    # =========================================================================
    # Locations
    # =========================================================================

    async def get_locations(self) -> list[dict[str, Any]]:
        """Get all locations.

        Returns:
            List of location objects.
        """
        return await self._request("GET", "/locations")

    async def get_location(self, location_id: str) -> dict[str, Any]:
        """Get a specific location by ID.

        Args:
            location_id: The location UUID.

        Returns:
            Location object.
        """
        return await self._request("GET", f"/locations/{location_id}")

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

        return await self._request("POST", "/locations", json=data)

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
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if parent_id is not None:
            data["parentId"] = parent_id

        return await self._request("PUT", f"/locations/{location_id}", json=data)

    async def delete_location(self, location_id: str) -> None:
        """Delete a location.

        Args:
            location_id: The location UUID.
        """
        await self._request("DELETE", f"/locations/{location_id}")

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

    async def get_item(self, item_id: str) -> dict[str, Any]:
        """Get a specific item by ID.

        Args:
            item_id: The item UUID.

        Returns:
            Item object with full details.
        """
        return await self._request("GET", f"/items/{item_id}")

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
        # First get the current item to preserve existing values
        current = await self.get_item(item_id)

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
        await self._request("DELETE", f"/items/{item_id}")

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
    # Labels
    # =========================================================================

    async def get_labels(self) -> list[dict[str, Any]]:
        """Get all labels.

        Returns:
            List of label objects.
        """
        return await self._request("GET", "/labels")

    async def get_label(self, label_id: str) -> dict[str, Any]:
        """Get a specific label by ID.

        Args:
            label_id: The label UUID.

        Returns:
            Label object.
        """
        return await self._request("GET", f"/labels/{label_id}")

    async def create_label(
        self,
        name: str,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Create a new label.

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

        return await self._request("POST", "/labels", json=data)

    async def update_label(
        self,
        label_id: str,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Update a label.

        Args:
            label_id: The label UUID.
            name: New name (optional).
            description: New description (optional).
            color: New color (optional).

        Returns:
            Updated label object.
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if color is not None:
            data["color"] = color

        return await self._request("PUT", f"/labels/{label_id}", json=data)

    async def delete_label(self, label_id: str) -> None:
        """Delete a label.

        Args:
            label_id: The label UUID.
        """
        await self._request("DELETE", f"/labels/{label_id}")

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_statistics(self) -> dict[str, Any]:
        """Get inventory statistics.

        Returns:
            Statistics object with counts and totals.
        """
        return await self._request("GET", "/groups/statistics")
