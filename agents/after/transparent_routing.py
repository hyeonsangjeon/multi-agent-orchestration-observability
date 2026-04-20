"""Section 2: Transparent Routing — AgentGroupChat + KernelFunctionSelectionStrategy.

Routing is separated from response generation. Selection function returns structured
JSON with agent, reason, and confidence. result_parser logs the decision and returns
only the agent name.
"""

import json
import logging
from typing import Callable

from opentelemetry import trace
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

from agents.common.recommend_agent import RecommendPlugin
from agents.common.search_agent import SearchPlugin
from agents.common.policy_agent import PolicyPlugin
from utils.logging_config import log_routing_decision

# Agent names — must match exactly what the selection LLM returns
RECOMMEND_AGENT = "RecommendAgent"
SEARCH_AGENT = "SearchAgent"
POLICY_AGENT = "PolicyAgent"

VALID_AGENTS = {RECOMMEND_AGENT, SEARCH_AGENT, POLICY_AGENT}
AGENT_ALIASES: dict[str, str] = {
    "recommendagent": RECOMMEND_AGENT,
    "recommend agent": RECOMMEND_AGENT,
    "recommend": RECOMMEND_AGENT,
    "searchagent": SEARCH_AGENT,
    "search agent": SEARCH_AGENT,
    "search": SEARCH_AGENT,
    "policyagent": POLICY_AGENT,
    "policy agent": POLICY_AGENT,
    "policy": POLICY_AGENT,
}

SELECTION_PROMPT = """\
You are a routing classifier for a beauty e-commerce chatbot.

Given a user query, determine which agent should handle it.
Choose EXACTLY ONE from these agents: {{$_agent_}}

Agent descriptions:
- RecommendAgent: 상품 추천 — 피부 타입별 제품 추천, 성분 분석, 루틴 추천
- SearchAgent: 상품 검색 — 가격 조회, 재고 확인, 매장 위치, 프로모션 정보
- PolicyAgent: 정책 안내 — 교환/환불, 배송, 멤버십/포인트 정책

Respond in JSON only (no markdown fences):
{"agent": "<agent_name>", "reason": "<한국어 선택 이유>", "confidence": <0.0~1.0>, "alternatives": ["<other_agent>"]}

CONVERSATION:
{{$_history_}}
"""

TERMINATION_PROMPT = """\
Examine the RESPONSE below. If the assistant has provided a substantive answer
to the user's question, respond with "yes". Otherwise respond with "no".

RESPONSE:
{{$lastmessage}}
"""


def create_result_parser(
    logger: logging.Logger,
    tracer: trace.Tracer,
    query: str,
    override_rules: dict[str, str] | None = None,
) -> Callable:
    """Create a result_parser that logs routing decisions and applies overrides."""

    def parser(result) -> str:
        raw = str(result.value[0]).strip() if result.value[0] is not None else RECOMMEND_AGENT

        with tracer.start_as_current_span("routing_decision") as span:
            # Parse JSON from LLM response
            try:
                # Strip markdown fences if present
                clean = raw
                if clean.startswith("```"):
                    lines = clean.split("\n")
                    lines = [l for l in lines if not l.startswith("```")]
                    clean = "\n".join(lines)
                parsed = json.loads(clean)
                agent_name = parsed.get("agent", RECOMMEND_AGENT)
                reason = parsed.get("reason", "")
                confidence = float(parsed.get("confidence", 0.0))
                alternatives = parsed.get("alternatives", [])
            except (json.JSONDecodeError, AttributeError, ValueError):
                agent_name = raw.strip()
                reason = "direct selection (non-JSON response)"
                confidence = 0.8
                alternatives = []

            # Normalize agent name if LLM returned a variant
            if agent_name not in VALID_AGENTS:
                normalized = agent_name.lower().strip()
                agent_name = AGENT_ALIASES.get(normalized, RECOMMEND_AGENT)

            # Check override rules
            override_applied = False
            if override_rules:
                for substring, target_agent in override_rules.items():
                    if substring in query:
                        agent_name = target_agent
                        override_applied = True
                        reason = f"Override: '{substring}' detected → {target_agent}"
                        break

            # Log structured routing decision
            log_routing_decision(
                logger,
                query=query,
                selected_agent=agent_name,
                reason=reason,
                confidence=confidence,
                alternatives_considered=alternatives,
                override_applied=override_applied,
            )

            # Set OTel span attributes
            span.set_attribute("routing.agent", agent_name)
            span.set_attribute("routing.reason", reason)
            span.set_attribute("routing.confidence", confidence)
            span.set_attribute("routing.override_applied", override_applied)
            span.set_attribute("routing.query", query)

        return agent_name

    return parser


def build_transparent_routing_chat(
    kernel: Kernel,
    logger: logging.Logger,
    tracer: trace.Tracer,
    query: str,
    override_rules: dict[str, str] | None = None,
) -> tuple[AgentGroupChat, dict[str, ChatCompletionAgent]]:
    """Build an AgentGroupChat with transparent routing (Section 2).

    Returns the chat instance and a dict of agent name → agent object.
    """
    # Create 3 ChatCompletionAgents with plugins
    recommend_agent = ChatCompletionAgent(
        kernel=kernel,
        name=RECOMMEND_AGENT,
        instructions=(
            "당신은 뷰티 상품 추천 전문가입니다. "
            "사용자의 피부 타입과 고민에 맞는 상품을 추천하세요. 한국어로 답변하세요."
        ),
        plugins=[RecommendPlugin()],
    )
    search_agent = ChatCompletionAgent(
        kernel=kernel,
        name=SEARCH_AGENT,
        instructions=(
            "당신은 뷰티 상품 검색 전문가입니다. "
            "상품 가격, 재고, 프로모션 정보를 정확히 제공하세요. 한국어로 답변하세요."
        ),
        plugins=[SearchPlugin()],
    )
    policy_agent = ChatCompletionAgent(
        kernel=kernel,
        name=POLICY_AGENT,
        instructions=(
            "당신은 뷰티 커머스 정책 안내 전문가입니다. "
            "교환/환불, 배송, 멤버십 정책을 정확히 안내하세요. 한국어로 답변하세요."
        ),
        plugins=[PolicyPlugin()],
    )

    agents = {
        RECOMMEND_AGENT: recommend_agent,
        SEARCH_AGENT: search_agent,
        POLICY_AGENT: policy_agent,
    }

    # Selection strategy
    selection_function = KernelFunctionFromPrompt(
        function_name="routing_selection",
        prompt=SELECTION_PROMPT,
    )
    selection_function.prompt_template.allow_dangerously_set_content = True

    history_reducer = ChatHistoryTruncationReducer(target_count=1)

    # Termination strategy — stop after the selected agent responds
    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=TERMINATION_PROMPT,
    )
    termination_function.prompt_template.allow_dangerously_set_content = True

    chat = AgentGroupChat(
        agents=[recommend_agent, search_agent, policy_agent],
        selection_strategy=KernelFunctionSelectionStrategy(
            function=selection_function,
            kernel=kernel,
            result_parser=create_result_parser(logger, tracer, query, override_rules),
            history_variable_name="_history_",
            history_reducer=history_reducer,
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[recommend_agent, search_agent, policy_agent],
            function=termination_function,
            kernel=kernel,
            # Strict equality on the trimmed lower-cased result, so substrings
            # like "yesterday" or "not yes" do not accidentally terminate.
            result_parser=lambda result: str(result.value[0]).strip().lower() == "yes",
            history_variable_name="lastmessage",
            maximum_iterations=2,
            history_reducer=history_reducer,
        ),
    )

    return chat, agents
