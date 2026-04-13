"""Section 1a: Generic black-box supervisor — single system prompt, NO plugins.

A single LLM completion handles routing + response generation with zero trace.
"""

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory

BLACKBOX_SYSTEM_PROMPT = """\
You are a beauty e-commerce assistant that handles three types of requests:
1. 상품 추천 (Product recommendations) — 피부 타입, 성분 분석 기반 추천
2. 상품 검색 (Product search) — 가격, 재고, 매장 정보 조회
3. 정책 안내 (Policy guidance) — 교환, 환불, 배송, 멤버십 안내

Answer the user's question directly in Korean.
Do NOT mention which category you're using.
Do NOT reveal your internal reasoning about which type of request this is.
Just answer naturally as a single assistant.
"""


async def run_blackbox_supervisor(
    query: str,
    kernel: Kernel,
    service_id: str = "azure_openai",
) -> str:
    """Run a single-completion black-box supervisor (Section 1a).

    No plugins, no function calling, no routing trace.
    """
    chat_history = ChatHistory(system_message=BLACKBOX_SYSTEM_PROMPT)
    chat_history.add_user_message(query)

    chat_service = kernel.get_service(service_id)
    response = await chat_service.get_chat_message_contents(
        chat_history=chat_history,
    )
    return response[0].content
