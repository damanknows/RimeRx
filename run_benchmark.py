import sys, asyncio, argparse
from scripts.run_benchmark import run_benchmark, check_credentials, compute_per

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RimeRx benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to run")
    args = parser.parse_args()

    check_credentials()
    asyncio.run(run_benchmark(limit=args.limit))
