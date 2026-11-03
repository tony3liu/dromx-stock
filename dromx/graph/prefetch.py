"""Run-start context 并行预取

run-start 阶段要在图启动前构建 5-8 项上下文（past/instrument/portfolio/
market/overnight/pattern/foreign_flow/instrument_type），它们互相独立却长期
串行执行（每项都是网络/文件/LLM 阻塞调用），图还没开始就可能花掉几十秒。

这些 builder 均为纯查询函数（各自内部 try/except degrade，无共享状态），
用线程池并行即可，图拓扑与 stream 消费方式完全不用动。
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)


def parallel_prefetch(
    tasks: dict[str, Callable[[], Any]],
    *,
    max_workers: int = 8,
    label: str = "prefetch",
) -> dict[str, Any]:
    """并行执行一组互相独立的上下文构建任务，按原名返回结果 dict。

    - 任务间无依赖、无共享状态（调用方保证）；任一任务抛异常会整体抛出
      （与原串行行为一致——各 builder 内部已自行 degrade 的不会走到这）。
    - 返回 dict 的 key 与 tasks 一致，value 为任务返回值（可为 tuple 等任意类型）。
    """
    if not tasks:
        return {}
    t0 = time.monotonic()
    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=min(len(tasks), max_workers)) as ex:
        futs = {name: ex.submit(fn) for name, fn in tasks.items()}
        for name, fut in futs.items():
            results[name] = fut.result()
    logger.info("%s: %d tasks parallel-done in %.1fs", label, len(tasks), time.monotonic() - t0)
    return results
