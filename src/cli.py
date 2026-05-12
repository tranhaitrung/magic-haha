from __future__ import annotations

import argparse
from pathlib import Path

from src.config_loader import load_config
from src.logging_setup import setup_logging
from src.orchestrator import ensure_local_directories, pick_next_input_file, process_single_input_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Facebook Social Affiliate Channel Scanner")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--input", help="Path to a single input .xlsx file")
    parser.add_argument("--watch-dir", help="Watch mode for inbox directory (single-run pick)")
    parser.add_argument("--profile", help="Optional browser profile path")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to load config: {exc}")
        return 1

    logger = setup_logging(config.paths.log_dir)
    ensure_local_directories(config)

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: Input file not found: {input_path}")
            return 1

        temp_input = config.paths.inbox_dir / input_path.name
        if input_path.resolve() != temp_input.resolve():
            temp_input.write_bytes(input_path.read_bytes())

        result = process_single_input_file(temp_input, config, logger, profile_path=args.profile)
        logger.info(
            "Done. total=%s success=%s failed=%s output=%s",
            result.total_channels,
            result.success_channels,
            result.failed_channels,
            result.output_file,
        )
        return 0

    watch_dir = Path(args.watch_dir) if args.watch_dir else config.paths.inbox_dir
    if not watch_dir.exists():
        logger.error("Watch directory does not exist: %s", watch_dir)
        return 1

    next_file = pick_next_input_file(watch_dir)
    if not next_file:
        logger.info("No input files found in %s", watch_dir)
        return 0

    result = process_single_input_file(next_file, config, logger, profile_path=args.profile)
    logger.info(
        "Done. total=%s success=%s failed=%s output=%s",
        result.total_channels,
        result.success_channels,
        result.failed_channels,
        result.output_file,
    )
    return 0
