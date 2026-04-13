"""Dummy product search plugin for beauty e-commerce demo."""

import json
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function


class SearchPlugin:
    """Product search plugin backed by mock search index data."""

    def __init__(self) -> None:
        mock_path = Path(__file__).parent.parent.parent / "mock_data" / "search_index.json"
        with open(mock_path, encoding="utf-8") as f:
            self._index: list[dict] = json.load(f)

    @kernel_function(
        name="search_product",
        description="상품명, 가격, 재고 등 구체적인 상품 정보를 검색합니다. 예: '설화수 자음생 크림 가격 알려줘'",
    )
    def search_product(
        self,
        query: Annotated[str, "사용자의 상품 검색 쿼리"],
    ) -> Annotated[str, "검색 결과 JSON"]:
        query_lower = query.lower()
        matched: list[dict] = []
        for item in self._index:
            keywords = item.get("query_keywords", [])
            if any(kw.lower() in query_lower for kw in keywords):
                matched.append(item)

        if not matched:
            matched = self._index[:1]

        result = {
            "source": "SearchAgent",
            "query": query,
            "results": [
                {
                    "name": item["name"],
                    "price": item["price"],
                    "currency": item["currency"],
                    "availability": item["availability"],
                    "store_locations": item["store_locations"],
                    "promotions": item["promotions"],
                }
                for item in matched[:3]
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
