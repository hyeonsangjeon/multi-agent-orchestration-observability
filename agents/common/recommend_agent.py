"""Dummy product recommendation plugin for beauty e-commerce demo."""

import json
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function


class RecommendPlugin:
    """Product recommendation plugin backed by mock catalog data."""

    def __init__(self) -> None:
        mock_path = Path(__file__).parent.parent.parent / "mock_data" / "products.json"
        with open(mock_path, encoding="utf-8") as f:
            self._products: list[dict] = json.load(f)

    @kernel_function(
        name="recommend_product",
        description="피부 타입이나 고민에 맞는 상품을 추천합니다. 예: '건성 피부에 좋은 크림 추천해줘'",
    )
    def recommend_product(
        self,
        query: Annotated[str, "사용자의 상품 추천 요청 쿼리"],
    ) -> Annotated[str, "추천 상품 목록 JSON"]:
        query_lower = query.lower()
        matched: list[dict] = []
        for p in self._products:
            skin_match = any(st in query_lower for st in p.get("skin_type", []))
            cat_match = p.get("category", "").lower() in query_lower
            name_match = p.get("name", "").lower() in query_lower or p.get("brand", "").lower() in query_lower
            if skin_match or cat_match or name_match:
                matched.append(p)

        if not matched:
            matched = self._products[:2]

        result = {
            "source": "RecommendAgent",
            "query": query,
            "recommendations": [
                {
                    "name": p["name"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "description": p["description"],
                    "skin_type": p["skin_type"],
                    "rating": p["rating"],
                }
                for p in matched[:3]
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
