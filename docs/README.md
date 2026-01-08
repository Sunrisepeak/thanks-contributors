# all-contributors

自动收集并聚合 GitHub 组织、用户或指定仓库的所有贡献者数据，生成 JSON、PNG 和交互式 HTML 三种格式输出。支持作为 GitHub Action 自动化运行，也可本地命令行使用。

---

## ✨ 核心特性

### 🚀 零配置启动
无需任何参数即可统计当前仓库所属组织/用户的所有公开仓库贡献者，自动生成可追踪的历史记录。

### 🎯 灵活目标配置
- **通配符匹配**：`owner/*` 统计该 owner 下所有仓库
- **精确指定**：`owner/repo` 统计特定仓库
- **混合批量**：一次性指定多个组织、用户或仓库
- **智能默认**：默认统计当前仓库所在用户或组织下的所有公开仓库贡献者

### 📊 多格式输出
1. **JSON 数据**（`contributors.json`）
   - 全局去重汇总，按贡献次数降序
   - 按仓库维度详细分组
   - 完整的贡献者信息（姓名、邮箱、~~头像、主页~~）

2. **PNG 图片墙**（`contributors.png`）
   - 圆形头像布局，透明背景
   - 自动优化为 2:1 矩形比例（宽度约为高度两倍）
   - 根据贡献者数量智能排列

3. **交互式 HTML**（`contributors.html`）
   - 现代渐变设计，响应式布局
   - 头像可点击跳转到贡献者 GitHub 主页
   - 内嵌 PNG 图片预览
   - 一键复制图片链接按钮（适合分享到其他平台和嵌入到网站或README中）

### 🔧 智能处理
- 跨仓库去重汇总贡献次数
- 自动跳过 fork 和归档仓库
- 速率限制智能延迟

---

## 🚀 快速开始

### 使用默认配置

- 1.[创建all-contributors](https://github.com/new?template_name=all-contributors&template_owner=Sunrisepeak)
- 2.开启新建仓库的`Github Pages`功能 (可选)
  - `Setting -> Pages -> Build and deployment -> Source -> Github Actions`

### GitHub Action 方式

#### 最简配置（自动检测当前组织）
```yaml
name: Update Contributors
on:
  schedule:
    - cron: '0 3 * * *'  # 每天凌晨 3 点运行
  workflow_dispatch:

jobs:
  collect:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Collect contributors
        uses: Sunrisepeak/all-contributors@main
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add contributors.*
          git diff --quiet && git diff --staged --quiet || (git commit -m "Update contributors" && git push)
```

#### 指定多个目标
```yaml
      - uses: Sunrisepeak/all-contributors@main
        with:
          token: ${{ secrets.MY_PAT }}
          targets: |
            my-org/*
            alice/*
            team/tool
            bob/project
```

**说明**：
- 支持空格、逗号或换行作为分隔符
- `owner/*` 统计该 owner 的所有公开仓库
- `owner/repo` 统计特定仓库
- 留空 `targets` 则自动检测 `GITHUB_REPOSITORY` 的 owner

### 本地命令行方式

```bash
# 克隆仓库
git clone https://github.com/Sunrisepeak/all-contributors.git
cd all-contributors

# 安装依赖
pip install -r requirements.txt

# 统计指定目标
export GITHUB_TOKEN=ghp_your_token_here
python main.py 'octocat/*'

# 或直接传递参数
python main.py --token ghp_xxx 'myorg/*' alice/repo bob/project
```

**生成文件**：
- `contributors.json` - 结构化数据
- `contributors.png` - 贡献者头像墙
- `contributors.html` - 交互式网页

---

## ⚙️ 参数配置

### Inputs（GitHub Action）

| 参数 | 默认值 | 说明 |
|------|------|--------|------|
| `token` | `GITHUB_TOKEN` | GitHub 访问令牌。建议使用 PAT；公开仓库可用 `GITHUB_TOKEN` |
| `targets` | 自动检测 | 目标列表，格式：`owner/*` 或 `owner/repo`，多个用空格/逗号/换行分隔 |
| `out_file` | `contributors.json` | 输出 JSON 文件路径 |
| `include_anonymous` | `true` | 是否包含匿名贡献者 |
| `skip_archived` | `true` | 是否跳过已归档仓库 |
| `per_repo_delay_ms` | `150` | 每个仓库请求间隔（毫秒），避免速率限制 |

### 环境变量（本地运行）

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` 或 `GH_TOKEN` | GitHub 访问令牌 |
| `TARGETS` | 目标列表（逗号或空格分隔） |
| `OUT_FILE` | 输出文件路径 |
| `INCLUDE_ANONYMOUS` | 包含匿名贡献者（`true`/`false`） |
| `SKIP_ARCHIVED` | 跳过归档仓库（`true`/`false`） |
| `PER_REPO_DELAY_MS` | 仓库间延迟毫秒数 |

---

## 📄 输出格式

### contributors.json 结构

```json
{
  "all-contributors": "1.0.0",
  "count": 5,
  "contributors": [
    {
      "name": "Alice",
      "email": "alice@example.com",
    },
    {
      "name": "Bob",
      "email": null,
    }
  ],
  "details": {
    "owner/repo1": {
      "count": 3,
      "contributors": [...]
    },
    "owner/repo2": {
      "count": 2,
      "contributors": [...]
    }
  }
}
```

**字段说明**：
- `all-contributors`：工具版本标识
- `count`：全局去重后的贡献者总数
- `contributors`：聚合的贡献者列表（按 `contributions` 降序）
  - `name`：贡献者姓名
  - `email`：邮箱（可能为 null）
  - ~~`avatar_url`：GitHub 头像 URL~~
  - ~~`html_url`：GitHub 个人主页~~
  - ~~`contributions`：跨仓库累计提交次数~~
- `details`：按仓库分组的详细贡献者信息

### contributors.png

- **布局**：圆形头像，透明背景，自动计算最接近 2:1 比例的网格布局
- **尺寸**：头像 80×80 px，间距 10 px，边距 16 px
- **用途**：适合嵌入 README 或分享到社交平台

### contributors.html

- **设计**：现代渐变背景，玻璃态效果，响应式网格
- **功能**：
  - 头像可点击跳转到贡献者主页
  - 内嵌 PNG 图片预览
  - "复制贡献者图片链接" 按钮（使用 Clipboard API）
- **部署**：可直接作为 GitHub Pages 发布（参考 `.github/workflows/deploy-pages.yml`）

---

## 🔐 权限与速率限制

### Token 权限
- **公开仓库**：`GITHUB_TOKEN`（Actions 自动提供）通常足够
- **私有仓库**：需要有 `repo` 权限的 Personal Access Token (PAT)
- **大型组织**：建议使用 PAT 以获得更高速率限制

### 速率限制应对
- **默认延迟**：每个仓库间隔 150 毫秒
- **大型组织**：调大 `per_repo_delay_ms`（如 `300` 或 `500`）
- **速率耗尽**：日志会显示剩余额度与重置时间，脚本自动处理 403 响应

---

## 📦 依赖

- **Python 3.7+**
- **Pillow**：PNG 图片生成（GitHub Action 自动安装，本地需手动 `pip install -r requirements.txt`）

---

## 🌟 示例项目

本仓库自身使用该 Action 统计以下目标：
- `Sunrisepeak/*`
- `mcpp-community/*`
- `d2learn/*`

查看最新结果：
- [contributors.json](../contributors.json)
- [contributors.png](../contributors.png)
- [contributors.html](../contributors.html)（可通过 GitHub Pages 访问）

---

## 🛠️ 高级用法

### 自动部署到 GitHub Pages

在 `.github/workflows/deploy-pages.yml` 中配置：

```yaml
name: Deploy Contributors to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'contributors.html'
      - 'contributors.png'
      - 'contributors.json'
      - '.github/workflows/deploy-pages.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Pages
        uses: actions/configure-pages@v4
      
      - name: Prepare deployment
        run: |
          mkdir -p _site
          cp contributors.html _site/index.html
          cp contributors.png _site/
          cp contributors.json _site/
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
      
      - name: Deploy to Pages
        uses: actions/deploy-pages@v4
```

### 本地调试

```bash
# 检查 Python 环境
python --version

# 安装依赖
pip install -r requirements.txt

# 测试单个仓库
python main.py --token ghp_xxx octocat/Hello-World

# 测试通配符
python main.py --token ghp_xxx 'my-org/*'

# 查看生成的文件
ls -lh contributors.*
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**贡献者列表由本工具自动维护** 🎉

---

## 📜 许可证

Apache-2.0 License - 详见 [LICENSE](../LICENSE)

---

## 💬 反馈

如有问题或建议，请访问 [GitHub Issues](https://github.com/Sunrisepeak/all-contributors/issues)