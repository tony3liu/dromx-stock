# DromX

> Multi-Agent LLM Financial Trading Framework — agent loop + skills + 取证型分析。

基于 DromX 架构完全重构。核心能力围绕 **agent loop + skills**(不写死 workflow):

- **agent loop + skills**:分析师可调工具迭代思考(LLM 用工具深挖),skill 可插拔方法论,按 regime/instrument/market 自动挂载
- **取证型 + 预测型分析**:异常检测 + 锚点偏差竞争 + 算法精度证据 + 跨市场传导 + 外资筹码
- **Orchestrator**:动态选分析师 + skill(LLM 判断 instrument/regime,不硬编码)
- **DepthController**:信号清晰度 + 事件冲击 → conclude/standard/deep_dive
- **Re-Analysis**:事件触发重审视(前向节点,不反向遍历)
- **PM with tools**:read_analyst_report(回溯原始报告)+ position_simulate(定量 P&L)+ web_search(serper google)
- **多数据源**:tencent/mootdx(中)/eastmoney/sec(US)/yfinance/naver(韩)/FRED/Polymarket
- **多 LLM provider**:OpenAI/DeepSeek/Anthropic/Google/Bedrock/Ollama
- **webapp**:FastAPI + SSE + React(Tailwind)
- **web_search**:serper.dev 数据源失败时 google 搜(通用 fallback,CXMT 定价/当日实时)

## Quick start

```bash
conda activate dromx
conda run --no-capture-output -n tradingagents uvicorn webapp.backend.main:app --port 8077 --log-level info --reload
```

## Config (`.env`)

- `DEEPSEEK_API_KEY` / `SERPER_API_KEY`(serper.dev google 搜)
- `DROMX_OUTPUT_LANGUAGE=中文`
- `DROMX_LLM_PROVIDER` / `DROMX_DEEP_THINK_LLM`

## Architecture

LangGraph + agent loop + skills(21 内置)。Python 包名 `dromx`(import),项目名 DromX。

## License

私有项目(基于开源 DromX 架构重构)。
