"""Measure real HTTP RAG latency: 50 questions, five authenticated sessions."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import getpass
import json
import os
from pathlib import Path
import platform
import time
import uuid
from typing import Any

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://localhost:3000")
    parser.add_argument("--email", required=True, help="Demo Customer login")
    parser.add_argument(
        "--output",
        default="docs/reports/final-acceptance-20261029/performance-live.json",
    )
    args = parser.parse_args()
    password = os.getenv("VC_BENCH_PASSWORD") or getpass.getpass(
        "Demo customer password: "
    )
    questions = [
        "Làm sao đăng nhập hệ thống demo?",
        "Ticket có những trạng thái nào?",
        "Khi không có thông tin phù hợp thì tôi làm gì?",
        "Tôi cần gặp nhân viên hỗ trợ.",
        "Tôi có nên cung cấp OTP trong chat không?",
    ] * 10
    durations = []
    errors = []
    providers = set()

    def worker(index: int) -> tuple[list[float], list[dict[str, Any]], set[str]]:
        result = []
        failed = []
        seen = set()
        with httpx.Client(base_url=args.origin, timeout=120) as client:

            def post(path: str, payload: dict[str, Any]) -> httpx.Response:
                return client.post(
                    path,
                    json=payload,
                    headers={
                        "Origin": args.origin,
                        "X-Vietincare-Request": "1",
                        "Idempotency-Key": str(uuid.uuid4()),
                    },
                )

            login = post("/api/auth/login", {"email": args.email, "password": password})
            login.raise_for_status()
            for question in questions[index * 10 : (index + 1) * 10]:
                started = time.perf_counter()
                try:
                    chat = post("/api/chats", {"content": question})
                    chat.raise_for_status()
                    data = chat.json()
                    answer = post(
                        f"/api/chats/{data['id']}/messages/{data['messageId']}/answer",
                        {"language": "vi"},
                    )
                    answer.raise_for_status()
                    detail = client.get(f"/api/chats/{data['id']}")
                    detail.raise_for_status()
                    seen.add(detail.json().get("aiProvider", "unknown"))
                    result.append(time.perf_counter() - started)
                except httpx.HTTPError as error:
                    failed.append(
                        {
                            "type": type(error).__name__,
                            "http_status": getattr(
                                getattr(error, "response", None), "status_code", None
                            ),
                        }
                    )
        return result, failed, seen

    with ThreadPoolExecutor(max_workers=5) as pool:
        for result, failed, seen in pool.map(worker, range(5)):
            durations.extend(result)
            errors.extend(failed)
            providers.update(seen)
    durations.sort()
    p95 = (
        durations[max(0, __import__("math").ceil(len(durations) * 0.95) - 1)]
        if durations
        else None
    )
    report = {
        "questions": 50,
        "concurrent_sessions": 5,
        "successful": len(durations),
        "errors": errors,
        "p95_seconds": p95,
        "providers": sorted(providers),
        "machine": platform.platform(),
        "cpu": platform.processor(),
        "network_origin": args.origin,
        "knowledge_limit": 1000,
        "acceptance": (
            "PASS"
            if len(durations) == 50
            and not errors
            and p95 <= 5
            and providers <= {"gemini", "openai"}
            else "NOT_MET_OR_NOT_LIVE"
        ),
        "scope": "HTTP demo run; source grounding/answer quality must also be reviewed. Configure exact model and network in the release report.",
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True))
    if report["acceptance"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
