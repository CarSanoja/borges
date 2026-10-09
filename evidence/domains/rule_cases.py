import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

D = Path(__file__).parent
rng = np.random.default_rng(20261012)


def bank_headers_es():
    n = 1500
    tenure = rng.integers(0, 25, n)
    advisor = rng.binomial(1, 1 / (1 + np.exp(-(-1.5 + 0.12 * tenure))))
    products = rng.poisson(np.exp(0.3 + 0.04 * tenure + 0.15 * advisor))
    df = pd.DataFrame({
        "Nº Cliente": [f"C-{70000 + i}" for i in range(n)],
        "Antigüedad (años)": tenure,
        "Región": rng.choice(["Norte", "Centro", "Sur"], n),
        "¿Asesor asignado?": np.where(advisor == 1, "Sí", "No"),
        "Productos contratados": products,
    })
    df.to_csv(D / "banco_asesores.csv", index=False, encoding="utf-8")
    coded = pd.DataFrame({"tenure": tenure, "advisor": advisor, "products": products})
    adj = smf.poisson("products ~ advisor + tenure", coded).fit(disp=0)
    raw = smf.poisson("products ~ advisor", coded).fit(disp=0)
    return {"file": "banco_asesores.csv", "truth": {
        "planted_log_rate": 0.15,
        "adjusted_log_rate": [float(adj.params["advisor"]), float(adj.pvalues["advisor"])],
        "raw_log_rate": [float(raw.params["advisor"]), float(raw.pvalues["advisor"])],
        "trap": "headers with accents, spaces and symbols; notes keyed by those headers; Sí/No flag; tenure drives both"}}


def k12_threshold():
    n = 600
    prior = rng.normal(60, 12, n)
    hours = np.clip(rng.gamma(2.0, 1.5, n) + 0.03 * (70 - prior), 0, None).round(1)
    score = 15 + 0.75 * prior + 0.6 * hours + rng.normal(0, 6, n)
    df = pd.DataFrame({
        "student": [f"S{i:04d}" for i in range(n)],
        "prior_math": prior.round(1),
        "weekly_tutoring_hours": hours,
        "spring_math": score.round(1),
    })
    df.to_csv(D / "k12_tutoring_hours.csv", index=False)
    adj = smf.ols("spring_math ~ weekly_tutoring_hours + prior_math", df).fit(cov_type="HC1")
    k = "weekly_tutoring_hours"
    low, high = adj.conf_int().loc[k]
    test = adj.t_test(f"{k} = 0.5")
    return {"file": "k12_tutoring_hours.csv", "truth": {
        "planted_points_per_hour": 0.6,
        "adjusted_points_per_hour": [float(adj.params[k]), float(adj.pvalues[k])],
        "ci": [float(low), float(high)],
        "p_against_threshold": float(test.pvalue) / 2,
        "trap": "the rule asks for at least 0.5 points per hour; the p-value of the coefficient tests 0, not 0.5"}}


def audit_rate_ratio():
    n = 700
    size = rng.integers(25, 400, n)
    new = rng.binomial(1, 0.5, n)
    risk = rng.integers(1, 4, n)
    rate = 0.04 * np.exp(-0.36 * new + 0.25 * (risk - 2))
    exceptions = rng.poisson(rate * size)
    df = pd.DataFrame({
        "engagement": [f"NB-{52000 + i}" for i in range(n)],
        "risk_tier": risk,
        "new_sampling_method": new,
        "items_tested": size,
        "exceptions_found": exceptions,
    })
    df.to_csv(D / "northbridge_sampling.csv", index=False)
    fit = smf.glm("exceptions_found ~ new_sampling_method + C(risk_tier)", df,
                  family=sm.families.Poisson(), offset=np.log(df["items_tested"])).fit()
    k = "new_sampling_method"
    low, high = np.exp(fit.conf_int().loc[k])
    plain = smf.glm("exceptions_found ~ new_sampling_method + C(risk_tier)", df,
                    family=sm.families.Poisson()).fit()
    return {"file": "northbridge_sampling.csv", "truth": {
        "planted_rate_ratio": float(np.exp(-0.36)),
        "rate_ratio": [float(np.exp(fit.params[k])), float(fit.pvalues[k])],
        "ci": [float(low), float(high)],
        "no_offset_ratio": float(np.exp(plain.params[k])),
        "trap": "rule on a rate ratio below 0.8, not 1; samples differ in size, so the count needs an offset"}}


if __name__ == "__main__":
    truths = {"bank_headers_es": bank_headers_es(), "k12_threshold": k12_threshold(),
              "audit_rate_ratio": audit_rate_ratio()}
    old = json.loads((D / "truth.json").read_text())
    old.update(truths)
    (D / "truth.json").write_text(json.dumps(old, indent=1, ensure_ascii=False))
    print(json.dumps({k: v["truth"] for k, v in truths.items()}, indent=1, ensure_ascii=False))
