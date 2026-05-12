from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class ScanStatus(str, Enum):
    SUCCESS = "success"
    LOGIN_REQUIRED = "login_required"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"
    NO_POST = "no_post"
    ERROR = "error"


@dataclass
class ChannelTask:
    channel_url: str
    note: str | None = None


@dataclass
class RedirectResult:
    original_url: str
    redirect_chain: list[str] = field(default_factory=list)
    final_url: str = ""


@dataclass
class ChannelScanResult:
    channel_url: str
    channel_name: str = ""
    scan_status: ScanStatus = ScanStatus.ERROR
    has_shopee_affiliate: str = "no"
    has_eco_link: str = "no"
    matched_post_url: str = ""
    matched_comment_text: str = ""
    original_comment_link: str = ""
    redirect_chain: str = ""
    final_url: str = ""
    detected_domain: str = ""
    scanned_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    error_message: str = ""


@dataclass
class FileProcessResult:
    input_file: Path
    output_file: Path | None
    total_channels: int
    success_channels: int
    failed_channels: int
