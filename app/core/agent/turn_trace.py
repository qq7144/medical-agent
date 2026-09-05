"""回合决策轨迹（TurnTrace）。

MedLattice 每个回复都附带一份“可解释的决策元数据”：
- 走了哪个意图、规划了几步、是否重规划；
- 检索命中了哪些来源、公共知识库命中多少条；
- 事实校验 / 免责声明 / 确认交互等安全闸门状态。

刻意只收录元数据，不回传档案正文、检索原文或记忆内容，
避免 trace 本身成为新的隐私泄漏面。
"""
from __future__ import annotations

from typing import Any

from app.config.compliance_rules import STANDARD_DISCLAIMER
from app.config.settings import settings

_FACT_CHECK_WARN_MARK = "以上部分健康信息未能从当前知识库中充分验证"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_turn_trace(state: dict[str, Any], *, duration_ms: int) -> dict[str, Any]:
    """从引擎终态整理出可审计的回合轨迹。"""
    plan = _as_dict(state.get("execution_plan"))
    steps = _as_list(plan.get("steps"))
    results = _as_dict(state.get("plan_step_results"))
    retrieved = _as_dict(state.get("retrieved_knowledge"))
    final_response = state.get("final_response") or state.get("llm_output") or ""
    has_error = bool(state.get("error_msg"))

    public_kb = retrieved.get("public_kb")
    public_kb_hits = len(public_kb) if isinstance(public_kb, list) else 0

    tool_targets: list[str] = []
    for step in steps:
        if isinstance(step, dict) and step.get("target_type") == "tool":
            target = step.get("target_name")
            if target:
                tool_targets.append(str(target))

    failed_steps: list[str] = []
    for step_id, step_result in results.items():
        if isinstance(step_result, dict) and step_result.get("error_msg"):
            failed_steps.append(str(step_id))

    return {
        "schema_version": 1,
        "pipeline": "medlattice",
        "duration_ms": int(duration_ms),
        "finished_ok": not has_error,
        "intent": state.get("intent", ""),
        "planning": {
            "strategy": plan.get("strategy", ""),
            "requested_steps": len(steps),
            "completed_steps": len(results),
            "failed_steps": failed_steps[:10],
            "tool_targets": tool_targets[:10],
            "replan_count": int(state.get("replan_count") or 0),
        },
        "retrieval": {
            "selective_rag": bool(settings.ENABLE_SELECTIVE_RAG),
            "knowledge_sources": [key for key in retrieved.keys() if key != "public_kb"],
            "public_kb_hits": public_kb_hits,
        },
        "guards": {
            "disclaimer_appended": bool(
                settings.FORCE_DISCLAIMER and final_response and STANDARD_DISCLAIMER in final_response
            ),
            "fact_check_warning": _FACT_CHECK_WARN_MARK in final_response,
            "confirmation_required": bool(state.get("needs_confirmation")),
            "input_check": bool(settings.ENABLE_INPUT_CHECK),
            "output_check": bool(settings.ENABLE_OUTPUT_CHECK),
        },
        "output": {
            "response_mode": state.get("response_mode", ""),
            "chars": len(final_response or ""),
            "error_msg": state.get("error_msg", "") if has_error else "",
        },
    }
