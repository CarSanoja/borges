from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.claim_compare import check_claim
from borges.analysis.models import AnalysisPlan
from borges.garden.aliased import aliased_caveats, rebuilt_caveats, tangled_caveats
from borges.garden.covariate_sample import baseline_sample_caveats, covariate_sample_caveats
from borges.garden.discrete_quantile import discrete_quantile_caveats
from borges.garden.duplicate_rows import duplicate_row_caveats
from borges.garden.failed_caveat import failed_caveat, untested_decision_caveats
from borges.garden.filtered_rows import filtered_rows_caveats
from borges.garden.hc_variant import hc_variant_caveats
from borges.garden.influence import build_report
from borges.garden.likelihood_question import likelihood_caveats
from borges.garden.models import Report
from borges.garden.outcome_scale import scale_note
from borges.garden.repeated_units import repeated_unit_caveats
from borges.garden.scaled_outcome import scaled_outcome_caveats
from borges.runs.pipeline_caveats import claim_caveats, judge_caveats, merge_caveats, report_caveats

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


def assemble_report(pipeline: Pipeline, plan: AnalysisPlan) -> Report:
    pipeline.caveats.extend(pipeline.armor.caveats())
    pipeline.report = build_report(plan, pipeline.garden, pipeline.flip)
    pipeline.report.search = pipeline.search
    pipeline.report.coding = pipeline.coding if pipeline.coding.options else None
    failed = failed_caveat(plan, pipeline.garden)
    threshold = plan.decision_rule.threshold
    pipeline.caveats.extend(report_caveats(pipeline.report, pipeline.flip, threshold, failed))
    pipeline.caveats.extend(judge_caveats(pipeline.coding))
    pipeline.caveats.extend(
        [
            *aliased_caveats(pipeline.garden),
            *tangled_caveats(pipeline.garden),
            *rebuilt_caveats(pipeline.garden),
            *scaled_outcome_caveats(pipeline.garden),
            *baseline_sample_caveats(plan, pipeline.garden),
            *filtered_rows_caveats(plan, pipeline.garden),
            *covariate_sample_caveats(plan, pipeline.garden),
            *discrete_quantile_caveats(
                pipeline.garden, pipeline.flip and pipeline.flip.universe_id
            ),
            *hc_variant_caveats(pipeline.garden),
            *untested_decision_caveats(plan, pipeline.garden),
            *repeated_unit_caveats(plan, pipeline.garden),
            *duplicate_row_caveats(plan),
            *likelihood_caveats(plan, pipeline.garden),
        ]
    )
    note = scale_note(pipeline.garden)
    if note is not None:
        pipeline.caveats.append(note)
    pipeline.report.claim_check = check_claim(
        pipeline.resolved.analysis, pipeline.report.original_result, plan.decision_rule
    )
    pipeline.report.caveats = merge_caveats(
        claim_caveats(pipeline.report.claim_check), pipeline.caveats, pipeline.report.caveats
    )
    return pipeline.report
