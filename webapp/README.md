# DromX Web 运行说明

产品介绍与最短启动步骤见[项目首页](../README.md)。本页补充配置、常见问题与部署说明。

## 环境与安装

准备 Python 3.10+、Node.js 22.12+，以及可用的模型服务或已启动的本地模型。在项目根目录运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[web]"
python -m uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8077
```

Windows 使用 `python -m venv .venv` 创建环境，PowerShell 中执行 `.venv\Scripts\Activate.ps1` 激活；后续命令相同。

另开终端，在 `webapp/frontend` 目录运行：

```bash
npm ci
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)。前端会将 API 请求转发到本机的 8077 端口。

## 配置模型与数据源

在「应用配置」中选择提供商、填写密钥、设置快速模型与深度模型，然后保存。模型名称应与服务商当前支持的名称一致。自定义兼容服务还需填写 API 地址。

可选的联网搜索、宏观指标和财经快讯密钥也在该页面配置。未配置的数据服务可能无法使用，其他功能的可用性取决于对应数据源。

也可以复制根目录的 `.env.example` 为 `.env`，填写所需密钥。模型与语言配置使用 `DROMX_*` 环境变量，例如：

```dotenv
DROMX_LLM_PROVIDER=deepseek
DROMX_QUICK_THINK_LLM=deepseek-chat
DROMX_DEEP_THINK_LLM=deepseek-reasoner
DROMX_OUTPUT_LANGUAGE=中文
DEEPSEEK_API_KEY=your-api-key
```

页面保存的配置优先于 `.env`，清除页面配置后会回落到环境配置。

## 本地模型

使用 Ollama 时，先启动服务并下载模型，再在「应用配置」中将提供商设为 `ollama`，填写已下载的模型名称。默认连接本机 `http://localhost:11434/v1`；远程服务可通过 `OLLAMA_BASE_URL` 指定。

投研任务需要模型支持工具调用，深度报告还依赖结构化输出。请根据所选模型的能力判断可用功能。

## 保存位置与访问

配置保存在 `~/.dromx/user_settings.json`，研究运行记录保存在 `~/.dromx/web_runs/`。配置包含所填写的密钥，请勿分享配置文件或将其提交到仓库。

默认启动命令只让后端监听本机。如需供其他人访问，请设置 `DROMX_WEB_PASSWORD` 启用密码登录，并使用 HTTPS 反向代理；前端开发服务器用于本地开发。

## 常见问题

| 问题 | 检查方式 |
| --- | --- |
| 页面打开了但不能请求数据 | 确认后端已启动，且监听 8077 端口；查看后端终端错误 |
| 模型报鉴权或模型不存在 | 检查提供商、密钥、模型名称及自定义 API 地址是否匹配 |
| 某个市场或数据源没有结果 | 检查该服务的网络与密钥，尝试其他标的或稍后重试 |
| 深度分析耗时较长 | 等待页面进度更新，或使用停止按钮结束任务；更换模型会影响速度与费用 |
| 修改 `.env` 后没有生效 | 检查页面是否保存了同名配置，并重启后端 |

开发贡献、测试和前端构建见[贡献指南](../CONTRIBUTING.md)。
