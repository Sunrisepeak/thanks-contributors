# all-contributors

自动收集并聚合 GitHub 组织、用户或指定仓库的所有贡献者数据，生成 JSON、PNG、HTML 和 Markdown 四种格式输出。支持作为 GitHub Action 自动化运行，也可本地命令行使用。

---

## 核心特性

- **零配置启动**：无需任何参数即可统计当前仓库所属组织/用户的所有公开仓库贡献者
- **灵活目标配置**：支持通配符 `owner/*` 或精确指定 `owner/repo`
- **多格式输出**：JSON 数据、PNG 图片、HTML 网页、Markdown 文档
- **自动 README 更新**：自动在 README 中插入贡献者表格，支持自定义目标文件
- **跨仓库去重**：汇总贡献者信息并按贡献次数排序
- **智能处理**：自动跳过 fork 和归档仓库，速率限制智能延迟

---

## 快速开始

### 使用项目模板

1. [创建 all-contributors 仓库](https://github.com/new?template_name=all-contributors&template_owner=Sunrisepeak)
2. 开启新建仓库的 GitHub Pages 功能（可选）
   - Settings → Pages → Build and deployment → Source → GitHub Actions

### GitHub Action 方式

#### 最简配置

```yaml
name: All Contributors
on:
  schedule:
    - cron: '0 3 * * *'
  workflow_dispatch:

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Collect contributors
        uses: Sunrisepeak/all-contributors@main
```

#### 指定目标和选项

```yaml
      - uses: Sunrisepeak/all-contributors@main
        with:
          targets: 'org1/* org2/* alice/repo'
          token: ${{ secrets.GITHUB_TOKEN }}
          auto_commit: 'true'
          readme_path: 'README.md'
          deploy_to_pages: 'false'
```

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

# 或传递参数
python main.py --token ghp_xxx 'org/*' user/repo
```

生成文件：
- `contributors.json` - 结构化数据
- `contributors.png` - 头像墙（PNG 图片）
- `contributors.html` - 交互式网页
- `contributors.md` - Markdown 文档

---

## 参数配置

### GitHub Action Inputs

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `targets` | 自动检测 | 目标列表，格式：`owner/*` 或 `owner/repo`，空格分隔 |
| `token` | `${{ github.token }}` | GitHub 访问令牌 |
| `include_anonymous` | `true` | 包含匿名贡献者 |
| `skip_archived` | `false` | 跳过已归档仓库 |
| `per_repo_delay_ms` | `150` | 仓库间延迟（毫秒） |
| `auto_commit` | `true` | 自动提交更改 |
| `readme_path` | `README.md` | README 文件路径（相对路径） |
| `deploy_to_pages` | `false` | 部署到 GitHub Pages |

### 环境变量（本地运行）

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` 或 `GH_TOKEN` | GitHub 访问令牌 |
| `TARGETS` | 目标列表 |
| `OUTPUT_DIR` | 输出目录（默认：`.all-contributors`） |
| `README_PATH` | README 文件路径（默认：`README.md`） |
| `INCLUDE_ANONYMOUS` | 包含匿名贡献者 |
| `SKIP_ARCHIVED` | 跳过归档仓库 |
| `PER_REPO_DELAY_MS` | 仓库间延迟 |

---

## 输出格式

### contributors.json

包含全局汇总和按仓库分组的详细贡献者信息。

```json
{
  "count": 5,
  "contributors": [
    {
      "name": "Alice",
      "email": "alice@example.com",
    }
  ]
}
```

### contributors.png

圆形头像布局，透明背景，自动优化为 2:1 宽高比。

### contributors.html

现代设计的交互式网页，头像可点击跳转到贡献者主页，支持复制图片链接。

### contributors.md

Markdown 格式的贡献者表格，头像（50×50）+ 名字，每行 10 个贡献者。

---

## README 自动更新

项目支持自动在 README 中插入/更新贡献者表格。

### 使用标记

在 README 中添加标记：

```markdown
<!-- all-contributors-flag-start -->
<!-- all-contributors-flag-end -->
```

首次运行时，贡献者表格会自动插入到标记之间。后续更新会替换标记内的内容。

如果不添加标记，贡献者表格会追加到 README 末尾（仍会添加标记）。

### 自定义 README 文件

在 workflow 中指定 `readme_path`：

```yaml
- uses: Sunrisepeak/all-contributors@main
  with:
    readme_path: 'docs/CONTRIBUTORS.md'
```

---

## 权限与限制

- **公开仓库**：使用 `${{ github.token }}` 通常足够
- **私有仓库**：需要有 `repo` 权限的 Personal Access Token (PAT)
- **大型组织**：使用 PAT 获得更高的速率限制，建议调整 `per_repo_delay_ms`

---

## 高级用法

### 本地调试

```bash
# 测试单个仓库
python main.py --token ghp_xxx octocat/Hello-World

# 测试通配符
python main.py --token ghp_xxx 'my-org/*'
```

### 部署到 GitHub Pages

在 workflow 中启用 Pages 部署：

```yaml
- uses: Sunrisepeak/all-contributors@main
  with:
    deploy_to_pages: 'true'
```

确保仓库 Settings → Pages 中已配置为从 GitHub Actions 部署。

---

## 依赖

- Python 3.7+
- Pillow（用于 PNG 生成，自动安装）

---



## 贡献

欢迎提交 Issue 和 Pull Request, 以及Star该项目

---

## 许可证

Apache-2.0 License