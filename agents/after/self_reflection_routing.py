"""Section 3: Self-Reflection Routing — explicit reflect() function.

Uses the same transparent routing setup as Section 2, plus:
- After agent responds, an explicit reflect() function evaluates the response
- If reflection fails, the response is REPLACED via direct agent.invoke()
- This pattern is framework-portable (SK / MAF / LangGraph)
"""

import json
from dataclasses import dataclass

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory


@dataclass
class ReflectionResult:
    """Result of self-reflection evaluation."""

    intent_match: bool
    sufficient_info: bool
    should_reroute: bool
    reroute_to: str | None
    reason: str


# Business rules for rule-based pre-check (before LLM reflection).
# Can be externalized to JSON/YAML config later.
BUSINESS_RULES: dict[str, list[str] | str] = {
    "price_keywords": ["가격", "얼마", "프로모션", "할인", "세일"],
    "price_agent": "SearchAgent",
}


REFLECTION_PROMPT_TEMPLATE = """\
You are a quality evaluator for a beauty e-commerce chatbot.

Given:
- Original user query: {query}
- Agent that responded: {agent_name}
- Agent response: {agent_response}
- KB results used: {kb_results}

Evaluate the response quality:
1. Does the response match the user's original intent?
2. Is the information sufficient to fully answer the query?
3. Should this be re-routed to a different agent for a better answer?

Available agents for re-routing:
- RecommendAgent: 상품 추천 (피부 타입별 제품 추천, 성분 분석)
- SearchAgent: 상품 검색 (가격 조회, 재고, 프로모션)
- PolicyAgent: 정책 안내 (교환/환불, 배송, 멤버십)

Respond in JSON only (no markdown fences):
{{"intent_match": true/false, "sufficient_info": true/false, "should_reroute": true/false, "reroute_to": "<agent_name or null>", "reason": "<한국어로 판단 이유>"}}
"""


async def reflect(
    query: str,
    agent_name: str,
    agent_response: str,
    kb_results: list[dict],
    kernel: Kernel,
    service_id: str = "azure_openai",
) -> ReflectionResult:
    """Explicit self-reflection — NOT tied to any SK framework hook.

    This pattern is portable across SK, MAF, and LangGraph.

    Two-phase check:
    1. Rule-based pre-check (no LLM call, fast)
    2. LLM-based evaluation (if rules don't trigger)
    """
    # Phase 1: Rule-based pre-check
    price_keywords = BUSINESS_RULES.get("price_keywords", [])
    price_agent = BUSINESS_RULES.get("price_agent", "SearchAgent")
    for kw in price_keywords:
        if kw in query and agent_name != price_agent:
            return ReflectionResult(
                intent_match=True,
                sufficient_info=False,
                should_reroute=True,
                reroute_to=str(price_agent),
                reason=f"비즈니스 규칙: '{kw}' 키워드 감지 → {price_agent} 필수",
            )

    # Phase 2: LLM-based evaluation
    prompt = REFLECTION_PROMPT_TEMPLATE.format(
        query=query,
        agent_name=agent_name,
        agent_response=agent_response,
        kb_results=json.dumps(kb_results, ensure_ascii=False),
    )

    chat_history = ChatHistory()
    chat_history.add_user_message(prompt)

    chat_service = kernel.get_service(service_id)
    response = await chat_service.get_chat_message_contents(
        chat_history=chat_history,
        settings=AzureChatPromptExecutionSettings(),
    )

    raw = response[0].content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines).strip()

    try:
        parsed = json.loads(raw)
        return ReflectionResult(
            intent_match=parsed.get("intent_match", True),
            sufficient_info=parsed.get("sufficient_info", True),
            should_reroute=parsed.get("should_reroute", False),
            reroute_to=parsed.get("reroute_to"),
            reason=parsed.get("reason", ""),
        )
    except (json.JSONDecodeError, AttributeError):
        return ReflectionResult(
            intent_match=False,
            sufficient_info=False,
            should_reroute=False,
            reroute_to=None,
            reason=f"⚠️ REFLECTION_PARSE_FAILED: {raw[:200]}",
        )
