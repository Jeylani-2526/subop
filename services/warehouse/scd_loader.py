"""Warehouse loader: source tables -> generated star schema, SCD Type 1 and 2 (M8W29T2)."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.warehouse.metadata import (
    Dimension,
    MetadataValidationError,
    WarehouseDefinition,
    load_definition,
    surrogate_key,
)
from services.warehouse.schema_generator import (
    DEFAULT_TARGET_REF,
    META_SCHEMA,
    TARGET_SCHEMA,
    TablePlan,
    fingerprint,
    plan_schema,
)

STAGE_BATCH_ROWS = 500


class LoaderError(Exception):
    error_code = "WAREHOUSE_LOAD_FAILED"


@dataclass
class TableReport:
    table: str
    inserted: int = 0
    new_versions: int = 0
    updated: int = 0
    unmatched: Dict[str, int] = field(default_factory=dict)


def _cols(names: Sequence[str], alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return ", ".join(f"{prefix}{n}" for n in names)


def _row(names: Sequence[str], alias: str) -> str:
    # (a.x, a.y) — compared with IS DISTINCT FROM, which treats NULLs as values.
    return f"({_cols(names, alias)})"


def _match(keys: Sequence[str], left: str, right: str) -> str:
    return " AND ".join(f"{left}.{k} = {right}.{k}" for k in keys)


class WarehouseLoader:
    """Loads one generated definition. Every write is one execute_write
    statement, so the Postgres connector's commit-per-statement never leaves
    a dimension half-changed. Source rows are staged in session temp tables,
    which keeps the SCD logic set-based and lets the source be any database
    the Abstraction Layer reads."""

    def __init__(
        self,
        defn: WarehouseDefinition,
        source: Any,
        warehouse: Any,
        schema: str = TARGET_SCHEMA,
        meta_schema: str = META_SCHEMA,
    ) -> None:
        self.defn = defn
        self._source = source
        self._dw = warehouse
        self.schema = schema
        self._meta = meta_schema
        self._plan: Dict[str, TablePlan] = {
            t.name: t for t in plan_schema(defn, schema)
        }

    # -- run -----------------------------------------------------------------

    def load(self) -> List[TableReport]:
        self._require_generated()
        fact = self.defn.fact
        stage = {fact.name: self._stage(fact.name, fact.source_table, fact.columns)}
        for dim in self.defn.dimensions:
            if dim.source_table:
                stage[dim.name] = self._stage(dim.name, dim.source_table, dim.columns)

        reports = []
        for dim in self.defn.dimensions:
            if dim.derived_from:
                reports.append(self._load_date_dimension(dim, stage[fact.name]))
            elif dim.scd_type == 2:
                reports.append(self._load_type2(dim, stage[dim.name]))
            else:
                reports.append(self._load_type1(dim, stage[dim.name]))
        reports.append(self._load_fact(stage[fact.name]))
        return reports

    def _require_generated(self) -> None:
        registry = f"{self._meta}.schema_registry"
        exists = self._dw.execute_query("SELECT to_regclass(%s) AS t", (registry,))
        rows = (
            self._dw.execute_query(
                f"SELECT fingerprint, target_schema FROM {registry} WHERE schema_id = %s",
                (self.defn.name,),
            )
            if exists[0]["t"]
            else []
        )
        if not rows:
            raise LoaderError(
                f"'{self.defn.name}' has not been generated yet; run the schema "
                "generator (or POST /api/warehouse/schemas/generate) first"
            )
        if rows[0]["fingerprint"] != fingerprint(self.defn) or (
            rows[0]["target_schema"] != self.schema
        ):
            raise LoaderError(
                f"'{self.defn.name}' was generated from a different definition or "
                "into another schema; changing a schema needs versioning (deferred)"
            )

    # -- staging ---------------------------------------------------------------

    def _stage(self, table: str, source_table: str, columns: Dict[str, str]) -> str:
        names = list(columns)
        types = {c.name: c.warehouse_type for c in self._plan[table].columns}
        stage = f"stage_{table}"
        body = ", ".join(f"{n} {types[n]}" for n in names)
        # Recreated every run, so a stage left by another definition in the
        # same session can never carry a stale shape.
        self._dw.execute_write(f"DROP TABLE IF EXISTS pg_temp.{stage}")
        self._dw.execute_write(f"CREATE TEMP TABLE {stage} ({body})")

        rows = self._source.execute_query(f"SELECT {_cols(names)} FROM {source_table}")
        placeholder = "(" + ", ".join(["%s"] * len(names)) + ")"
        for start in range(0, len(rows), STAGE_BATCH_ROWS):
            end = start + STAGE_BATCH_ROWS
            batch = rows[start:end]
            params = [row[n] for row in batch for n in names]
            self._dw.execute_write(
                f"INSERT INTO {stage} ({_cols(names)}) VALUES "
                + ", ".join([placeholder] * len(batch)),
                params,
            )

        bk = self._plan[table].business_key
        dupes = self._dw.execute_query(
            f"SELECT {_cols(bk)} FROM {stage} WHERE ({_cols(bk)}) IS NOT NULL "
            f"GROUP BY {_cols(bk)} HAVING count(*) > 1 LIMIT 5"
        )
        if dupes:
            raise LoaderError(
                f"{source_table} has duplicate business keys ({', '.join(bk)}): "
                f"{[tuple(r.values()) for r in dupes]}"
            )
        return stage

    # -- dimensions --------------------------------------------------------------

    def _split(self, dim: Dimension) -> Tuple[str, List[str], List[str]]:
        key = dim.business_key[0]
        tracked = list(dim.tracked_attributes)
        untracked = [c for c in dim.columns if c != key and c not in tracked]
        return key, tracked, untracked

    def _overwrite(self, target: str, stage: str, key: str, cols: List[str]) -> int:
        # Type 1: overwrite in place. In a Type 2 dimension this corrects every
        # version of the key, since a Type 1 attribute carries no history.
        if not cols:
            return 0
        sets = ", ".join(f"{c} = s.{c}" for c in cols)
        return self._dw.execute_write(
            f"UPDATE {target} d SET {sets} FROM {stage} s "
            f"WHERE d.{key} = s.{key} AND {_row(cols, 'd')} IS DISTINCT FROM {_row(cols, 's')}"
        )

    def _load_type1(self, dim: Dimension, stage: str) -> TableReport:
        target = f"{self.schema}.{dim.name}"
        key, _, attrs = self._split(dim)
        report = TableReport(dim.name)
        report.updated = self._overwrite(target, stage, key, attrs)
        cols = [key] + attrs
        report.inserted = self._dw.execute_write(
            f"INSERT INTO {target} ({_cols(cols)}) SELECT {_cols(cols, 's')} FROM {stage} s "
            f"WHERE NOT EXISTS (SELECT 1 FROM {target} d WHERE d.{key} = s.{key})"
        )
        return report

    def _load_type2(self, dim: Dimension, stage: str) -> TableReport:
        target = f"{self.schema}.{dim.name}"
        key, tracked, untracked = self._split(dim)
        cols = [key] + untracked + tracked
        report = TableReport(dim.name)
        report.updated = self._overwrite(target, stage, key, untracked)

        # Close the current row and insert its new version in ONE statement:
        # the connector commits per statement, so two statements could leave a
        # key with no current row if the second one failed.
        report.new_versions = self._dw.execute_write(
            f"WITH closed AS ("
            f"UPDATE {target} d SET valid_to = now(), is_current = false "
            f"FROM {stage} s WHERE d.{key} = s.{key} AND d.is_current "
            f"AND {_row(tracked, 'd')} IS DISTINCT FROM {_row(tracked, 's')} "
            f"RETURNING d.{key}) "
            f"INSERT INTO {target} ({_cols(cols)}, valid_from, valid_to, is_current) "
            f"SELECT {_cols(cols, 's')}, now(), NULL, true "
            f"FROM {stage} s JOIN closed c ON c.{key} = s.{key}"
        )
        report.inserted = self._dw.execute_write(
            f"INSERT INTO {target} ({_cols(cols)}, valid_from, valid_to, is_current) "
            f"SELECT {_cols(cols, 's')}, now(), NULL, true FROM {stage} s "
            f"WHERE NOT EXISTS (SELECT 1 FROM {target} d WHERE d.{key} = s.{key})"
        )
        return report

    def _date_of(self, column: str, alias: str) -> str:
        # Calendar dates are taken in UTC, so the same order lands on the same
        # date whatever the session's time zone is.
        canonical = next(
            c.canonical_type
            for c in self._plan[self.defn.fact.name].columns
            if c.name == column
        )
        if canonical == "DATE":
            return f"{alias}.{column}"
        return f"({alias}.{column} AT TIME ZONE 'UTC')::date"

    def _load_date_dimension(self, dim: Dimension, fact_stage: str) -> TableReport:
        target = f"{self.schema}.{dim.name}"
        key = surrogate_key(dim.name)
        day = self._date_of(dim.derived_from.column, "s")
        report = TableReport(dim.name)
        report.inserted = self._dw.execute_write(
            f"INSERT INTO {target} ({key}, full_date, year, quarter, month, day, day_of_week) "
            f"SELECT DISTINCT to_char(x.d, 'YYYYMMDD')::int, x.d, "
            f"extract(year FROM x.d)::int, extract(quarter FROM x.d)::int, "
            f"extract(month FROM x.d)::int, extract(day FROM x.d)::int, "
            f"extract(isodow FROM x.d)::int "
            f"FROM (SELECT {day} AS d FROM {fact_stage} s) x "
            f"WHERE x.d IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM {target} t WHERE t.full_date = x.d)"
        )
        return report

    # -- fact ----------------------------------------------------------------

    def _key_lookup(self, ref: str, dim: Dimension) -> str:
        """SQL for the surrogate key the stage row s points to."""
        key = surrogate_key(dim.name)
        if dim.derived_from:
            return f"to_char({self._date_of(ref, 's')}, 'YYYYMMDD')::int"
        current = " AND d.is_current" if dim.scd_type == 2 else ""
        return (
            f"(SELECT d.{key} FROM {self.schema}.{dim.name} d "
            f"WHERE d.{dim.business_key[0]} = s.{ref}{current})"
        )

    def _load_fact(self, stage: str) -> TableReport:
        fact = self.defn.fact
        target = f"{self.schema}.{fact.name}"
        bk = list(fact.business_key)
        cols = list(fact.columns)
        other = [c for c in cols if c not in bk]
        refs = [
            (ref, self.defn.dimension(name), surrogate_key(name))
            for ref, name in fact.dimension_keys.items()
        ]
        report = TableReport(fact.name)

        # An existing row keeps the dimension version it was first loaded with.
        # Its key is looked up again only when the reference itself changed, or
        # when it had no match before (a late-arriving dimension row).
        sets = [f"{c} = s.{c}" for c in other]
        changed = [f"{_row(other, 'f')} IS DISTINCT FROM {_row(other, 's')}"]
        for ref, dim, key in refs:
            lookup = self._key_lookup(ref, dim)
            sets.append(
                f"{key} = CASE WHEN f.{ref} IS DISTINCT FROM s.{ref} OR f.{key} IS NULL "
                f"THEN {lookup} ELSE f.{key} END"
            )
            changed.append(f"(f.{key} IS NULL AND {lookup} IS NOT NULL)")
        report.updated = self._dw.execute_write(
            f"UPDATE {target} f SET {', '.join(sets)} FROM {stage} s "
            f"WHERE {_match(bk, 'f', 's')} AND ({' OR '.join(changed)})"
        )

        keys = [key for _, _, key in refs]
        lookups = [self._key_lookup(ref, dim) for ref, dim, _ in refs]
        report.inserted = self._dw.execute_write(
            f"INSERT INTO {target} ({_cols(cols + keys)}) "
            f"SELECT {_cols(cols, 's')}, {', '.join(lookups)} FROM {stage} s "
            f"WHERE NOT EXISTS (SELECT 1 FROM {target} f WHERE {_match(bk, 'f', 's')})"
        )

        for ref, dim, key in refs:
            rows = self._dw.execute_query(
                f"SELECT count(*) AS n FROM {target} "
                f"WHERE {key} IS NULL AND {ref} IS NOT NULL"
            )
            report.unmatched[dim.name] = rows[0]["n"]
        return report


# -- command line -----------------------------------------------------------


def _print(reports: List[TableReport]) -> None:
    for r in reports:
        line = f"  {r.table}: {r.inserted} inserted, {r.updated} updated"
        if r.new_versions:
            line += f", {r.new_versions} new versions"
        print(line)
        for dim, n in r.unmatched.items():
            if n:
                print(f"    {n} row(s) with no matching {dim} row (key left NULL)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load a generated warehouse star schema from its source tables."
    )
    parser.add_argument("definition", help="path to a definition JSON file")
    parser.add_argument(
        "--target-ref",
        default=DEFAULT_TARGET_REF,
        help=f"warehouse connection ref (default: {DEFAULT_TARGET_REF})",
    )
    args = parser.parse_args(argv)

    try:
        defn = load_definition(args.definition)
    except MetadataValidationError as exc:
        print("Definition is invalid:", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    from services.connectors.errors import ConnectorError
    from services.etl_engine.connection_resolver import (
        release_connection,
        resolve_connection,
    )
    from services.warehouse.schema_generator import _load_dotenv

    _load_dotenv()
    opened = []
    try:
        source, _ = resolve_connection(
            defn.source.connector_type, defn.source.connection_ref
        )
        opened.append(source)
        warehouse, _ = resolve_connection("postgresql", args.target_ref)
        opened.append(warehouse)
        reports = WarehouseLoader(defn, source, warehouse).load()
    except LoaderError as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        return 3
    except ConnectorError as exc:
        print(f"Load failed: {exc.error_code}: {exc.message}", file=sys.stderr)
        return 4
    finally:
        for layer in opened:
            release_connection(layer)

    print(f"{defn.name}: loaded")
    _print(reports)
    return 0


if __name__ == "__main__":
    sys.exit(main())
