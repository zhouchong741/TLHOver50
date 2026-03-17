from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

from .models import ProductSnapshot, format_price


def build_site(
    products: list[ProductSnapshot],
    output_dir: Path,
    category_url: str,
    min_discount: int,
    pages_url: str,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    sorted_products = sorted(
        products,
        key=lambda item: (-item.discount_percent, item.sale_price_cents, item.name.lower()),
    )

    payload = {
        "generated_at": generated_at,
        "category_url": category_url,
        "min_discount": min_discount,
        "pages_url": pages_url,
        "product_count": len(sorted_products),
        "products": [product.to_state_record() for product in sorted_products],
    }

    (output_dir / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    (output_dir / "index.html").write_text(
        _render_index_html(payload),
        encoding="utf-8",
    )
    return {
        "generated_at": generated_at,
        "site_dir": str(output_dir),
        "product_count": len(sorted_products),
    }


def _render_index_html(payload: dict[str, object]) -> str:
    products = payload["products"]
    if not isinstance(products, list):
        raise ValueError("Site payload products must be a list.")

    cards = "\n".join(_render_card(product) for product in products)
    pages_url = str(payload.get("pages_url") or "")
    pages_link = (
        f'<a class="secondary-link" href="{escape(pages_url)}">Open This Page</a>'
        if pages_url
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TLH Over 50 | Icebreaker Deals</title>
  <style>
    :root {{
      --bg: #f5efe7;
      --surface: rgba(255, 252, 247, 0.88);
      --surface-strong: #fffdf8;
      --ink: #1e1c19;
      --muted: #666055;
      --line: rgba(73, 59, 44, 0.14);
      --accent: #b24324;
      --accent-soft: #f4d8c8;
      --success: #1d6a4d;
      --shadow: 0 24px 80px rgba(67, 41, 16, 0.12);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", Helvetica, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(178, 67, 36, 0.20), transparent 30%),
        radial-gradient(circle at top right, rgba(29, 106, 77, 0.16), transparent 28%),
        linear-gradient(180deg, #f6f0e9 0%, #efe6db 100%);
      min-height: 100vh;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    .shell {{
      width: min(1240px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 64px;
    }}

    .hero {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
      padding: 36px;
      backdrop-filter: blur(8px);
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -40px -60px auto;
      width: 180px;
      height: 180px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(178, 67, 36, 0.18), rgba(178, 67, 36, 0));
    }}

    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 14px;
    }}

    h1 {{
      margin: 0;
      font-family: Georgia, Cambria, "Times New Roman", serif;
      font-size: clamp(34px, 4vw, 58px);
      line-height: 0.95;
      max-width: 700px;
    }}

    .hero-copy {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.7;
      max-width: 720px;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 28px;
    }}

    .stat {{
      background: var(--surface-strong);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
    }}

    .stat-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .stat-value {{
      margin-top: 8px;
      font-size: 26px;
      font-weight: 700;
    }}

    .hero-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }}

    .primary-link,
    .secondary-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-weight: 700;
    }}

    .primary-link {{
      background: var(--ink);
      color: #fffdf8;
    }}

    .secondary-link {{
      background: rgba(255, 255, 255, 0.55);
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
      margin-top: 24px;
    }}

    .card {{
      background: rgba(255, 253, 248, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 14px 36px rgba(58, 43, 24, 0.08);
    }}

    .thumb {{
      aspect-ratio: 4 / 5;
      background: linear-gradient(180deg, #f7efe6, #f0e4d6);
      overflow: hidden;
    }}

    .thumb img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}

    .card-body {{
      padding: 18px;
    }}

    .badge-row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
    }}

    .badge-discount {{
      color: var(--accent);
      background: var(--accent-soft);
    }}

    .badge-price {{
      color: var(--success);
      background: rgba(29, 106, 77, 0.12);
    }}

    .card-title {{
      font-size: 18px;
      line-height: 1.4;
      font-weight: 700;
      min-height: 76px;
    }}

    .price-stack {{
      display: grid;
      gap: 8px;
      margin-top: 16px;
    }}

    .price-line {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--muted);
      font-size: 14px;
    }}

    .price-line strong {{
      color: var(--ink);
      font-size: 16px;
    }}

    .card-link {{
      margin-top: 18px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      color: var(--accent);
    }}

    footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 13px;
      text-align: center;
    }}

    @media (max-width: 640px) {{
      .shell {{
        width: min(100vw - 20px, 1240px);
        padding-top: 20px;
      }}

      .hero {{
        padding: 24px;
        border-radius: 22px;
      }}

      .card-title {{
        min-height: auto;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">The Last Hunt Monitor</div>
      <h1>Icebreaker 折扣大于等于 {escape(str(payload["min_discount"]))}% 商品看板</h1>
      <p class="hero-copy">
        自动抓取分类页并生成静态看板。当前页面展示满足折扣条件的全部商品，包括图片、名称、原价、折后价、折扣率和详情页链接。
      </p>
      <div class="stats">
        <div class="stat">
          <div class="stat-label">Product Count</div>
          <div class="stat-value">{escape(str(payload["product_count"]))}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Discount Threshold</div>
          <div class="stat-value">>= {escape(str(payload["min_discount"]))}%</div>
        </div>
        <div class="stat">
          <div class="stat-label">Updated At</div>
          <div class="stat-value">{escape(str(payload["generated_at"]))}</div>
        </div>
      </div>
      <div class="hero-links">
        <a class="primary-link" href="{escape(str(payload["category_url"]))}" target="_blank" rel="noreferrer">Open Source Category</a>
        <a class="secondary-link" href="./data.json" target="_blank" rel="noreferrer">Open JSON Data</a>
        {pages_link}
      </div>
    </section>

    <section class="grid">
      {cards}
    </section>

    <footer>
      Generated by GitHub Actions for TLHOver50.
    </footer>
  </main>
</body>
</html>
"""


def _render_card(product: object) -> str:
    if not isinstance(product, dict):
        raise ValueError("Product payload must be a mapping.")

    name = escape(str(product["name"]))
    image_url = escape(str(product["image_url"]))
    detail_url = escape(str(product["detail_url"]))
    discount_percent = escape(str(product["discount_percent"]))
    original_price = format_price(int(product["original_price_cents"]))
    sale_price = format_price(int(product["sale_price_cents"]))

    return f"""
      <article class="card">
        <div class="thumb">
          <img src="{image_url}" alt="{name}" loading="lazy" referrerpolicy="no-referrer">
        </div>
        <div class="card-body">
          <div class="badge-row">
            <span class="badge badge-discount">-{discount_percent}%</span>
            <span class="badge badge-price">{escape(sale_price)}</span>
          </div>
          <div class="card-title">{name}</div>
          <div class="price-stack">
            <div class="price-line">
              <span>原价</span>
              <strong>{escape(original_price)}</strong>
            </div>
            <div class="price-line">
              <span>折后价</span>
              <strong>{escape(sale_price)}</strong>
            </div>
            <div class="price-line">
              <span>折扣率</span>
              <strong>{discount_percent}%</strong>
            </div>
          </div>
          <a class="card-link" href="{detail_url}" target="_blank" rel="noreferrer">查看详情</a>
        </div>
      </article>
    """
