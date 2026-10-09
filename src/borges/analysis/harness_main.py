from __future__ import annotations

from borges.analysis.harness_cell_check import CELL_CHECK_SOURCE, MIN_CELL_ROWS
from borges.analysis.harness_cluster import CLUSTER_MODELS, CLUSTER_SOURCE
from borges.analysis.harness_cluster_count import CLUSTER_COUNT_SOURCE, MIN_CLUSTERS
from borges.analysis.harness_covariates import COVARIATES_SOURCE
from borges.analysis.harness_design import (
    DESIGN_CONDITION_LIMIT,
    DESIGN_MAX_ROWS,
    DESIGN_MEANS_KEPT,
    DESIGN_ROWS_KEPT,
    DESIGN_SOURCE,
    DESIGN_WIDE_COLUMNS,
)
from borges.analysis.harness_design_checks import DESIGN_CHECKS_SOURCE, PRODUCT_MAX_COLUMNS
from borges.analysis.harness_design_errors import DESIGN_ERRORS_SOURCE
from borges.analysis.harness_domain import DOMAIN_SOURCE
from borges.analysis.harness_effects import CHECKS_SOURCE, EFFECTS_SOURCE, RESTORED_NOTE
from borges.analysis.harness_filled import FILLED_SOURCE
from borges.analysis.harness_fingerprint import FINGERPRINT_SOURCE
from borges.analysis.harness_fit_rows import FIT_ROWS_SOURCE
from borges.analysis.harness_hints import HINTS_SOURCE
from borges.analysis.harness_missing_cut import MISSING_CUT_SOURCE
from borges.analysis.harness_normalise import NORMALISE_SOURCE
from borges.analysis.harness_outcome import LOG_LINK_MODELS, OUTCOME_MAX_ROWS, OUTCOME_SOURCE
from borges.analysis.harness_rebuild import REBUILD_SOURCE
from borges.analysis.harness_result_checks import RESULT_CHECKS_SOURCE
from borges.analysis.harness_split_half import SPLIT_HALF_SOURCE
from borges.analysis.harness_validate import VALIDATE_SOURCE
from borges.analysis.model_spec.render_design import ALIAS_NOTE

_TEMPLATE = """

def __borges_main():
    import json as _json
    import math as _math
    import numbers as _numbers
    import numpy as _np
    import os as _os
    import random as _random
    import sys as _sys
    import traceback as _tb

    import pandas as _pd

    step_id = __STEP_ID__
    option_id = __OPTION_ID__
    kind = __KIND__

__VALIDATE__
__SPLIT_HALF_CHECK__
__CHECKS__
__MISSING_CUT__

__DOMAIN__
__EFFECTS__
__HINTS__
__DESIGN__
__CLUSTER__
__FINGERPRINT__
    seen = {}
    _np.random.seed(0)
    _random.seed(0)
    try:
        state_df = _os.path.join("state", "df.parquet")
        state_ctx = _os.path.join("state", "ctx.json")
        df = _pd.read_parquet(state_df if _os.path.exists(state_df) else "data.parquet")
        df = df.reset_index(drop=True)
        if _os.path.exists(state_ctx):
            with open(state_ctx) as handle:
                ctx = _json.load(handle)
        else:
            ctx = {}
        rows_before = int(len(df))
        seen.update({"columns": list(map(str, df.columns)), "ctx": list(map(str, ctx))})
        _check_rebuilt(seen["columns"])
        nulls = df.isna().sum()
        seen["rows"] = int(len(df))
        seen["missing"] = {str(k): int(v) for k, v in nulls[nulls > 0].items()}
        seen["nonnumeric"] = [
            str(c) for c in df.columns
            if not _pd.api.types.is_numeric_dtype(df[c]) and not _pd.api.types.is_bool_dtype(df[c])
        ][:200]
        seen["ctx_lists"] = [
            str(item) for value in ctx.values() if isinstance(value, list) for item in value
        ]
        seen["frame"] = df
        trace = {
            "step_id": step_id,
            "option_id": option_id,
            "rows_before": rows_before,
            "rows_after": rows_before,
            "note": "",
        }
        if kind == "model":
            _install_design_probe()
            cluster_unit = __CLUSTER_BY__
            _install_cluster_hook(cluster_unit, df)
            raw_result = estimate(df, ctx)
            _check_clustered(cluster_unit)
            if isinstance(raw_result, dict) and isinstance(raw_result.get("note"), str):
                trace["note"] = raw_result["note"][:500]
            reported = raw_result.get("estimate") if isinstance(raw_result, dict) else None
            design = _design_payload(
                list(map(str, df.columns)), seen.get("ctx_lists", []), reported
            )
            if design is not None:
                trace["design"] = design
                design["outcome"] = _outcome_name(df, reported)
                _fit_keys(design, df)
                scale = _outcome_scale(df, reported)
                if scale is not None:
                    design["outcome_log"] = scale
                if __DESIGN_CHECK__ and design["deficient"]:
                    raise ValueError(_design_error(design, df))
                if __DESIGN_CHECK__ and design["no_intercept"]:
                    raise ValueError(_intercept_error(design))
                _check_offset(design)
                _check_weights(design)
                _check_main_effects(df, reported)
                _check_thin_cells(reported)
                _check_few_clusters(reported)
                ignored = _ignored_covariates(design, ctx, df, trace["note"])
                if __DESIGN_CHECK__ and ignored:
                    raise ValueError(_ignored_error(ignored, design))
                if design["aliased"]:
                    alias = __ALIAS_NOTE__ + ", ".join(design["aliased"])
                    trace["note"] = (alias + "; " + trace["note"] if trace["note"] else alias)[:500]
            result = _validate(raw_result)
            _check_standardised_outcome(reported)
            _use_model_rows(df, reported, result, trace)
            _check_model_cuts(df, result)
            if __SPLIT_HALF__:
                _check_split_half(df, ctx, result)
            _emit("BORGES_TRACE ", trace)
            _emit("BORGES_RESULT ", result)
            return
        ctx_before = set(ctx)
        before = df.copy() if __SPLIT_HALF__ else None
        groups = _group_counts(df)
        out, finite_before, domain = _apply_watching_domain(df, ctx)
        if not isinstance(out, _pd.DataFrame):
            raise TypeError("apply() must return a DataFrame, got " + type(out).__name__)
        out = _carry_group_attributes(df, out)
        out, restored = _restore_columns(df, out, seen["columns"], rows_before, kind)
        if restored:
            trace["note"] = (__RESTORED_NOTE__ + ", ".join(map(str, restored)))[:500]
        _check_columns(seen["columns"], rows_before, out, kind)
        _check_domain(out, finite_before, domain)
        _check_produces(out, ctx, df)
        _check_missing_cuts(df, out)
        _check_kept_rows(out, rows_before)
        _check_grouped_rows(groups, out, rows_before)
        _check_ctx(ctx)
        _check_ctx_columns(ctx, out, trace)
        _os.makedirs("state", exist_ok=True)
        out.to_parquet(state_df)
        with open(state_ctx, "w") as handle:
            _json.dump(ctx, handle)
        trace["rows_after"] = int(len(out))
        trace["fingerprint"] = _fingerprint(out, ctx)
        if __SPLIT_HALF__:
            try:
                trace["effects"] = _effects(before, out, ctx_before, ctx)
            except Exception:
                pass
        _emit("BORGES_TRACE ", trace)
    except BaseException as exc:
        lines = [line for line in _tb.format_exc().strip().splitlines() if line.strip()]
        roots = {_os.getcwd(), _os.path.realpath(_os.getcwd()), _sys.prefix, _sys.base_prefix}

        def _clean(text):
            for root in sorted(roots, key=len, reverse=True):
                text = text.replace(root + _os.sep, "").replace(root, "")
            return text

        _emit(
            "BORGES_ERROR ",
            {
                "type": type(exc).__name__,
                "message": _clean(
                    _explain(exc, seen)
                    + _encoding_hint(exc, seen, kind)
                    + _fit_key_hint(exc)
                    + _singular_hint(exc, seen, kind)
                    + _spelled_hint(exc, seen)
                    + _statsmodels_hint(exc)
                ),
                "where": _clean("\\n".join(lines[-6:])),
            },
        )
        _sys.exit(1)


__borges_main()
"""
MAIN_TEMPLATE = (
    _TEMPLATE.replace("__VALIDATE__", VALIDATE_SOURCE.strip("\n") + "\n")
    .replace("__NORMALISE__", NORMALISE_SOURCE.strip("\n"))
    .replace("__SPLIT_HALF_CHECK__", SPLIT_HALF_SOURCE.strip("\n"))
    .replace(
        "__CHECKS__",
        "\n\n".join(
            x.strip("\n") for x in (CHECKS_SOURCE, REBUILD_SOURCE, FIT_ROWS_SOURCE, FILLED_SOURCE)
        ),
    )
    .replace("__MISSING_CUT__", MISSING_CUT_SOURCE.strip("\n"))
    .replace("__DOMAIN__", DOMAIN_SOURCE.strip("\n"))
    .replace("__EFFECTS__", EFFECTS_SOURCE.strip("\n"))
    .replace("__HINTS__", HINTS_SOURCE.strip("\n"))
    .replace(
        "__DESIGN__",
        "\n\n".join(
            x.strip("\n")
            for x in (
                DESIGN_SOURCE,
                DESIGN_ERRORS_SOURCE,
                DESIGN_CHECKS_SOURCE,
                CELL_CHECK_SOURCE,
                CLUSTER_COUNT_SOURCE,
                COVARIATES_SOURCE,
                OUTCOME_SOURCE,
                RESULT_CHECKS_SOURCE,
            )
        ),
    )
    .replace("__OUTCOME_MAX_ROWS__", repr(OUTCOME_MAX_ROWS))
    .replace("__LOG_LINK_MODELS__", repr(LOG_LINK_MODELS))
    .replace("__PRODUCT_MAX_COLUMNS__", repr(PRODUCT_MAX_COLUMNS))
    .replace("__MIN_CELL_ROWS__", repr(MIN_CELL_ROWS))
    .replace("__MIN_CLUSTERS__", repr(MIN_CLUSTERS))
    .replace("__CLUSTER__", CLUSTER_SOURCE.strip("\n"))
    .replace("__CLUSTER_MODELS__", repr(CLUSTER_MODELS))
    .replace("__FINGERPRINT__", FINGERPRINT_SOURCE.strip("\n"))
    .replace("__DESIGN_CONDITION_LIMIT__", repr(DESIGN_CONDITION_LIMIT))
    .replace("__DESIGN_MAX_ROWS__", repr(DESIGN_MAX_ROWS))
    .replace("__DESIGN_ROWS_KEPT__", repr(DESIGN_ROWS_KEPT))
    .replace("__DESIGN_MEANS_KEPT__", repr(DESIGN_MEANS_KEPT))
    .replace("__ALIAS_NOTE__", repr(ALIAS_NOTE))
    .replace("__RESTORED_NOTE__", repr(RESTORED_NOTE))
    .replace("__DESIGN_WIDE_COLUMNS__", repr(DESIGN_WIDE_COLUMNS))
)
