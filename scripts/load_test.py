"""Load test for NFR-1.1: vacancy search with filters under N concurrent connections."""

import argparse
import asyncio
import random
import statistics
import sys
import time

import httpx

DOMAINS = ["PYTHON", "DOTNET", "JAVA", "GAMEDEV", "PROJECT_MANAGEMENT", "QA", "EMBEDDED"]
FORMATS = ["REMOTE", "OFFICE", "HYBRID"]
COMPANY_TYPES = ["PRODUCT", "OUTSOURCE", "OUTSTAFF", "STARTUP"]
ENGLISH = ["BEGINNER", "INTERMEDIATE", "UPPER_INTERMEDIATE", "ADVANCED"]


def random_filters(rng: random.Random) -> dict[str, str | int]:
    candidates: dict[str, str | int] = {
        "domain": rng.choice(DOMAINS),
        "experience_years": rng.randint(0, 8),
        "salary_from": rng.randrange(500, 6_000, 500),
        "work_format": rng.choice(FORMATS),
        "company_type": rng.choice(COMPANY_TYPES),
        "english_level": rng.choice(ENGLISH),
        "sort_by": rng.choice(["created_at", "salary_max"]),
    }
    keys = rng.sample(sorted(candidates), k=rng.randint(1, 4))
    return {key: candidates[key] for key in keys}


async def worker(
    client: httpx.AsyncClient,
    requests: int,
    rng: random.Random,
    latencies: list[float],
    errors: list[str],
) -> None:
    for _ in range(requests):
        started = time.perf_counter()
        try:
            response = await client.get("/api/v1/vacancies", params=random_filters(rng))
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code == 200:
                latencies.append(elapsed)
            else:
                errors.append(f"HTTP {response.status_code}")
        except httpx.HTTPError as exc:
            errors.append(type(exc).__name__)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


async def run(base_url: str, concurrency: int, per_client: int, threshold_ms: float) -> int:
    latencies: list[float] = []
    errors: list[str] = []
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=30) as client:
        await client.get("/health")
        started = time.perf_counter()
        await asyncio.gather(
            *(
                worker(client, per_client, random.Random(index), latencies, errors)
                for index in range(concurrency)
            )
        )
        duration = time.perf_counter() - started

    total = len(latencies) + len(errors)
    print(f"Requests: {total}, concurrency: {concurrency}, duration: {duration:.1f}s")
    print(f"Throughput: {total / duration:.0f} req/s, errors: {len(errors)}")
    if latencies:
        print(
            "Latency ms: "
            f"mean={statistics.fmean(latencies):.1f} "
            f"p50={percentile(latencies, 0.50):.1f} "
            f"p95={percentile(latencies, 0.95):.1f} "
            f"p99={percentile(latencies, 0.99):.1f} "
            f"max={max(latencies):.1f}"
        )
    if errors or not latencies:
        print("FAIL: some requests failed")
        return 1
    p95 = percentile(latencies, 0.95)
    verdict = "PASS" if p95 <= threshold_ms else "FAIL"
    print(f"{verdict}: p95 {p95:.1f} ms vs threshold {threshold_ms:.0f} ms (NFR-1.1)")
    return 0 if verdict == "PASS" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--requests-per-client", type=int, default=20)
    parser.add_argument("--threshold-ms", type=float, default=250)
    args = parser.parse_args()
    sys.exit(
        asyncio.run(
            run(args.base_url, args.concurrency, args.requests_per_client, args.threshold_ms)
        )
    )


if __name__ == "__main__":
    main()
