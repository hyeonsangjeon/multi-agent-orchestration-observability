"""Dummy policy guidance plugin for beauty e-commerce demo."""

import json
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function


class PolicyPlugin:
    """Policy guidance plugin backed by mock policy documents."""

    def __init__(self) -> None:
        mock_path = Path(__file__).parent.parent.parent / "mock_data" / "policies.json"
        with open(mock_path, encoding="utf-8") as f:
            self._policies: list[dict] = json.load(f)

    @kernel_function(
        name="lookup_policy",
        description="교환, 환불, 배송, 멤버십 등 정책 관련 안내를 합니다. 예: '교환 환불 정책 알려줘'",
    )
    def lookup_policy(
        self,
        query: Annotated[str, "사용자의 정책 관련 질문"],
    ) -> Annotated[str, "관련 정책 문서 JSON"]:
        query_lower = query.lower()
        keyword_map = {
            "교환": "교환/환불",
            "환불": "교환/환불",
            "반품": "교환/환불",
            "배송": "배송",
            "택배": "배송",
            "멤버십": "멤버십",
            "포인트": "멤버십",
            "적립": "멤버십",
            "vip": "멤버십",
        }

        matched_categories: set[str] = set()
        for keyword, category in keyword_map.items():
            if keyword in query_lower:
                matched_categories.add(category)

        matched = [p for p in self._policies if p.get("category") in matched_categories]

        if not matched:
            matched = self._policies

        result = {
            "source": "PolicyAgent",
            "query": query,
            "policies": [
                {
                    "title": p["title"],
                    "category": p["category"],
                    "content": p["content"],
                    "last_updated": p["last_updated"],
                }
                for p in matched
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
