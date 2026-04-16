from __future__ import annotations

import argparse

from app.config import load_settings
from app.pipeline import ResearchPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local research orchestrator.")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML settings file.",
    )
    parser.add_argument(
        "--objective",
        default=None,
        help="Override the configured research objective.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Prompt/output profile, for example early_discovery_ai_infra or weekly_scarcity_brief.",
    )
    parser.add_argument(
        "--healthcheck",
        action="store_true",
        help="Check configured local services and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)
    if args.profile:
        settings.pipeline.profile = args.profile
    pipeline = ResearchPipeline(settings)
    if args.healthcheck:
        failures = 0
        for service, status in pipeline.healthcheck():
            print(f"{service}: {status}")
            if status.startswith("error"):
                failures += 1
        raise SystemExit(1 if failures else 0)
    objective = args.objective or settings.pipeline.objective
    try:
        artifacts = pipeline.run(objective)
    except Exception as exc:
        print(f"Run failed: {exc}")
        raise SystemExit(1) from exc
    print(f"Run complete: {artifacts.manifest.run_dir}")
    if artifacts.brief_path:
        print(f"Brief: {artifacts.brief_path}")


if __name__ == "__main__":
    main()
