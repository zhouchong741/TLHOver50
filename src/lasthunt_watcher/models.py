from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductSnapshot:
    object_id: str
    slug: str
    name: str
    original_price_cents: int
    sale_price_cents: int
    discount_percent: int
    detail_url: str
    image_url: str

    def to_state_record(self) -> dict[str, object]:
        return {
            "object_id": self.object_id,
            "slug": self.slug,
            "name": self.name,
            "original_price_cents": self.original_price_cents,
            "sale_price_cents": self.sale_price_cents,
            "discount_percent": self.discount_percent,
            "detail_url": self.detail_url,
            "image_url": self.image_url,
        }


@dataclass(frozen=True)
class CountChange:
    previous_count: int
    current_count: int

    @property
    def delta(self) -> int:
        return self.current_count - self.previous_count

    @property
    def abs_delta(self) -> int:
        return abs(self.delta)

    @property
    def direction_label(self) -> str:
        return "增加" if self.delta > 0 else "减少"


@dataclass(frozen=True)
class SearchContext:
    category_url: str
    app_bundle_url: str
    algolia_index_name: str
    algolia_params: str
    total_pages: int


def format_price(cents: int) -> str:
    return f"C${cents / 100:.2f}"
