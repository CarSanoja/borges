"""A repair hint for a Cox model fitted with statsmodels' PHReg.

Three clinic runs on 9 October 2026 (r_20261009T085134_fe4c15, r_20261009T092811_c73eca,
r_20261009T093251_469e47) asked for the log hazard ratio of readmission. The coder reached for
lifelines, R's Surv(), cov_type="robust", get_robustcov_results and the event as the second
positional argument; statsmodels answered "cov_type not recognized", "no attribute 'wexog'" or
"multiple values for argument 'exog'", and no repair learned from that how PHReg is called.
"""

from __future__ import annotations

PHREG_SOURCE = r"""
    def _phreg_hint(exc):
        names, tb = [], exc.__traceback__
        while tb is not None:
            names += [type(v).__name__ for v in list(tb.tb_frame.f_locals.values())[:50]]
            tb = tb.tb_next
        if "PHReg" not in str(exc) and not {"PHReg", "PHRegResults"} & set(names):
            return ""
        return (
            " | a Cox model is smf.phreg('days ~ exposure + age', data, status=data['event'])"
            + " or sm.PHReg(time, X, status=event), the event always as status=; robust errors"
            + " come from .fit(groups=np.arange(len(data))) or groups=<cluster column>, never"
            + " from cov_type or get_robustcov_results; params, pvalues and conf_int() are"
            + " arrays: i = fit.model.exog_names.index(name), then fit.params[i],"
            + " fit.pvalues[i] and fit.conf_int()[i]"
        )
"""
