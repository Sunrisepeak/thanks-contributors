# 常见问题

### Q1.如果仓库有分支保护, 自动更新失败问题

> A1.设置`auto_commit: false` -> 增加`pull-requests: write`权限 -> 设置仓库或组织允许Github Action创建PR
>
> `Org/Repo -> Setting -> Actions -> Genenral -> Workflow permissions -> Allow GitHub Actions to create and approve pull requests`

**参考案例** - [mcpp-community](https://github.com/mcpp-community/.github)

```yaml
name: Thanks, Contributors!

on:
  workflow_dispatch:
  schedule:
    - cron: "0 3 * * *"

permissions:
  contents: write
  pull-requests: write

jobs:
  collect:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Collect contributors
        uses: Sunrisepeak/thanks-contributors@0.0.4
        with:
          readme_path: profile/README.md
          auto_commit: false
```

### Q2.如果自定义README路径

> A2.配置readme_path参数, 详情 -> [说明文档](README.md)