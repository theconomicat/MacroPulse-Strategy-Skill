#!/usr/bin/env python3
"""Extract macro and narrative signals from news input.

The default adapter reads the sample JSON file. A future production adapter can
replace the fetch step while preserving the normalized signal contract.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_NEWS_INPUT = SKILL_DIR / "examples" / "sample-news-input.json"

RISK_TOPICS = {
    "cpi",
    "fomc",
    "rate hike",
    "rate cut",
    "inflation",
    "regulation",
    "sec",
    "liquidation",
    "hack",
    "insolvency",
    "exchange risk",
}
NARRATIVE_TOPICS = {
    "ai",
    "defi",
    "rwa",
    "restaking",
    "gaming",
    "meme",
    "infrastructure",
    "payments",
}
NARRATIVE_CANONICAL = {
    "ai": "AI",
    "defi": "DeFi",
    "rwa": "RWA",
    "restaking": "Restaking",
    "gaming": "Gaming",
    "meme": "Meme",
    "infrastructure": "Infrastructure",
    "payments": "Payments",
}
KNOWN_ASSETS = {"BTC", "ETH", "BNB", "SOL", "USDC", "USDT", "CAKE", "FET", "AAVE", "UNI"}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def contains_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) is not None


def canonical_narrative(value: str) -> str:
    lowered = value.strip().lower()
    return NARRATIVE_CANONICAL.get(lowered, value.strip())


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


@dataclass
class NewsAdapter:
    """Base adapter contract for news sources."""

    source: str

    def fetch(self, lookback: str) -> tuple[list[dict[str, Any]], list[str]]:
        raise NotImplementedError


@dataclass
class SampleNewsAdapter(NewsAdapter):
    input_path: Path

    def fetch(self, lookback: str) -> tuple[list[dict[str, Any]], list[str]]:
        payload = load_json(self.input_path)
        notes = [
            f"Loaded sample news input from {self.input_path}.",
            f"Lookback argument was accepted as metadata: {lookback}.",
        ]
        return normalize_news_items(payload), notes


@dataclass
class HttpNewsAdapter(NewsAdapter):
    """Optional JSON HTTP adapter for future news service integration.

    Set MACROPULSE_NEWS_API_URL to an endpoint that returns either
    {"items": [...]} or a raw JSON array of news items. Set
    MACROPULSE_NEWS_API_KEY only if the endpoint requires bearer auth.
    """

    fallback_path: Path

    def fetch(self, lookback: str) -> tuple[list[dict[str, Any]], list[str]]:
        endpoint = os.getenv("MACROPULSE_NEWS_API_URL")
        token = os.getenv("MACROPULSE_NEWS_API_KEY")
        if not endpoint:
            payload = load_json(self.fallback_path)
            return normalize_news_items(payload), [
                "MACROPULSE_NEWS_API_URL is not set; using sample news input.",
                f"Loaded sample news input from {self.fallback_path}.",
            ]

        url = endpoint
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}lookback={lookback}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return normalize_news_items(payload), [f"Loaded news items from {endpoint}."]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            payload = load_json(self.fallback_path)
            return normalize_news_items(payload), [
                f"News API request failed: {exc}",
                f"Using sample news input from {self.fallback_path}.",
            ]


def normalize_news_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items", [])
    else:
        items = []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "published_at": item.get("published_at"),
                "source": item.get("source", "unknown"),
                "credibility_score": float(item.get("credibility_score", 0.6)),
                "sentiment": float(item.get("sentiment", 0.0)),
                "impact_score": float(item.get("impact_score", 0.5)),
                "tags": [str(tag) for tag in item.get("tags", [])],
                "assets": [str(asset).upper() for asset in item.get("assets", [])],
                "narratives": [str(tag) for tag in item.get("narratives", [])],
            }
        )
    return normalized


def extract_signals_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "macro_sentiment": 0.0,
            "risk_event_score": 0.0,
            "dominant_topics": [],
            "asset_mentions": [],
            "asset_mention_counts": {},
            "narrative_tags": [],
            "narrative_counts": {},
            "summary": "No news items were available; signals are neutral.",
            "item_count": 0,
        }

    weighted_sentiment = 0.0
    sentiment_weight = 0.0
    risk_points = 0.0
    risk_weight = 0.0
    topic_counter: Counter[str] = Counter()
    asset_counter: Counter[str] = Counter()
    narrative_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    high_impact_titles: list[str] = []

    for item in items:
        tags = [tag.lower() for tag in item.get("tags", [])]
        title = str(item.get("title", ""))
        summary = str(item.get("summary", ""))
        text_blob = f"{title} {summary} {' '.join(tags)}".lower()
        credibility = clamp(float(item.get("credibility_score", 0.6)))
        impact = clamp(float(item.get("impact_score", 0.5)))
        sentiment = max(-1.0, min(1.0, float(item.get("sentiment", 0.0))))
        weight = max(0.05, credibility * impact)

        weighted_sentiment += sentiment * weight
        sentiment_weight += weight
        source_counter[str(item.get("source", "unknown"))] += 1

        for tag in item.get("tags", []):
            normalized_tag = str(tag).strip()
            if normalized_tag:
                topic_counter[normalized_tag] += 1

        for asset in item.get("assets", []):
            asset_counter[str(asset).upper()] += 1
        for asset in KNOWN_ASSETS:
            if asset.lower() in text_blob:
                asset_counter[asset] += 1

        for narrative in item.get("narratives", []):
            normalized_narrative = canonical_narrative(str(narrative))
            if normalized_narrative:
                narrative_counter[normalized_narrative] += 1
        for narrative in NARRATIVE_TOPICS:
            if contains_term(text_blob, narrative):
                narrative_counter[canonical_narrative(narrative)] += 1

        risk_hit_count = sum(1 for topic in RISK_TOPICS if topic in text_blob)
        risk_component = clamp((risk_hit_count * 0.18) + max(0.0, -sentiment) * 0.35 + impact * 0.30)
        risk_points += risk_component * weight
        risk_weight += weight

        if impact >= 0.7:
            high_impact_titles.append(title)

    macro_sentiment = weighted_sentiment / sentiment_weight if sentiment_weight else 0.0
    risk_event_score = risk_points / risk_weight if risk_weight else 0.0
    dominant_topics = [topic for topic, _ in topic_counter.most_common(8)]
    asset_mentions = [asset for asset, _ in asset_counter.most_common(10)]
    narrative_tags = [tag for tag, _ in narrative_counter.most_common(8)]

    if macro_sentiment < -0.25:
        sentiment_phrase = "macro tone is defensive"
    elif macro_sentiment > 0.25:
        sentiment_phrase = "macro tone is constructive"
    else:
        sentiment_phrase = "macro tone is mixed"

    risk_phrase = "risk events are elevated" if risk_event_score >= 0.65 else "risk events are contained"
    summary = f"{sentiment_phrase}; {risk_phrase}; dominant topics include {', '.join(dominant_topics[:3]) or 'none'}."

    return {
        "macro_sentiment": round(macro_sentiment, 4),
        "risk_event_score": round(risk_event_score, 4),
        "dominant_topics": dominant_topics,
        "asset_mentions": asset_mentions,
        "asset_mention_counts": dict(asset_counter.most_common()),
        "narrative_tags": narrative_tags,
        "narrative_counts": dict(narrative_counter.most_common()),
        "source_counts": dict(source_counter.most_common()),
        "high_impact_titles": high_impact_titles[:5],
        "summary": summary,
        "item_count": len(items),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract macro sentiment, risk events, asset mentions, and narrative tags from news input.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_NEWS_INPUT, help="Path to sample or normalized news JSON input.")
    parser.add_argument("--source", choices=["sample", "mock", "news-api"], default="sample", help="News adapter to use.")
    parser.add_argument("--lookback", default="7d", help="Lookback window metadata passed to live adapters.")
    parser.add_argument("--output", type=Path, help="Write extracted signals to this JSON file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.source in {"sample", "mock"}:
        adapter: NewsAdapter = SampleNewsAdapter(source=args.source, input_path=args.input)
    else:
        adapter = HttpNewsAdapter(source=args.source, fallback_path=args.input)

    items, notes = adapter.fetch(args.lookback)
    signals = extract_signals_from_items(items)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "adapter_notes": notes,
        "signals": signals,
    }
    output = json.dumps(payload, indent=2, sort_keys=False)

    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"News signals written to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
