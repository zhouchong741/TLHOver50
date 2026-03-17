from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

from .models import ProductSnapshot


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

    min_discount = int(payload["min_discount"])
    thresholds = sorted({value for value in (60, 55, min_discount) if value >= min_discount}, reverse=True)
    tab_buttons = "\n".join(
        (
            f'<button class="tab-btn{" active" if threshold == min_discount else ""}" '
            f'data-threshold="{threshold}">{threshold}%+</button>'
        )
        for threshold in thresholds
    )
    tab_buttons += '\n<button class="tab-btn" data-threshold="all">全部</button>'
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TLH Over 50 | Icebreaker Deals</title>
  <style>
    :root {{
      --bg: #f5f5f5;
      --panel: #ffffff;
      --panel-alt: #fafafa;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --accent: #ef4444;
      --accent-deep: #b91c1c;
      --accent-soft: rgba(239, 68, 68, 0.10);
      --shadow: 0 10px 30px rgba(17, 24, 39, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Inter, "Avenir Next", "Helvetica Neue", Helvetica, sans-serif;
      color: var(--ink);
      background: var(--bg);
      min-height: 100vh;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    button,
    input,
    select {{
      font: inherit;
    }}

    .shell {{
      width: min(1440px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 14px 0 56px;
    }}

    .masthead {{
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-bottom: 14px;
    }}

    .header-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 18px;
    }}

    .header-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .eyebrow {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(24px, 3vw, 34px);
      line-height: 1.1;
    }}

    .subtitle {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}

    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }}

    .count-pill,
    .update-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 0 14px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
      border: 1px solid var(--line);
      background: var(--panel-alt);
    }}

    .update-pill {{
      color: #ffffff;
      border-color: transparent;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }}

    .control {{
      min-height: 38px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--ink);
      padding: 0 12px;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    .control:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.10);
    }}

    .search-input {{
      min-width: 220px;
    }}

    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 12px;
    }}

    .primary-link,
    .secondary-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      padding: 0 16px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 13px;
      font-weight: 700;
    }}

    .primary-link {{
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
      border-color: transparent;
      color: #ffffff;
    }}

    .secondary-link {{
      background: var(--panel-alt);
    }}

    .tabs {{
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding: 2px 0 8px;
      margin-bottom: 14px;
      scrollbar-width: none;
    }}

    .tabs::-webkit-scrollbar {{
      display: none;
    }}

    .tab-btn {{
      min-height: 40px;
      padding: 0 16px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #e5e7eb;
      color: #4b5563;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
    }}

    .tab-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #ffffff;
    }}

    .meta-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}

    .meta-note {{
      color: var(--muted);
      font-size: 12px;
    }}

    .product-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}

    .product-card {{
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 4px 18px rgba(17, 24, 39, 0.06);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .product-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 12px 28px rgba(17, 24, 39, 0.12);
    }}

    .product-figure {{
      position: relative;
      background: #f3f4f6;
      overflow: hidden;
    }}

    .product-img {{
      width: 100%;
      height: 170px;
      object-fit: cover;
      display: block;
    }}

    .discount-badge {{
      position: absolute;
      top: 10px;
      right: 10px;
      min-height: 28px;
      padding: 0 10px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
      color: #ffffff;
      font-size: 12px;
      font-weight: 800;
      box-shadow: 0 4px 15px rgba(239, 68, 68, 0.35);
    }}

    .product-info {{
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1;
    }}

    .meta-chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .meta-chip {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      background: var(--accent-soft);
      color: var(--accent-deep);
    }}

    .product-name {{
      font-size: 13px;
      line-height: 1.45;
      font-weight: 700;
      min-height: 56px;
    }}

    .price-row {{
      display: flex;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .sale-price {{
      font-size: 18px;
      font-weight: 800;
      color: var(--ink);
    }}

    .original-price {{
      font-size: 12px;
      color: var(--muted);
      text-decoration: line-through;
    }}

    .detail-grid {{
      display: grid;
      gap: 6px;
      margin-top: auto;
      padding-top: 2px;
    }}

    .detail-line {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--muted);
      font-size: 12px;
    }}

    .detail-line strong {{
      color: var(--ink);
      font-size: 13px;
    }}

    .product-link {{
      margin-top: 8px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      color: var(--accent-deep);
      font-size: 13px;
    }}

    .empty-state {{
      grid-column: 1 / -1;
      padding: 42px 16px;
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 18px;
      text-align: center;
      color: var(--muted);
    }}

    footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }}

    #back-to-top {{
      position: fixed;
      right: 22px;
      bottom: 22px;
      width: 46px;
      height: 46px;
      border: none;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
      color: #ffffff;
      box-shadow: 0 6px 20px rgba(239, 68, 68, 0.35);
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transform: translateY(10px);
      transition: opacity 0.25s ease, transform 0.25s ease, visibility 0.25s ease;
    }}

    #back-to-top.show {{
      opacity: 1;
      visibility: visible;
      transform: translateY(0);
    }}

    @media (min-width: 640px) {{
      .product-grid {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }}

      .product-img {{
        height: 210px;
      }}
    }}

    @media (min-width: 1024px) {{
      .product-grid {{
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
      }}

      .product-img {{
        height: 240px;
      }}
    }}

    @media (min-width: 1280px) {{
      .product-grid {{
        grid-template-columns: repeat(5, minmax(0, 1fr));
      }}
    }}

    @media (max-width: 640px) {{
      .shell {{
        width: min(100vw - 16px, 1440px);
        padding-top: 8px;
      }}

      .header-card {{
        padding: 14px;
      }}

      .toolbar {{
        align-items: stretch;
      }}

      .control,
      .search-input {{
        width: 100%;
      }}

      .count-pill,
      .update-pill {{
        width: 100%;
        justify-content: center;
      }}

      .product-img {{
        height: 150px;
      }}

      .product-name {{
        min-height: 48px;
        font-size: 12px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="masthead">
      <div class="header-card">
        <div class="header-row">
          <div>
            <div class="eyebrow">The Last Hunt Watcher</div>
            <h1>Icebreaker 折扣商品看板</h1>
            <div class="subtitle">当前页面展示折扣大于等于 {escape(str(payload["min_discount"]))}% 的商品，样式参考 End70New 的紧凑商品流。</div>
          </div>
          <div class="toolbar">
            <span class="count-pill" id="item-count">加载中...</span>
            <input class="control search-input" id="search" type="text" placeholder="搜索产品名称...">
            <select class="control" id="sort-select">
              <option value="discount_desc">折扣率从高到低</option>
              <option value="price_asc">折后价从低到高</option>
              <option value="price_desc">折后价从高到低</option>
              <option value="name_asc">名称 A-Z</option>
            </select>
          </div>
        </div>
        <div class="link-row">
          <a class="primary-link" href="{escape(str(payload["category_url"]))}" target="_blank" rel="noreferrer">源分类页</a>
          <a class="secondary-link" href="./data.json" target="_blank" rel="noreferrer">JSON 数据</a>
        </div>
      </div>

      <div class="tabs" id="discount-tabs">
        {tab_buttons}
      </div>

      <div class="meta-row">
        <span class="update-pill" id="update-time">最后更新: 加载中...</span>
        <span class="meta-note">支持搜索、阈值筛选和价格排序</span>
      </div>
    </section>

    <section class="product-grid" id="product-grid"></section>

    <footer>
      Generated by GitHub Actions for TLHOver50.
    </footer>
  </main>
  <button id="back-to-top" title="回到顶部" aria-label="回到顶部">↑</button>
  <script id="page-data" type="application/json">{payload_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById("page-data").textContent);
    const allProducts = Array.isArray(payload.products) ? payload.products : [];
    const grid = document.getElementById("product-grid");
    const searchInput = document.getElementById("search");
    const sortSelect = document.getElementById("sort-select");
    const countLabel = document.getElementById("item-count");
    const updateTime = document.getElementById("update-time");
    const tabs = Array.from(document.querySelectorAll(".tab-btn"));
    const backToTop = document.getElementById("back-to-top");
    let activeThreshold = tabs.find((button) => button.classList.contains("active"))?.dataset.threshold || "all";

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }}

    function formatPrice(cents) {{
      return `C$${{(Number(cents) / 100).toFixed(2)}}`;
    }}

    function formatTime(value) {{
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {{
        return value;
      }}
      return date.toLocaleString("zh-CN", {{
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      }});
    }}

    function renderCard(product) {{
      const name = escapeHtml(product.name);
      const detailUrl = escapeHtml(product.detail_url);
      const imageUrl = escapeHtml(product.image_url);
      const salePrice = formatPrice(product.sale_price_cents);
      const originalPrice = formatPrice(product.original_price_cents);
      return `
        <article class="product-card">
          <a class="product-figure" href="${{detailUrl}}" target="_blank" rel="noreferrer">
            <img class="product-img" src="${{imageUrl}}" alt="${{name}}" loading="lazy" referrerpolicy="no-referrer">
            <span class="discount-badge">-${{product.discount_percent}}%</span>
          </a>
          <div class="product-info">
            <div class="meta-chips">
              <span class="meta-chip">折后价 ${{escapeHtml(salePrice)}}</span>
            </div>
            <div class="product-name">${{name}}</div>
            <div class="price-row">
              <span class="sale-price">${{escapeHtml(salePrice)}}</span>
              <span class="original-price">${{escapeHtml(originalPrice)}}</span>
            </div>
            <div class="detail-grid">
              <div class="detail-line"><span>原价</span><strong>${{escapeHtml(originalPrice)}}</strong></div>
              <div class="detail-line"><span>折后价</span><strong>${{escapeHtml(salePrice)}}</strong></div>
              <div class="detail-line"><span>折扣率</span><strong>${{product.discount_percent}}%</strong></div>
            </div>
            <a class="product-link" href="${{detailUrl}}" target="_blank" rel="noreferrer">查看详情</a>
          </div>
        </article>
      `;
    }}

    function getFilteredProducts() {{
      const keyword = searchInput.value.trim().toLowerCase();
      let products = allProducts.filter((product) => {{
        if (activeThreshold !== "all" && Number(product.discount_percent) < Number(activeThreshold)) {{
          return false;
        }}
        if (!keyword) {{
          return true;
        }}
        return String(product.name).toLowerCase().includes(keyword);
      }});

      switch (sortSelect.value) {{
        case "price_asc":
          products.sort((left, right) => left.sale_price_cents - right.sale_price_cents);
          break;
        case "price_desc":
          products.sort((left, right) => right.sale_price_cents - left.sale_price_cents);
          break;
        case "name_asc":
          products.sort((left, right) => String(left.name).localeCompare(String(right.name)));
          break;
        default:
          products.sort((left, right) => (
            right.discount_percent - left.discount_percent
            || left.sale_price_cents - right.sale_price_cents
            || String(left.name).localeCompare(String(right.name))
          ));
      }}
      return products;
    }}

    function render() {{
      const products = getFilteredProducts();
      countLabel.textContent = `显示 ${{products.length}} / ${{allProducts.length}} 件商品`;
      if (!products.length) {{
        grid.innerHTML = '<div class="empty-state">未找到符合当前筛选条件的商品。</div>';
        return;
      }}
      grid.innerHTML = products.map(renderCard).join("");
    }}

    tabs.forEach((button) => {{
      button.addEventListener("click", () => {{
        tabs.forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        activeThreshold = button.dataset.threshold || "all";
        render();
      }});
    }});

    searchInput.addEventListener("input", render);
    sortSelect.addEventListener("change", render);
    updateTime.textContent = `最后更新: ${{formatTime(payload.generated_at)}}`;

    window.addEventListener("scroll", () => {{
      if (window.scrollY > 320) {{
        backToTop.classList.add("show");
      }} else {{
        backToTop.classList.remove("show");
      }}
    }});

    backToTop.addEventListener("click", () => {{
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }});

    render();
  </script>
</body>
</html>
"""
