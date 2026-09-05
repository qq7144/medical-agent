"""执行阶段注册表：把一轮咨询拆成可观测、可复用的阶段清单。

MedLattice 的设计约定：
- 图模式（LangGraph StateGraph）按 STAGE_SEQUENCE 挂载节点；
- 流式模式按同一份清单逐段推进并上报进度；
- 阶段标签直接用于前端诊断面板，避免“图路径”与“流式路径”
  各自维护一套阶段列表而逐渐漂移。
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core.agent import nodes

StageFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class StageSpec:
    key: str
    label: str
    fn: StageFn


STAGE_SEQUENCE: tuple[StageSpec, ...] = (
    StageSpec(key="input_check", label="安全检入", fn=nodes.input_check),
    StageSpec(key="mem_load", label="记忆加载", fn=nodes.memory_load),
    StageSpec(key="intent_node", label="意图分诊", fn=nodes.intent_recognition),
    StageSpec(key="entities", label="实体抽取", fn=nodes.entity_extraction),
    StageSpec(key="knowledge", label="知识检索", fn=nodes.knowledge_retrieve),
    StageSpec(key="plan", label="任务规划", fn=nodes.plan_node),
    StageSpec(key="execute", label="子任务执行", fn=nodes.execute_node),
    StageSpec(key="reconcile", label="结果整合", fn=nodes.reconcile_node),
    StageSpec(key="response_plan", label="回复策略", fn=nodes.response_plan),
    StageSpec(key="llm", label="文本生成", fn=nodes.llm_generate),
    StageSpec(key="fact_check", label="事实校验", fn=nodes.fact_check),
    StageSpec(key="out", label="输出合规", fn=nodes.output_check_and_disclaimer),
    StageSpec(key="commit", label="事实提交", fn=nodes.commit_gate),
    StageSpec(key="mem", label="记忆更新", fn=nodes.memory_update),
    StageSpec(key="err", label="异常收口", fn=nodes.error_finalize),
)

STAGE_BY_KEY = {stage.key: stage for stage in STAGE_SEQUENCE}

# 进入 LLM 文本生成前的编排阶段（流式模式先逐步跑完并上报进度）
PRE_LLM_STAGES = STAGE_SEQUENCE[:6]
