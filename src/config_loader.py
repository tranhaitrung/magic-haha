from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PathsConfig:
    inbox_dir: Path
    processing_dir: Path
    output_dir: Path
    archive_dir: Path
    error_dir: Path
    log_dir: Path


@dataclass
class ScanConfig:
    max_posts_per_channel: int
    max_scroll_times: int
    max_comment_expand: int
    scroll_pause_min_ms: int
    scroll_pause_max_ms: int
    action_delay_min_ms: int
    action_delay_max_ms: int
    redirect_timeout_ms: int
    channels_per_hour_limit: int
    consecutive_login_fail_limit: int
    channel_page_timeout_ms: int
    worker_count: int = 1


@dataclass
class AppConfig:
    paths: PathsConfig
    eco_domains: list[str]
    shopee_domains: list[str]
    scan: ScanConfig


def _require_keys(data: dict, keys: list[str], section: str) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"Missing keys in {section}: {', '.join(missing)}")


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    _require_keys(raw, ["paths", "eco_domains", "shopee_domains", "scan"], "root")
    _require_keys(
        raw["paths"],
        ["inbox_dir", "processing_dir", "output_dir", "archive_dir", "error_dir", "log_dir"],
        "paths",
    )

    paths = PathsConfig(
        inbox_dir=Path(raw["paths"]["inbox_dir"]),
        processing_dir=Path(raw["paths"]["processing_dir"]),
        output_dir=Path(raw["paths"]["output_dir"]),
        archive_dir=Path(raw["paths"]["archive_dir"]),
        error_dir=Path(raw["paths"]["error_dir"]),
        log_dir=Path(raw["paths"]["log_dir"]),
    )

    scan_raw = raw["scan"]
    _require_keys(
        scan_raw,
        [
            "max_posts_per_channel",
            "max_scroll_times",
            "max_comment_expand",
            "scroll_pause_min_ms",
            "scroll_pause_max_ms",
            "action_delay_min_ms",
            "action_delay_max_ms",
            "redirect_timeout_ms",
            "channels_per_hour_limit",
            "consecutive_login_fail_limit",
            "channel_page_timeout_ms",
        ],
        "scan",
    )

    scan = ScanConfig(
        max_posts_per_channel=int(scan_raw["max_posts_per_channel"]),
        max_scroll_times=int(scan_raw["max_scroll_times"]),
        max_comment_expand=int(scan_raw["max_comment_expand"]),
        scroll_pause_min_ms=int(scan_raw["scroll_pause_min_ms"]),
        scroll_pause_max_ms=int(scan_raw["scroll_pause_max_ms"]),
        action_delay_min_ms=int(scan_raw["action_delay_min_ms"]),
        action_delay_max_ms=int(scan_raw["action_delay_max_ms"]),
        redirect_timeout_ms=int(scan_raw["redirect_timeout_ms"]),
        channels_per_hour_limit=int(scan_raw["channels_per_hour_limit"]),
        consecutive_login_fail_limit=int(scan_raw["consecutive_login_fail_limit"]),
        channel_page_timeout_ms=int(scan_raw["channel_page_timeout_ms"]),
        worker_count=int(scan_raw.get("worker_count", 1)),
    )

    eco_domains = [str(d).strip().lower() for d in raw["eco_domains"] if str(d).strip()]
    shopee_domains = [str(d).strip().lower() for d in raw["shopee_domains"] if str(d).strip()]

    return AppConfig(paths=paths, eco_domains=eco_domains, shopee_domains=shopee_domains, scan=scan)
