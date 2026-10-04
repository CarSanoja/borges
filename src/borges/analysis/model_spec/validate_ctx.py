from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput

CTX_COVARIATES = re.compile(r"""ctx\s*\[\s*["']covariates["']\s*\]|covariates from ctx""")


def ctx_problems(spec: ModelSpecOutput, ctx_names: list[str], option_text: str) -> list[str]:
    problems = []
    if CTX_COVARIATES.search(option_text) and not spec.covariates_from_ctx:
        problems.append(
            "the option uses the covariate list an earlier step stores in ctx['covariates']: "
            "set covariates_from_ctx to true"
        )
    if spec.covariates_from_ctx:
        problems += [
            f"'{name}' is chosen by the covariate step through ctx['covariates']; listing it "
            "in covariates as well keeps it in every universe and makes that step's choice "
            "dead, so leave it to ctx"
            for name in spec.covariates
            if name in ctx_names
        ]
    return problems
