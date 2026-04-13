"""Section 1b: OK Architecture Mirror — ChatCompletionAgent + plugins.

Mirrors the ok_sk_agent_flow pattern: supervisor agent with plugins,
combined routing + response in a single invoke() call.
"""

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatHistory

from agents.common.recommend_agent import RecommendPlugin
from agents.common.search_agent import SearchPlugin
from agents.common.policy_agent import PolicyPlugin

SUPERVISOR_INSTRUCTIONS = """\
You are a beauty e-commerce supervisor agent.
You have access to these tools:
- recommend: 상품 추천 (피부 타입별 제품 추천, 성분 분석)
- search: 상품 검색 (가격, 재고, 매장 위치, 프로모션)
- policy: 정책 안내 (교환/환불, 배송, 멤버십/포인트)

Analyze the user's intent and call the appropriate tool.
Based on the tool result, provide a helpful answer in Korean.
"""


async def run_ok_pattern_supervisor(
    query: str,
    kernel: Kernel,
) -> str:
    """Run the OK architecture mirror (Section 1b).

    Uses ChatCompletionAgent with plugins — routing decision is buried inside
    the LLM call with no hook available.
    """
    # 1. Build plugins (same as OK's get_kernel_instance)
    recommend_plugin = RecommendPlugin()
    search_plugin = SearchPlugin()
    policy_plugin = PolicyPlugin()

    # 2. Create supervisor agent (same as OK's ChatCompletionAgent)
    # <<< ROUTING DECISION HAPPENS HERE — buried inside LLM call, no hook available >>>
    supervisor = ChatCompletionAgent(
        kernel=kernel,
        name="Supervisor",
        instructions=SUPERVISOR_INSTRUCTIONS,
        plugins=[recommend_plugin, search_plugin, policy_plugin],
    )

    # 3. Build chat history
    history = ChatHistory()
    history.add_user_message(query)

    # 4. Invoke (same as OK's invoke_stream)
    # <<< TOOL SELECTION — no separate logging, combined with response generation >>>
    # <<< This is why the customer cannot see which agent was selected or why >>>
    response_parts: list[str] = []
    async for message in supervisor.invoke(history):
        if message.content:
            response_parts.append(message.content)

    return "\n".join(response_parts)
