from datetime import datetime
from importlib import import_module
from pathlib import Path
import os
import socket
import sys
import traceback

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ENV_PATH = PROJECT_ROOT / "config" / ".env"
LOGS_DIR = PROJECT_ROOT / "logs"

SUCCESS_WITH_ROWS = "SUCCESS_WITH_ROWS"
SUCCESS_EMPTY = "SUCCESS_EMPTY"
FAILED_PORT_UNREACHABLE = "FAILED_PORT_UNREACHABLE"
FAILED_DRIVER_MISSING = "FAILED_DRIVER_MISSING"
FAILED_MODULE_MISSING = "FAILED_MODULE_MISSING"
FAILED_CONNECTION = "FAILED_CONNECTION"
FAILED_QUERY = "FAILED_QUERY"


class QueryExecutionError(Exception):
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


def tcp_check(host, port, timeout_seconds=5):
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return "SUCCESS", ""
    except OSError as exc:
        return "FAILED", str(exc)


def import_optional(module_name):
    try:
        return import_module(module_name), ""
    except Exception as exc:
        return None, str(exc)


def fetch_count_from_cursor(cursor):
    row = cursor.fetchone()
    if row is None:
        return 0
    return int(row[0])


def run_cursor_queries(cursor, count_sql, sample_sql):
    cursor.execute(count_sql)
    row_count = fetch_count_from_cursor(cursor)
    cursor.execute(sample_sql)
    cursor.fetchmany(5)
    return row_count


def run_mssql(source, username, password, eff_dat):
    pymssql, error = import_optional("pymssql")
    if not pymssql:
        return None, FAILED_MODULE_MISSING, error

    count_sql = (
        f"SELECT COUNT(*) FROM {source['view']} "
        f"WHERE eff_dat = CAST('{eff_dat}' AS date)"
    )
    sample_sql = (
        f"SELECT TOP (5) * FROM {source['view']} "
        f"WHERE eff_dat = CAST('{eff_dat}' AS date) ORDER BY order_id"
    )

    connection = pymssql.connect(
        server=source["host"],
        port=source["port"],
        user=username,
        password=password,
        database=source["database"],
        login_timeout=5,
        timeout=10,
    )
    try:
        cursor = connection.cursor()
        try:
            return run_cursor_queries(cursor, count_sql, sample_sql), None, ""
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def run_oracle(source, username, password, eff_dat):
    oracledb, error = import_optional("oracledb")
    if not oracledb:
        return None, FAILED_MODULE_MISSING, error

    dsn = f"{source['host']}:{source['port']}/{source['database']}"
    count_sql = (
        f"SELECT COUNT(*) FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}'"
    )
    sample_sql = (
        f"SELECT * FROM {source['view']} WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id FETCH FIRST 5 ROWS ONLY"
    )

    connection = oracledb.connect(user=username, password=password, dsn=dsn)
    try:
        cursor = connection.cursor()
        try:
            return run_cursor_queries(cursor, count_sql, sample_sql), None, ""
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def run_db2(source, username, password, eff_dat):
    jdbc_jar = Path(source["jdbc_jar"])
    if not jdbc_jar.is_absolute():
        jdbc_jar = PROJECT_ROOT / jdbc_jar
    if not jdbc_jar.is_file():
        return None, FAILED_DRIVER_MISSING, f"DB2 JDBC driver JAR not found: {jdbc_jar}"

    jaydebeapi, jaydebeapi_error = import_optional("jaydebeapi")
    jpype, jpype_error = import_optional("jpype")
    module_errors = []
    if not jaydebeapi:
        module_errors.append(f"jaydebeapi: {jaydebeapi_error}")
    if not jpype:
        module_errors.append(f"jpype: {jpype_error}")
    if module_errors:
        return None, FAILED_MODULE_MISSING, "; ".join(module_errors)

    jdbc_url = (
        f"jdbc:db2://{source['host']}:{source['port']}/{source['database']}"
    )
    count_sql = (
        f"SELECT COUNT(*) FROM {source['view']} "
        f"WHERE eff_dat = DATE('{eff_dat}')"
    )
    sample_sql = (
        f"SELECT * FROM {source['view']} WHERE eff_dat = DATE('{eff_dat}') "
        "ORDER BY order_id FETCH FIRST 5 ROWS ONLY"
    )

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
            return run_cursor_queries(cursor, count_sql, sample_sql), None, ""
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def run_mysql(source, username, password, eff_dat):
    mysql_connector, error = import_optional("mysql.connector")
    if not mysql_connector:
        return None, FAILED_MODULE_MISSING, error

    count_sql = (
        f"SELECT COUNT(*) FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}'"
    )
    sample_sql = (
        f"SELECT * FROM {source['view']} WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id LIMIT 5"
    )

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
            return run_cursor_queries(cursor, count_sql, sample_sql), None, ""
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


def run_postgres(source, username, password, eff_dat):
    psycopg2, error = import_optional("psycopg2")
    if not psycopg2:
        return None, FAILED_MODULE_MISSING, error

    count_sql = (
        f"SELECT COUNT(*) FROM {source['view']} "
        f"WHERE eff_dat = DATE '{eff_dat}'"
    )
    sample_sql = (
        f"SELECT * FROM {source['view']} WHERE eff_dat = DATE '{eff_dat}' "
        "ORDER BY order_id LIMIT 5"
    )

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
            return run_cursor_queries(cursor, count_sql, sample_sql), None, ""
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
    finally:
        connection.close()


RUNNERS = {
    "MSSQL": run_mssql,
    "Oracle": run_oracle,
    "DB2": run_db2,
    "MySQL": run_mysql,
    "PostgreSQL": run_postgres,
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


def test_source(source, username, password, eff_dat):
    result = {
        "source": source["name"],
        "host": source["host"],
        "port": str(source["port"]),
        "database_or_service": source["database"],
        "configured_view_name": source["view"],
        "tcp_status": "",
        "connection_status": "",
        "query_status": "",
        "EFF_DAT": eff_dat,
        "row_count": "",
        "status": "",
        "error_message": "",
    }

    tcp_status, tcp_error = tcp_check(source["host"], source["port"])
    result["tcp_status"] = tcp_status
    if tcp_status != "SUCCESS":
        result["connection_status"] = "SKIPPED"
        result["query_status"] = "SKIPPED"
        result["status"] = FAILED_PORT_UNREACHABLE
        result["error_message"] = tcp_error
        return result

    try:
        row_count, pre_connection_failure, pre_connection_error = RUNNERS[source["name"]](
            source,
            username,
            password,
            eff_dat,
        )
        if pre_connection_failure:
            result["connection_status"] = "SKIPPED"
            result["query_status"] = "SKIPPED"
            result["status"] = pre_connection_failure
            result["error_message"] = pre_connection_error
            return result
    except QueryExecutionError as exc:
        result["connection_status"] = "SUCCESS"
        result["query_status"] = "FAILED"
        result["status"] = FAILED_QUERY
        result["error_message"] = f"{exc.__class__.__name__}: {exc}"
        return result
    except Exception as exc:
        result["connection_status"] = "FAILED"
        result["query_status"] = "SKIPPED"
        result["status"] = FAILED_CONNECTION
        result["error_message"] = f"{exc.__class__.__name__}: {exc}"
        return result

    result["connection_status"] = "SUCCESS"
    result["row_count"] = str(row_count)
    result["query_status"] = "SUCCESS"
    result["status"] = SUCCESS_WITH_ROWS if row_count > 0 else SUCCESS_EMPTY
    return result


def write_log(results):
    LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"database_connection_test_{timestamp}.log"
    lines = [f"timestamp={datetime.now().isoformat(timespec='seconds')}"]
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
        "host",
        "port",
        "tcp_status",
        "connection_status",
        "query_status",
        "row_count",
        "status",
    ]
    widths = {
        column: max(len(column), *(len(str(result[column])) for result in results))
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    separator = "  ".join("-" * widths[column] for column in columns)
    print(header)
    print(separator)
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
            f"database_connection_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        log_path.write_text(
            f"status=FAILED_CONFIG\nerror_message={exc}\n",
            encoding="utf-8",
        )
        print(f"Configuration error: {exc}", file=sys.stderr)
        print(f"Log file: {log_path}", file=sys.stderr)
        return 1

    results = []
    for source in sources:
        try:
            results.append(test_source(source, username, password, eff_dat))
        except Exception as exc:
            results.append(
                {
                    "source": source["name"],
                    "host": source["host"],
                    "port": str(source["port"]),
                    "database_or_service": source["database"],
                    "configured_view_name": source["view"],
                    "tcp_status": "UNKNOWN",
                    "connection_status": "UNKNOWN",
                    "query_status": "UNKNOWN",
                    "EFF_DAT": eff_dat,
                    "row_count": "",
                    "status": FAILED_QUERY,
                    "error_message": (
                        f"{exc.__class__.__name__}: {exc}; "
                        f"{traceback.format_exc(limit=1).strip()}"
                    ),
                }
            )

    log_path = write_log(results)
    print_summary(results)
    print(f"Log file: {log_path}")

    success_statuses = {SUCCESS_WITH_ROWS, SUCCESS_EMPTY}
    return 0 if all(result["status"] in success_statuses for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
