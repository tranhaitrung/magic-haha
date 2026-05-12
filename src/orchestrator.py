from __future__ import annotations

import shutil
from pathlib import Path

from src.channel_scanner import ChannelScanner
from src.config_loader import AppConfig
from src.excel_reader import InputValidationError, read_channel_tasks
from src.models import FileProcessResult, ScanStatus
from src.redirect_resolver import clear_resolve_cache
from src.result_writer import write_results_to_csv


def ensure_local_directories(config: AppConfig) -> None:
    config.paths.inbox_dir.mkdir(parents=True, exist_ok=True)
    config.paths.processing_dir.mkdir(parents=True, exist_ok=True)
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)
    config.paths.archive_dir.mkdir(parents=True, exist_ok=True)
    config.paths.error_dir.mkdir(parents=True, exist_ok=True)
    config.paths.log_dir.mkdir(parents=True, exist_ok=True)


def pick_next_input_file(inbox_dir: Path) -> Path | None:
    files = sorted(inbox_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime)
    return files[0] if files else None


def _unique_target_file(target_file: Path) -> Path:
    if not target_file.exists():
        return target_file

    base = target_file.stem
    suffix = target_file.suffix
    parent = target_file.parent
    idx = 1
    while True:
        candidate = parent / f"{base}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def process_single_input_file(
    input_file: Path,
    config: AppConfig,
    logger,
    profile_path: str | None = None,
) -> FileProcessResult:
    processing_file = _unique_target_file(config.paths.processing_dir / input_file.name)
    shutil.move(str(input_file), str(processing_file))
    logger.info("Moved file to processing: %s", processing_file)

    output_file: Path | None = None
    total = 0
    success = 0
    failed = 0

    try:
        tasks = read_channel_tasks(processing_file)
        total = len(tasks)
        logger.info("Loaded %s valid channel URLs", total)

        scanner = ChannelScanner(config=config, logger=logger, profile_path=profile_path)
        results = []
        consecutive_login = 0
        force_stop = False

        with scanner:
            for idx, task in enumerate(tasks, start=1):
                logger.info("[%s/%s] Scanning: %s", idx, total, task.channel_url)
                result = scanner.scan_channel(task)
                results.append(result)

                if result.scan_status == ScanStatus.SUCCESS:
                    success += 1
                else:
                    failed += 1

                if result.scan_status == ScanStatus.LOGIN_REQUIRED:
                    consecutive_login += 1
                    logger.warning("[%s] Status: login_required - skipping", task.channel_url)
                    if consecutive_login >= config.scan.consecutive_login_fail_limit:
                        logger.error("Consecutive login failures - please re-authenticate browser session")
                        force_stop = True
                        break
                else:
                    consecutive_login = 0

                if result.scan_status == ScanStatus.CAPTCHA:
                    logger.error("CAPTCHA detected - stopping all scans. Please handle manually.")
                    force_stop = True
                    break

        if force_stop:
            logger.warning("Scan stopped early due to policy condition")

        output_file = write_results_to_csv(results, config.paths.output_dir, processing_file.stem)
        archive_file = _unique_target_file(config.paths.archive_dir / processing_file.name)
        shutil.move(str(processing_file), str(archive_file))
        logger.info("File processed successfully. Archived: %s", archive_file)
        clear_resolve_cache()

    except InputValidationError as exc:
        failed += 1
        logger.error("Input validation error: %s", exc)
        error_file = _unique_target_file(config.paths.error_dir / processing_file.name)
        shutil.move(str(processing_file), str(error_file))
        clear_resolve_cache()
    except Exception as exc:  # noqa: BLE001
        failed += 1
        logger.exception("Unhandled processing error: %s", exc)
        error_file = _unique_target_file(config.paths.error_dir / processing_file.name)
        if processing_file.exists():
            shutil.move(str(processing_file), str(error_file))
        clear_resolve_cache()

    return FileProcessResult(
        input_file=input_file,
        output_file=output_file,
        total_channels=total,
        success_channels=success,
        failed_channels=failed,
    )
