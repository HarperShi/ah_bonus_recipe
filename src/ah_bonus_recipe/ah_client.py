from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import httpx

from ah_bonus_recipe.config import (
    AH_API_BASE_URL,
    AH_APPLICATION,
    AH_CLIENT_ID,
    AH_CLIENT_VERSION,
    AH_USER_AGENT,
)


FETCH_BONUS_GROUP_PRODUCTS_QUERY = """
query FetchBonusPromotionWithProducts(
  $id: String
  $periodStart: String
  $periodEnd: String
  $filterUnavailableProducts: Boolean
  $forcePromotionVisibility: Boolean = true
  $showAllPromotionSegments: Boolean = true
) {
  bonusPromotions(
    input: {
      id: $id
      periodStart: $periodStart
      periodEnd: $periodEnd
      filterUnavailableProducts: $filterUnavailableProducts
      forcePromotionVisibility: $forcePromotionVisibility
      showAllPromotionSegments: $showAllPromotionSegments
    }
  ) {
    id
    title
    productCount
    products {
      id
      title
      brand
      category
      salesUnitSize
      icons
      availability { isOrderable }
      priceV2(
        periodStart: $periodStart
        periodEnd: $periodEnd
        filterUnavailableProducts: $filterUnavailableProducts
        forcePromotionVisibility: true
      ) {
        now { amount }
        was { amount }
        promotionLabel { tiers { mechanism description } }
      }
      imagePack { large { url width height } }
    }
  }
}
""".strip()


class AHClient:
    """Small client for the AH mobile API.

    The API is not a formally documented public developer API. Keep request
    volume modest, keep raw payloads, and expect fields to change.
    """

    def __init__(
        self,
        base_url: str = AH_API_BASE_URL,
        client_id: str = AH_CLIENT_ID,
        client_version: str = AH_CLIENT_VERSION,
        user_agent: str = AH_USER_AGENT,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_version = client_version
        self.user_agent = user_agent
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "AHClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def access_token(self) -> str | None:
        return self._access_token

    def get_anonymous_token(self) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/mobile-auth/v1/auth/token/anonymous",
            headers=self._headers(include_auth=False),
            json={"clientId": self.client_id},
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token")
        return payload

    def ensure_token(self) -> None:
        if not self._access_token:
            self.get_anonymous_token()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        self.ensure_token()
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        response = self.client.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=self._headers(include_auth=True),
        )
        response.raise_for_status()
        return response.json()

    def get_bonus_metadata(self) -> dict[str, Any]:
        payload = self.request_json("GET", "/mobile-services/bonuspage/v3/metadata")
        if not isinstance(payload, dict):
            raise TypeError("Expected AH bonus metadata response to be an object")
        return payload

    def get_bonus_section_from_metadata_url(self, metadata_url: str) -> dict[str, Any]:
        path = metadata_url
        if not path.startswith("/mobile-services/"):
            path = "/mobile-services/" + path.lstrip("/")
        payload = self.request_json("GET", path)
        if not isinstance(payload, dict):
            raise TypeError("Expected AH bonus section response to be an object")
        return payload

    def get_product_detail(self, webshop_id: int) -> dict[str, Any]:
        payload = self.request_json("GET", f"/mobile-services/product/detail/v4/fir/{webshop_id}")
        if not isinstance(payload, dict):
            raise TypeError("Expected AH product detail response to be an object")
        return payload

    def search_products(
        self,
        query: str,
        *,
        page: int = 0,
        size: int = 20,
        sort_on: str = "RELEVANCE",
    ) -> dict[str, Any]:
        payload = self.request_json(
            "GET",
            "/mobile-services/product/search/v2",
            params={"query": query, "page": page, "size": size, "sortOn": sort_on},
        )
        if not isinstance(payload, dict):
            raise TypeError("Expected AH product search response to be an object")
        return payload

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        payload = self.request_json(
            "POST",
            "/graphql",
            json_body={"query": query, "variables": dict(variables)},
        )
        if not isinstance(payload, dict):
            raise TypeError("Expected AH GraphQL response to be an object")
        if payload.get("errors"):
            raise RuntimeError(f"AH GraphQL error: {payload['errors']}")
        return payload

    def get_bonus_group_products(
        self,
        segment_id: str,
        *,
        period_start: str,
        period_end: str,
        filter_unavailable_products: bool = True,
    ) -> dict[str, Any]:
        return self.graphql(
            FETCH_BONUS_GROUP_PRODUCTS_QUERY,
            {
                "id": segment_id,
                "periodStart": period_start,
                "periodEnd": period_end,
                "filterUnavailableProducts": filter_unavailable_products,
                "forcePromotionVisibility": True,
                "showAllPromotionSegments": True,
            },
        )

    def _headers(self, *, include_auth: bool) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": self.user_agent,
            "x-application": AH_APPLICATION,
            "x-client-name": self.client_id,
            "x-client-version": self.client_version,
        }
        if include_auth and self._access_token:
            headers["authorization"] = f"Bearer {self._access_token}"
        return headers
