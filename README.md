# The Last Hunt Icebreaker Watcher

一个完整的 Python GitHub 项目：每 10 分钟抓取 The Last Hunt 的 Icebreaker 分类页，筛选折扣率大于等于 50% 的商品，检测新增或价格/折扣变化，并推送到飞书机器人 webhook。

项目优先使用站点 HTML、`__NEXT_DATA__` 内嵌 JSON 和站点公开搜索 API，不依赖 Playwright。

## 功能

- 每 10 分钟抓取一次目标分类页
- 自动处理分页
- 提取字段：
  - 产品名称
  - 原价
  - 折后价
  - 折扣率
  - 详情页链接
  - 图片链接
- 只推送“新增商品”或“价格/折扣变化”的商品
- 使用本地状态文件去重
- 支持 GitHub Actions `schedule` 和 `workflow_dispatch`
- 使用 GitHub Secret `FEISHU_WEBHOOK_URL`
- 支持日志、HTTP 重试、`--dry-run`

## 目录结构

```text
.
├── .github/workflows/monitor.yml
├── .env.example
├── README.md
├── requirements.txt
├── run.py
├── data/.gitkeep
└── src/lasthunt_watcher
    ├── __init__.py
    ├── __main__.py
    ├── config.py
    ├── main.py
    ├── models.py
    ├── notifier.py
    ├── scraper.py
    └── state.py
```

## 本地运行

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

填写：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook
```

### 3. 试跑但不发送消息

```bash
python run.py --dry-run
```

### 4. 正式运行

```bash
python run.py
```

## 命令行参数

```bash
python run.py --help
```

常用参数：

- `--dry-run`：只抓取和输出日志，不发送飞书消息，也不写入状态文件
- `--state-file`：自定义状态文件路径
- `--category-url`：自定义目标分类页 URL
- `--min-discount`：最低折扣阈值，默认 `50`
- `--log-level`：日志级别，默认 `INFO`
- `--log-file`：日志文件路径
- `--feishu-webhook-url`：命令行覆盖 webhook

## GitHub Actions

工作流文件为 `./.github/workflows/monitor.yml`。

触发方式：

- `workflow_dispatch`
- 每 10 分钟一次：`*/10 * * * *`

### 需要配置的 GitHub Secret

在仓库 Settings -> Secrets and variables -> Actions 中添加：

- `FEISHU_WEBHOOK_URL`

### 状态持久化

GitHub Actions 运行环境是临时的，项目通过 `actions/cache` 持久化 `data/state.json`，避免每次运行都把历史商品当成新商品。

## 实现说明

- 首先请求分类页 HTML，并解析 `__NEXT_DATA__`
- 从首屏数据中提取商品列表、分页总数和搜索请求模板
- 若存在更多分页，则从站点公开前端 bundle 中提取公开搜索配置，并调用公开搜索 API 拉取剩余页面
- 通过 `objectID` 做商品主键去重
- 只有在飞书推送成功后才会落盘更新状态文件，避免“通知失败但状态已前进”导致漏报

## 目标链接

默认监控页面：

```text
https://www.thelasthunt.com/c/icebreaker?size_1=S%2CM%2CL&sort=discountDesc
```
