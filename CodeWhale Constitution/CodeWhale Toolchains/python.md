# Python 工具链配置

> CodeWhale Constitution 附属文档 · 独立版本迭代 · 当前版本 1.0

---

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "your-project-name"
version = "0.1.0"
description = "项目描述"
requires-python = ">=3.11"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "F",    # pyflakes 错误
    "E",    # pycodestyle 错误
    "W",    # pycodestyle 警告
    "I",    # isort 导入排序
    "N",    # pep8-naming 命名规范
    "UP",   # pyupgrade 升级建议
    "B",    # bugbear bug 检测
    "SIM",  # 简化代码建议
    "ARG",  # 未使用参数检测
]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]

[tool.mypy]
strict = true
python_version = "3.11"
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
disallow_any_unimported = true
disallow_any_expr = false
disallow_any_decorated = false
disallow_any_explicit = true
disallow_subclassing_any = true

[[tool.mypy.overrides]]
module = ["tests.*"]
ignore_missing_imports = true
```

---

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        args: ["--line-length=100"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.8
    hooks:
      - id: ruff
        args: ["--fix"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: ["--strict"]
        additional_dependencies: ["types-requests"]
```
