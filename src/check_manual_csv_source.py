from datetime import datetime
from pathlib import Path
import os
import re
import socket
import sys

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ENV_PATH = PROJECT_ROOT / "config" / ".env"
LOGS_DIR = PROJECT_ROOT / "logs"
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})(?=\.csv$)")

SUCCESS_WITH_ROWS = "SUCCESS_WITH_ROWS"
SUCCESS_EMPTY = "SUCCESS_EMPTY"
FAILED_MISSING_FILE = "FAILED_MISSING_FILE"
FAILED_SOURCE_UNREACHABLE = "FAILED_SOURCE_UNREACHABLE"
FAILED_VALIDATION = "FAILED_VALIDATION"
FAILED_READ = "FAILED_READ"
FAILED_OUTPUT_WRITE = "FAILED_OUTPUT_WRITE"

CREATED_NEW_FILE = "CREATED_NEW_FILE"
REPLACED_EXISTING_FILE = "REPLACED_EXISTING_FILE"
LEFT_EXISTING_FILE_UNCHANGED = "LEFT_EXISTING_FILE_UNCHANGED"
NO_OUTPUT_CREATED = "NO_OUTPUT_CREATED"

REQUIRED_ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "status",
    "eff_dat",
    "last_update_at",
]


def write_log(details):
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"manual_csv_extraction_{timestamp}.log"
    lines = [f"{key}={value}" for key, value in details.items()]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_yyyy_mm_dd(value, label):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format: {value}") from exc


def extract_date_from_filename(path):
    match = DATE_PATTERN.search(path.name)
    if not match:
        return None
    try:
        return parse_yyyy_mm_dd(match.group(1), f"Snapshot date in {path.name}")
    except ValueError:
        return None


def select_customer_snapshot(source_dir, pattern):
    candidates = []
    for path in source_dir.glob(pattern):
        snapshot_date = extract_date_from_filename(path)
        if snapshot_date:
            candidates.append((snapshot_date, path))

    if not candidates:
        raise FileNotFoundError(
            f"No valid customer snapshot file found matching {pattern} in {source_dir}"
        )

    return max(candidates, key=lambda candidate: (candidate[0], candidate[1].name))


def build_orders_filename(pattern, eff_dat):
    return pattern.format(eff_dat=eff_dat, business_date=eff_dat)


def build_source_dir(value):
    source_dir = Path(value)
    if is_unc_path(value) or source_dir.is_absolute():
        return source_dir
    return PROJECT_ROOT / source_dir


def is_unc_path(source_dir):
    normalized = str(source_dir).replace("/", "\\")
    return normalized.startswith("\\\\") and not normalized.startswith("\\\\?\\")


def parse_unc_host(source_dir):
    normalized = str(source_dir).replace("/", "\\")
    if not is_unc_path(normalized):
        return None

    parts = [part for part in normalized.split("\\") if part]
    if not parts:
        return None
    return parts[0]


def assert_unc_host_reachable(source_dir, timeout_seconds=5):
    host = parse_unc_host(source_dir)
    if not host:
        return None

    try:
        with socket.create_connection((host, 445), timeout=timeout_seconds):
            return host
    except OSError as exc:
        raise ConnectionError(
            f"Manual CSV source host is unreachable on SMB port 445 within "
            f"{timeout_seconds} seconds: {host}"
        ) from exc


def failure_output_action(final_landing_output_file_path):
    if final_landing_output_file_path and Path(final_landing_output_file_path).exists():
        return LEFT_EXISTING_FILE_UNCHANGED
    return NO_OUTPUT_CREATED


def validate_order_columns(orders_df):
    missing_order_columns = [
        column for column in REQUIRED_ORDER_COLUMNS if column not in orders_df.columns
    ]
    if missing_order_columns:
        raise ValueError(
            "Daily orders file is missing required columns: "
            f"{', '.join(missing_order_columns)}"
        )


def validate_orders(orders_df, customers_df, eff_dat, snapshot_date):
    validate_order_columns(orders_df)

    parsed_order_dates = pd.to_datetime(orders_df["order_date"], errors="coerce").dt.date
    if parsed_order_dates.isna().any():
        raise ValueError("Daily orders file contains unreadable order_date values")

    parsed_eff_dats = pd.to_datetime(orders_df["eff_dat"], errors="coerce").dt.date
    if parsed_eff_dats.isna().any():
        raise ValueError("Daily orders file contains unreadable eff_dat values")

    eff_dat_value = parse_yyyy_mm_dd(eff_dat, "EFF_DAT")
    if not (parsed_eff_dats == eff_dat_value).all():
        raise ValueError(f"Every eff_dat value must equal EFF_DAT: {eff_dat}")

    parsed_last_update_at = pd.to_datetime(orders_df["last_update_at"], errors="coerce")
    if parsed_last_update_at.isna().any():
        raise ValueError("Daily orders file contains unreadable last_update_at values")

    max_order_date = parsed_order_dates.max()
    if max_order_date > snapshot_date:
        raise ValueError(
            f"max(order_date) {max_order_date} is greater than selected customer "
            f"snapshot date {snapshot_date}"
        )

    if "customer_id" not in customers_df.columns:
        raise ValueError("Customer snapshot file is missing required column: customer_id")

    customer_ids = set(customers_df["customer_id"].dropna())
    order_customer_ids = set(orders_df["customer_id"].dropna())
    missing_customer_ids = sorted(order_customer_ids - customer_ids)

    if missing_customer_ids:
        preview = ", ".join(str(customer_id) for customer_id in missing_customer_ids[:20])
        raise ValueError(
            "Daily orders contain customer_id values not found in the customer snapshot: "
            f"{preview}"
        )


def extract_manual_csv():
    timestamp = datetime.now().isoformat(timespec="seconds")
    details = {
        "timestamp": timestamp,
        "EFF_DAT": "",
        "manual_csv_source_directory": "",
        "manual_csv_source_path_type": "",
        "manual_csv_unc_host": "",
        "expected_daily_orders_file": "",
        "selected_customer_snapshot_file": "",
        "customer_snapshot_date": "",
        "csv_files_found": "",
        "orders_row_count": "",
        "customer_snapshot_row_count": "",
        "validation_status": "",
        "output_status": "",
        "staging_output_file_path": "",
        "final_landing_output_file_path": "",
        "output_action": NO_OUTPUT_CREATED,
        "error_message": "",
    }

    if CONFIG_ENV_PATH.exists():
        load_dotenv(CONFIG_ENV_PATH)

    try:
        eff_dat = require_env("EFF_DAT")
        parse_yyyy_mm_dd(eff_dat, "EFF_DAT")
        source_dir = build_source_dir(require_env("MANUAL_CSV_SOURCE_DIR"))
        customers_snapshot_file_pattern = require_env("CUSTOMERS_SNAPSHOT_FILE_PATTERN")
        orders_file_pattern = require_env("MANUAL_ORDERS_FILE_PATTERN")
        daily_orders_file = build_orders_filename(orders_file_pattern, eff_dat)

        staging_dir = PROJECT_ROOT / "data" / "staging" / eff_dat
        landing_dir = PROJECT_ROOT / "data" / "landing" / eff_dat
        staging_output_path = staging_dir / f"manual_csv_orders_{eff_dat}.csv"
        final_landing_output_path = landing_dir / f"manual_csv_orders_{eff_dat}.csv"

        details.update(
            {
                "EFF_DAT": eff_dat,
                "manual_csv_source_directory": str(source_dir),
                "manual_csv_source_path_type": "UNC" if is_unc_path(source_dir) else "LOCAL",
                "manual_csv_unc_host": parse_unc_host(source_dir) or "",
                "expected_daily_orders_file": daily_orders_file,
                "staging_output_file_path": str(staging_output_path),
                "final_landing_output_file_path": str(final_landing_output_path),
            }
        )

        staging_dir.mkdir(parents=True, exist_ok=True)
        landing_dir.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)

        try:
            assert_unc_host_reachable(source_dir)
        except ConnectionError:
            details["validation_status"] = FAILED_SOURCE_UNREACHABLE
            raise

        try:
            source_dir_is_available = source_dir.is_dir()
        except OSError as exc:
            details["validation_status"] = FAILED_SOURCE_UNREACHABLE
            raise ConnectionError(f"Manual CSV source share is unreachable: {source_dir}") from exc

        if not source_dir_is_available:
            details["validation_status"] = FAILED_SOURCE_UNREACHABLE
            raise ConnectionError(f"Manual CSV source share is unreachable: {source_dir}")

        csv_files = sorted(path.name for path in source_dir.glob("*.csv"))
        details["csv_files_found"] = ", ".join(csv_files)

        try:
            snapshot_date, customers_path = select_customer_snapshot(
                source_dir,
                customers_snapshot_file_pattern,
            )
        except FileNotFoundError:
            details["validation_status"] = FAILED_MISSING_FILE
            raise
        orders_path = source_dir / daily_orders_file

        details["selected_customer_snapshot_file"] = customers_path.name
        details["customer_snapshot_date"] = snapshot_date.isoformat()

        if not orders_path.exists():
            details["validation_status"] = FAILED_MISSING_FILE
            raise FileNotFoundError(f"Daily orders file does not exist: {orders_path}")

        try:
            customers_df = pd.read_csv(customers_path)
            orders_df = pd.read_csv(orders_path)
        except Exception:
            details["validation_status"] = FAILED_READ
            raise

        details["orders_row_count"] = str(len(orders_df))
        details["customer_snapshot_row_count"] = str(len(customers_df))

        try:
            validate_order_columns(orders_df)
            if len(orders_df) == 0:
                status = SUCCESS_EMPTY
            else:
                validate_orders(orders_df, customers_df, eff_dat, snapshot_date)
                status = SUCCESS_WITH_ROWS
        except Exception:
            details["validation_status"] = FAILED_VALIDATION
            raise

        details["validation_status"] = status
        details["output_status"] = "PENDING"

        try:
            orders_df.to_csv(staging_output_path, index=False)
            landing_exists = final_landing_output_path.exists()
            os.replace(staging_output_path, final_landing_output_path)
        except Exception:
            details["validation_status"] = FAILED_OUTPUT_WRITE
            details["output_status"] = FAILED_OUTPUT_WRITE
            details["output_action"] = failure_output_action(
                details["final_landing_output_file_path"]
            )
            raise

        details["output_status"] = status
        details["output_action"] = (
            REPLACED_EXISTING_FILE if landing_exists else CREATED_NEW_FILE
        )

        log_path = write_log(details)
        print(f"Validation status: {status}")
        print(f"Output status: {status}")
        print(f"Output action: {details['output_action']}")
        print(f"EFF_DAT: {eff_dat}")
        print(f"Expected daily orders file: {daily_orders_file}")
        print(f"Selected customer snapshot file: {customers_path.name}")
        print(f"Final landing output file: {final_landing_output_path}")
        print(f"Log file: {log_path}")
        return status, details["output_action"], final_landing_output_path, log_path, 0
    except Exception as exc:
        if not details["validation_status"]:
            details["validation_status"] = FAILED_VALIDATION
        if not details["output_status"]:
            details["output_status"] = details["validation_status"]
        if details["validation_status"] != FAILED_OUTPUT_WRITE:
            details["output_action"] = failure_output_action(
                details["final_landing_output_file_path"]
            )
        details["error_message"] = str(exc)
        log_path = write_log(details)
        print(f"Validation status: {details['validation_status']}", file=sys.stderr)
        print(f"Output status: {details['output_status']}", file=sys.stderr)
        print(f"Output action: {details['output_action']}", file=sys.stderr)
        print(f"Error: {exc}", file=sys.stderr)
        print(f"Log file: {log_path}", file=sys.stderr)
        return (
            details["validation_status"],
            details["output_action"],
            details["final_landing_output_file_path"],
            log_path,
            1,
        )


def main():
    return extract_manual_csv()[-1]


if __name__ == "__main__":
    sys.exit(main())
