# 参与贡献

欢迎帮助 DromX Stock 改进投研体验。问题反馈、文档修正、数据源适配和功能贡献都很有价值。

## 反馈问题或建议

请在 [Issues](https://github.com/tony3liu/dromx-stock/issues) 中说明使用场景、复现步骤、预期结果与实际结果。报错时可附上系统版本和经过脱敏的日志；不要贴出 API 密钥、个人持仓或其他私密信息。

较大的功能或交互调整建议先开 Issue 讨论，便于确认范围。

## 提交代码

1. Fork 仓库，从 `main` 创建自己的分支。
2. 根据[运行说明](webapp/README.md) 配置开发环境。
3. 完成修改，补充必要的文档和行为验证。
4. 提交 Pull Request，说明解决的问题、使用效果和验证结果。

请保持修改范围清晰，并保留原有许可与署名。

## 开发验证

在项目根目录、激活虚拟环境后：

```bash
python -m pip install -e ".[web,dev]"
python -m pytest tests/ -q -m "not integration"
```

前端修改还需执行：

```bash
cd webapp/frontend
npm ci
npm run build
```

调用真实外部服务的集成测试按需运行，需要自己的服务配置，可能产生费用。

## 许可

提交贡献即表示同意按项目的 [Apache License 2.0](LICENSE) 提供该贡献。
