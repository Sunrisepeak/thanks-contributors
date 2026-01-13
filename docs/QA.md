# 常见问题

### Q1.如果仓库有分支保护, 自动更新失败问题

> A1.设置`auto_commit: false` -> 增加`pull-requests: write`权限 -> 设置仓库或组织允许Github Action创建PR
>
> `Org/Repo -> Setting -> Actions -> Genenral -> Workflow permissions -> Allow GitHub Actions to create and approve pull requests`