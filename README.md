# Thanks, Contributors!

> `thanks-contributors`是一个自动统计组织或多个项目贡献者的开源工具

[![Github Action](https://img.shields.io/badge/Github-Action-7FFFD4?logo=github-actions&logoColor=white)](https://github.com/marketplace/actions/thanks-contributors-x)
[![Github Template](https://img.shields.io/badge/Github-Template-181717?logo=github&logoColor=white)](https://github.com/new?template_name=thanks-contributors&template_owner=Sunrisepeak)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-32CD32?logo=github&logoColor=white)](https://Sunrisepeak.github.io/thanks-contributors)

| [English](README.md) - [文档](docs/README.md) - [主页](https://Sunrisepeak.github.io/thanks-contributors) |
| --- |

## ✨功能

- 可自定义单仓库或多仓库组合的贡献者统计
- `template`一键配置, 默认统计仓库所在用户的所有公开仓库
- 支持`Github Action`和本地使用
- 支持`Github Pages`自动部署&同步更新
- 支持`贡献者图片墙`和`Markdown贡献者列表`两种格式

## 快速开始

## 方式一: 直接使用项目模板

- 1.通过[创建thanks-contributors](https://github.com/new?template_name=thanks-contributors&template_owner=Sunrisepeak)
- 2.开启新建仓库的`Github Pages`功能 (可选)
  - `Setting -> Pages -> Build and deployment -> Source -> Github Actions`

## 方式二: 使用`GitHub Action`

> 可以通过项目的 [`Marketplace Actions`](https://github.com/marketplace/actions/thanks-contributors-x) 界面选择已经发布的不同版本

**action**

```yaml
- name: Thanks, Contributors!
  uses: Sunrisepeak/thanks-contributors@0.0.3
```

**完整workflows示例 - `.github/workflows/thanks-contributors.yml`**

```yaml
name: Thanks, Contributors!

on:
  workflow_dispatch:
  schedule:
    - cron: "0 3 * * *"

permissions:
  contents: write

jobs:
  collect:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Collect contributors
        uses: Sunrisepeak/thanks-contributors@0.0.3
```

> [!CAUTION]
> - 注1: 默认会统计当下用户或组织所有公开仓库的贡献者, 每天自动更新一次, 如果想只统计当前仓库或自定义统计的仓库可以查看 -> [参考文档](docs/README.md)
>
> - 注2: 配置好后, 可以选择手动运行action或等定时触发后观察效果


## 示例

> 当前用户所有公开仓库的贡献者们 - 每天自动更新

### 贡献者图片墙

> 可以在 `README.md` 或 `其他网站` 引用生成的贡献者图片墙

```bash
![](.thanks-contributors/contributors.png)
```

![](.thanks-contributors/contributors.png)

### 可点击的贡献者`Markdown`列表

> 支持自定义文件路径, 以及自定义自动更新区域
