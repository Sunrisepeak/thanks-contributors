# all-contributors

> 一个自动统计组织或多个项目贡献者的开源工具

[![Github Action](https://img.shields.io/badge/Github-Action-7FFFD4?logo=github-actions&logoColor=white)](https://github.com/marketplace/actions/all-contributors-x)
[![Github Template](https://img.shields.io/badge/Github-Template-181717?logo=github&logoColor=white)](https://github.com/new?template_name=all-contributors&template_owner=Sunrisepeak)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-32CD32?logo=github&logoColor=white)](https://Sunrisepeak.github.io/all-contributors)

| [English](README.md) - [文档](docs/README.md) - [主页](https://Sunrisepeak.github.io/all-contributors) - [贡献者图片墙](contributors.png) |
| --- |

## ✨功能

- 支持单仓库和多仓库组合贡献者统计
- 支持用户或组织所有仓库贡献者统计
- 支持通过template一键配置, 默认统计仓库所在用户的所有公开仓库
- 支持`Github Action`和本地使用
- 支持`Github Pages`同步更新

## 快速开始

## 方式一: 直接使用项目模板

- 1.通过[创建all-contributors](https://github.com/new?template_name=all-contributors&template_owner=Sunrisepeak)
- 2.开启新建仓库的`Github Pages`功能 (可选)
  - `Setting -> Pages -> Build and deployment -> Source -> Github Actions`

## 方式二: 使用`GitHub Action`

> 可以通过项目的 [`Marketplace Actions`](https://github.com/marketplace/actions/all-contributors-x) 界面选择已经发布的不同版本

```yaml
- name: All Contributors X
  uses: Sunrisepeak/all-contributors@0.0.2
```

注: 默认会统计你名下所有公开仓库的贡献者, 每天凌晨自动更新一次, 如果想自定义统计的仓库可以查看 -> [参考文档](docs/README.md)

## 所有贡献者

> 当前用户所有公开仓库的贡献者们

![](contributors.png)