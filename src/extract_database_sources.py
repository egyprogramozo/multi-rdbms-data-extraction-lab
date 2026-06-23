from datetime import datetime
from importlib import import_module
from pathlib import Path
import csv
import os
import shutil
import socket
import sys
import traceback

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ENV_PATH = PROJECT_ROOT / "config" / ".env"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

SUCCESS_WITH_ROWS = "SUCCESS_WITH_ROWS"
SUCCESS_EMPTY = "SUCCESS_EMPTY"
FAILED_PORT_UNREACHABLE = "FAILED_PORT_UNREACHABLE"
FAILED_MODULE_MISSING = "FAILED_MODULE_MISSING"
FAILED_DRIVER_MISSING = "FAILED_DRIVER_MISSING"
FAILED_CONNECTION = "FAILED_CONNECTION"
FAILED_QUERY = "FAILED_QUERY"
FAILED_OUTPUT_WRITE = "FAILED_OUTPUT_WRITE"

SUCCESS_STATUSES = {SUCCESS_WITH_ROWS, SUCCESS_EMPTY}


class QueryExecutionError(Exception):
    pass


class OutputWriteError(Exception):
    pass


def require_env(name):
    value = os.getenv(name)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def require_int_env(name):
    value = require_env(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer: {value}") from exc


def import_optional(module_name):
    try:
        return import_module(module_name), ""
    except Exception as exc:
        return None, str(exc)


def tcp_check(host, port, timeout_seconds=5):
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return "SUCCESS", ""
    except OSError as exc:
        return "FAILED", str(exc)


def source_slug(source_name):
    return source_name.lower()


def output_paths(source_name, eff_dat):
    filename = f"{source_slug(source_name)}_orders_{eff_dat}.csv"
    relative_dir = Path(eff_dat) / "database_sources"
    return (
        DATA_DIR / "staging" / relative_dir / filename,
        DATA_DIR / "landing" / relative_dir / filename,
    )


def column_names(cursor):
    return [column[0] for column in cursor.description]


def fetch_query_results(cursor, sql):
    cursor.execute(sql)
    columns = column_names(cursor)
    rows = cursor.fetchall()
    return columns, rows


def write_csv(staging_path, landing_path, columns, rows):
    landing_exists = landing_path.exists()
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    landing_path.parent.mkdir(parents=True, exist_ok=True)
    landing_tmp_path = landing_path.with_name(f".{landing_path.name}.tmp")

    try:
        with staging_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            writer.writerows(rows)
        shutil.copy2(staging_path, landing_tmp_path)
        os.replace(landing_tmp_path, landing_path)
    except Exception as exc:
        raise OutputWriteError(f"{exc.__class__.__name__}: {exc}") from exc

    if landing_exists:
        return "REPLACED_EXISTING_FILE"
    return "CREATED_NEW_FILE"


def failure_output_action(landing_path):
    if landing_path.exists():
        return "LEFT_EXISTING_FILE_UNCHANGED"
    return "NO_OUTPUT_CREATED"


def mssql_sql(source, eff_dat):
    return (
        f"SELECT * FROM {source['view']} "
        f"WHERE eff_dat = CAST('{eff_dat}' AS date) "
        "ORDER BY order_id"
    )


def oracle_sql(source, eff_dat):
    return (
        f"SELECT * FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id"
    )


def db2_sql(source, eff_dat):
    return (
        f"SELECT * FROM {source['view']} "
        f"WHERE eff_dat = DATE('{eff_dat}') "
        "ORDER BY order_id"
    )


def mysql_sql(source, eff_dat):
    return (
        f"SELECT * FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id"
    )


def postgres_sql(source, eff_dat):
    return (
        f"SELECT * FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id"
    )


def extract_mssql(source, username, password, eff_dat):
    pymssql, error = import_optional("pymssql")
    if not pymssql:
        return None, None, FAILED_MODULE_MISSING, error

    connection = pymssql.connect(
        server=source["host"],
        port=source["port"],
        user=username,
        password=password,
        database=source["database"],
        login_timeout=5,
        timeout=30,
    )
    try:
        cursor = connection.cursor()
        try:
            return (*fetch_query_results(cursor, mssql_sql(source, eff_dat)), None, "")
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def extract_oracle(source, username, password, eff_dat):
    oracledb, error = import_optional("oracledb")
    if not oracledb:
        return None, None, FAILED_MODULE_MISSING, error

    dsn = f"{source['host']}:{source['port']}/{source['database']}"
    connection = oracledb.connect(user=username, password=password, dsn=dsn)
    try:
        cursor = connection.cursor()
        try:
            return (*fetch_query_results(cursor, oracle_sql(source, eff_dat)), None, "")
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def extract_db2(source, username, password, eff_dat):
    jdbc_jar = Path(source["jdbc_jar"])
    if not jdbc_jar.is_absolute():
        jdbc_jar = PROJECT_ROOT / jdbc_jar
    if not jdbc_jar.is_file():
        return None, None, FAILED_DRIVER_MISSING, f"DB2 JDBC driver JAR not found: {jdbc_jar}"

    jaydebeapi, jaydebeapi_error = import_optional("jaydebeapi")
    jpype, jpype_error = import_optional("jpype")
    module_errors = []
    if not jaydebeapi:
        module_errors.append(f"jaydebeapi: {jaydebeapi_error}")
    if not jpype:
        module_errors.append(f"jpype: {jpype_error}")
    if module_errors:
        return None, None, FAILED_MODULE_MISSING, "; ".join(module_errors)

    jdbc_url = f"jdbc:db2://{source['host']}:{source['port']}/{source['database']}"
    try:
        connection = jaydebeapi.connect(
            source["jdbc_class"],
            jdbc_url,
            [username, password],
            str(jdbc_jar),
        )
    except Exception as exc:
        raise ConnectionError(f"{exc.__class__.__name__}: {exc}") from exc

    try:
        cursor = connection.cursor()
        try:
            return (*fetch_query_results(cursor, db2_sql(source, eff_dat)), None, "")
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def extract_mysql(source, username, password, eff_dat):
    mysql_connector, error = import_optional("mysql.connector")
    if not mysql_connector:
        return None, None, FAILED_MODULE_MISSING, error

    connection = mysql_connector.connect(
        host=source["host"],
        port=source["port"],
        database=source["database"],
        user=username,
        password=password,
        connection_timeout=5,
    )
    try:
        cursor = connection.cursor()
        try:
            return (*fetch_query_results(cursor, mysql_sql(source, eff_dat)), None, "")
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def extract_postgres(source, username, password, eff_dat):
    psycopg2, error = import_optional("psycopg2")
    if not psycopg2:
        return None, None, FAILED_MODULE_MISSING, error

    connection = psycopg2.connect(
        host=source["host"],
        port=source["port"],
        dbname=source["database"],
        user=username,
        password=password,
        connect_timeout=5,
    )
    try:
        cursor = connection.cursor()
        try:
            return (*fetch_query_results(cursor, postgres_sql(source, eff_dat)), None, "")
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


EXTRACTORS = {
    "MSSQL": extract_mssql,
    "Oracle": extract_oracle,
    "DB2": extract_db2,
    "MySQL": extract_mysql,
    "PostgreSQL": extract_postgres,
}


def build_sources():
    return [
        {
            "name": "MSSQL",
            "host": require_env("MSSQL_HOST"),
            "port": require_int_env("MSSQL_PORT"),
            "database": require_env("MSSQL_DATABASE"),
            "view": require_env("MSSQL_VIEW"),
        },
        {
            "name": "Oracle",
            "host": require_env("ORACLE_HOST"),
            "port": require_int_env("ORACLE_PORT"),
            "database": require_env("ORACLE_SERVICE"),
            "view": require_env("ORACLE_VIEW"),
        },
        {
            "name": "DB2",
            "host": require_env("DB2_HOST"),
            "port": require_int_env("DB2_PORT"),
            "database": require_env("DB2_DATABASE"),
            "view": require_env("DB2_VIEW"),
            "jdbc_jar": os.getenv("DB2_JDBC_JAR", "local_drivers/db2/db2jcc4.jar"),
            "jdbc_class": os.getenv("DB2_JDBC_CLASS", "com.ibm.db2.jcc.DB2Driver"),
        },
        {
            "name": "MySQL",
            "host": require_env("MYSQL_HOST"),
            "port": require_int_env("MYSQL_PORT"),
            "database": require_env("MYSQL_DATABASE"),
            "view": require_env("MYSQL_VIEW"),
        },
        {
            "name": "PostgreSQL",
            "host": require_env("POSTGRES_HOST"),
            "port": require_int_env("POSTGRES_PORT"),
            "database": require_env("POSTGRES_DATABASE"),
            "view": require_env("POSTGRES_VIEW"),
        },
    ]


def base_result(source, eff_dat):
    staging_path, landing_path = output_paths(source["name"], eff_dat)
    return {
        "source": source["name"],
        "host": source["host"],
        "port": str(source["port"]),
        "database_or_service_name": source["database"],
        "configured_view": source["view"],
        "tcp_status": "",
        "connection_status": "",
        "query_status": "",
        "EFF_DAT": eff_dat,
        "row_count": "",
        "staging_output_file_path": str(staging_path),
        "final_landing_output_file_path": str(landing_path),
        "status": "",
        "output_action": "",
        "error_message": "",
    }


def extract_source(source, username, password, eff_dat):
    result = base_result(source, eff_dat)
    staging_path = Path(result["staging_output_file_path"])
    landing_path = Path(result["final_landing_output_file_path"])

    tcp_status, tcp_error = tcp_check(source["host"], source["port"])
    result["tcp_status"] = tcp_status
    if tcp_status != "SUCCESS":
        result["connection_status"] = "SKIPPED"
        result["query_status"] = "SKIPPED"
        result["status"] = FAILED_PORT_UNREACHABLE
        result["output_action"] = failure_output_action(landing_path)
        result["error_message"] = tcp_error
        return result

    try:
        columns, rows, pre_connection_failure, pre_connection_error = EXTRACTORS[
            source["name"]
        ](source, username, password, eff_dat)
        if pre_connection_failure:
            result["connection_status"] = "SKIPPED"
            result["query_status"] = "SKIPPED"
            result["status"] = pre_connection_failure
            result["output_action"] = failure_output_action(landing_path)
            result["error_message"] = pre_connection_error
            return result
    except QueryExecutionError as exc:
        result["connection_status"] = "SUCCESS"
        result["query_status"] = "FAILED"
        result["status"] = FAILED_QUERY
        result["output_action"] = failure_output_action(landing_path)
        result["error_message"] = f"{exc.__class__.__name__}: {exc}"
        return result
    except Exception as exc:
        result["connection_status"] = "FAILED"
        result["query_status"] = "SKIPPED"
        result["status"] = FAILED_CONNECTION
        result["output_action"] = failure_output_action(landing_path)
        result["error_message"] = f"{exc.__class__.__name__}: {exc}"
        return result

    row_count = len(rows)
    result["connection_status"] = "SUCCESS"
    result["query_status"] = "SUCCESS"
    result["row_count"] = str(row_count)

    try:
        result["output_action"] = write_csv(staging_path, landing_path, columns, rows)
    except OutputWriteError as exc:
        result["status"] = FAILED_OUTPUT_WRITE
        result["output_action"] = failure_output_action(landing_path)
        result["error_message"] = str(exc)
        return result

    result["status"] = SUCCESS_WITH_ROWS if row_count > 0 else SUCCESS_EMPTY
    return result


def write_log(results, eff_dat):
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"database_extraction_{timestamp}.log"
    lines = [
        f"timestamp={datetime.now().isoformat(timespec='seconds')}",
        f"EFF_DAT={eff_dat}",
    ]
    for result in results:
        lines.append(f"[{result['source']}]")
        for key, value in result.items():
            lines.append(f"{key}={value}")
        lines.append("")
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def print_summary(results):
    columns = [
        "source",
        "tcp_status",
        "connection_status",
        "query_status",
        "row_count",
        "status",
        "output_action",
        "final_landing_output_file_path",
    ]
    headers = {
        "final_landing_output_file_path": "landing_file",
    }
    widths = {
        column: max(
            len(headers.get(column, column)),
            *(len(str(result[column])) for result in results),
        )
        for column in columns
    }
    print("  ".join(headers.get(column, column).ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for result in results:
        print("  ".join(str(result[column]).ljust(widths[column]) for column in columns))


def main():
    if CONFIG_ENV_PATH.exists():
        load_dotenv(CONFIG_ENV_PATH)

    try:
        eff_dat = require_env("EFF_DAT")
        username = require_env("DB_USERNAME")
        password = require_env("DB_PASSWORD")
        sources = build_sources()
    except Exception as exc:
        LOGS_DIR.mkdir(exist_ok=True)
        log_path = LOGS_DIR / (
            f"database_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        log_path.write_text(
            "\n".join(
                [
                    f"timestamp={datetime.now().isoformat(timespec='seconds')}",
                    "status=FAILED_CONFIG",
                    f"error_message={exc}",
                ]
            ),
            encoding="utf-8",
        )
        print(f"Configuration error: {exc}", file=sys.stderr)
        print(f"Log file: {log_path}", file=sys.stderr)
        return 1

    results = []
    for source in sources:
        try:
            results.append(extract_source(source, username, password, eff_dat))
        except Exception as exc:
            result = base_result(source, eff_dat)
            result["tcp_status"] = "UNKNOWN"
            result["connection_status"] = "UNKNOWN"
            result["query_status"] = "UNKNOWN"
            result["status"] = FAILED_QUERY
            result["output_action"] = failure_output_action(
                Path(result["final_landing_output_file_path"])
            )
            result["error_message"] = (
                f"{exc.__class__.__name__}: {exc}; "
                f"{traceback.format_exc(limit=1).strip()}"
            )
            results.append(result)

    log_path = write_log(results, eff_dat)
    print_summary(results)
    print(f"Log file: {log_path}")

    return 0 if all(result["status"] in SUCCESS_STATUSES for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
