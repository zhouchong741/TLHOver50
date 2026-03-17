from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import ProductSnapshot, SearchContext


LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.thelasthunt.com"
DETAIL_BASE_URL = f"{BASE_URL}/p"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


def build_retry_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en;q=0.9",
        }
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@dataclass
class LastHuntScraper:
    session: requests.Session
    category_url: str
    min_discount: int
    timeout_seconds: float = 30.0

    def scrape(self) -> tuple[list[ProductSnapshot], dict[str, int]]:
        html = self._get_text(self.category_url)
        next_data = self._parse_next_data(html)
        search_context, initial_hits = self._extract_search_context(next_data, html)

        hits = list(initial_hits)
        LOGGER.info("Initial page returned %s hit(s).", len(initial_hits))

        if search_context.total_pages > 1:
            hits.extend(self._fetch_remaining_hits(search_context))

        deduped_hits = self._dedupe_hits(hits)
        products = self._normalize_hits(deduped_hits)
        filtered = [product for product in products if product.discount_percent >= self.min_discount]

        LOGGER.info(
            "Collected %s raw hit(s), %s unique product(s), %s product(s) after discount filter >= %s%%.",
            len(hits),
            len(products),
            len(filtered),
            self.min_discount,
        )
        return filtered, {
            "raw_hits": len(hits),
            "unique_products": len(products),
            "filtered_products": len(filtered),
            "total_pages": search_context.total_pages,
        }

    def _fetch_remaining_hits(self, context: SearchContext) -> list[dict[str, Any]]:
        algolia = self._extract_algolia_config(context.app_bundle_url)
        endpoint = algolia["proxy_url"] or f"https://{algolia['app_id']}.algolia.net"
        endpoint = f"{endpoint.rstrip('/')}/1/indexes/*/queries"

        all_hits: list[dict[str, Any]] = []
        pages = list(range(1, context.total_pages))
        for batch in _chunked(pages, 10):
            payload = {
                "requests": [
                    {
                        "indexName": context.algolia_index_name,
                        "params": self._set_algolia_page(context.algolia_params, page),
                    }
                    for page in batch
                ],
                "strategy": "none",
            }
            response = self.session.post(
                endpoint,
                headers={
                    "X-Algolia-Application-ID": algolia["app_id"],
                    "X-Algolia-API-Key": algolia["api_key"],
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()

            for requested_page, result in zip(batch, data.get("results", []), strict=False):
                reported_page = int(result.get("page", requested_page))
                page_hits = result.get("hits", [])
                LOGGER.info(
                    "Fetched page %s via Algolia API, got %s hit(s).",
                    reported_page,
                    len(page_hits),
                )
                all_hits.extend(page_hits)
        return all_hits

    def _extract_algolia_config(self, app_bundle_url: str) -> dict[str, str]:
        bundle_text = self._get_text(f"{BASE_URL}{app_bundle_url}")
        needle = "NEXT_PUBLIC_ALGOLIA_PROXY_URL"
        start = bundle_text.find(needle)
        if start == -1:
            raise RuntimeError("Could not locate public Algolia config in app bundle.")

        window = bundle_text[start : start + 4000]
        app_match = re.search(r'"([A-Z0-9]{10})"', window)
        api_key_match = re.search(r'"([a-fA-F0-9]{32})"', window, re.I)
        proxy_match = re.search(
            r'NEXT_PUBLIC_ALGOLIA_PROXY_URL\)\?[^:]+:"(https://[^"]+)"',
            window,
        )
        app_id = app_match.group(1) if app_match else ""
        api_key = api_key_match.group(1) if api_key_match else ""
        proxy_url = proxy_match.group(1) if proxy_match else ""

        if not app_id or not api_key:
            fallback = re.search(
                r'NEXT_PUBLIC_ALGOLIA_PROXY_URL.*?"([A-Z0-9]{10})".*?"([a-fA-F0-9]{32})"',
                bundle_text,
                re.I | re.S,
            )
            if fallback:
                app_id = fallback.group(1)
                api_key = fallback.group(2)

        if not app_id or not api_key:
            raise RuntimeError("Could not parse public Algolia credentials from app bundle.")

        LOGGER.info("Resolved public Algolia config from app bundle.")
        return {"app_id": app_id, "api_key": api_key, "proxy_url": proxy_url}

    def _extract_search_context(
        self, next_data: dict[str, Any], html: str
    ) -> tuple[SearchContext, list[dict[str, Any]]]:
        page_props = next_data["props"]["pageProps"]
        initial_results = page_props["serverState"]["initialResults"]
        product_key = next(
            (key for key in initial_results if key.startswith("PRODUCTS_TLH_")),
            None,
        )
        if not product_key:
            raise RuntimeError("Could not locate products initialResults payload.")

        result_bucket = initial_results[product_key]
        first_result = result_bucket["results"][0]
        app_bundle_url = self._extract_app_bundle_url(html)

        context = SearchContext(
            category_url=self.category_url,
            app_bundle_url=app_bundle_url,
            algolia_index_name=first_result["index"],
            algolia_params=first_result["params"],
            total_pages=int(first_result.get("nbPages", 1)),
        )
        return context, list(first_result.get("hits", []))

    def _extract_app_bundle_url(self, html: str) -> str:
        match = re.search(
            r'<script[^>]+src="(?P<src>/_next/static/chunks/pages/_app-[^"]+\.js(?:\?[^"]*)?)"',
            html,
        )
        if not match:
            raise RuntimeError("Could not find Next.js _app bundle URL.")
        return match.group("src")

    def _parse_next_data(self, html: str) -> dict[str, Any]:
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(?P<payload>.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            raise RuntimeError("Could not find __NEXT_DATA__ payload.")
        return json.loads(match.group("payload"))

    def _normalize_hits(self, hits: list[dict[str, Any]]) -> list[ProductSnapshot]:
        products: list[ProductSnapshot] = []
        for hit in hits:
            product = self._normalize_hit(hit)
            if product:
                products.append(product)
        return products

    def _normalize_hit(self, hit: dict[str, Any]) -> ProductSnapshot | None:
        object_id = str(hit.get("objectID") or "").strip()
        slug = str(hit.get("slug") or "").strip()
        name = str(hit.get("name") or "").strip()
        sale_price_cents = _extract_cent_amount(hit.get("price"))
        original_price_cents = _extract_cent_amount(hit.get("original_price"))
        discount_percent = _extract_percent(hit.get("discounted_percent"))
        image_url = str(hit.get("image_url") or _extract_thumbnail_image(hit.get("thumbnails")) or "").strip()

        if not object_id or not slug or not name:
            LOGGER.warning("Skipping hit with missing identifiers: %s", hit)
            return None

        if sale_price_cents is None or original_price_cents is None or discount_percent is None:
            LOGGER.warning("Skipping hit with missing price fields: %s", object_id)
            return None

        if not image_url:
            LOGGER.warning("Skipping hit with missing image URL: %s", object_id)
            return None

        return ProductSnapshot(
            object_id=object_id,
            slug=slug,
            name=name,
            original_price_cents=original_price_cents,
            sale_price_cents=sale_price_cents,
            discount_percent=discount_percent,
            detail_url=f"{DETAIL_BASE_URL}/{slug}",
            image_url=image_url,
        )

    def _dedupe_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for hit in hits:
            key = str(hit.get("objectID") or hit.get("slug") or "")
            if key:
                deduped[key] = hit
        return list(deduped.values())

    def _set_algolia_page(self, params_string: str, page: int) -> str:
        params = dict(parse_qsl(params_string, keep_blank_values=True))
        params["page"] = str(page)
        return urlencode(params)

    def _get_text(self, url: str) -> str:
        LOGGER.info("Fetching %s", url)
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text


def _extract_cent_amount(value: Any) -> int | None:
    if not value or not isinstance(value, dict):
        return None
    amount = value.get("CAD", {}).get("centAmount")
    if isinstance(amount, list):
        amount = next((item for item in amount if item is not None), None)
    if amount is None:
        return None
    return int(amount)


def _extract_percent(value: Any) -> int | None:
    if isinstance(value, list):
        value = next((item for item in value if item is not None), None)
    if value is None:
        return None
    return int(value)


def _extract_thumbnail_image(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    first = value[0]
    if not isinstance(first, dict):
        return None
    image_url = first.get("image_url")
    return str(image_url) if image_url else None


def _chunked(items: list[int], size: int) -> list[list[int]]:
    return [items[index : index + size] for index in range(0, len(items), size)]
