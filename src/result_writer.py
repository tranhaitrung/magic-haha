from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from src.models import ChannelScanResult


HEADERS = [
    "channel_url",
    "channel_name",
    "scan_status",
    "has_shopee_affiliate",
    "has_eco_link",
    "matched_post_url",
    "matched_comment_text",
    "original_comment_link",
    "redirect_chain",
    "final_url",
    "detected_domain",
    "scanned_at",
    "error_message",
]


def _build_output_file_path(output_dir: Path, input_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"scan_output_{input_name}_{stamp}.csv"


def write_results_to_csv(results: list[ChannelScanResult], output_dir: Path, input_basename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = _build_output_file_path(output_dir, input_basename)

    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(HEADERS)

        for item in results:
            writer.writerow(
                [
                    item.channel_url,
                    item.channel_name,
                    item.scan_status.value,
                    item.has_shopee_affiliate,
                    item.has_eco_link,
                    item.matched_post_url,
                    (item.matched_comment_text or "")[:300],
                    item.original_comment_link,
                    item.redirect_chain,
                    item.final_url,
                    item.detected_domain,
                    item.scanned_at,
                    item.error_message,
                ]
            )

    return output_file
