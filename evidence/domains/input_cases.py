import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

D = Path(__file__).parent
rng = np.random.default_rng(20261011)


def audit_text_flags():
    n = 1200
    risk = rng.integers(1, 4, n)
    walkthrough = rng.binomial(1, 0.25 + 0.15 * (risk - 1))
    lin = -2.2 + 0.6 * (risk - 1) - 0.8 * walkthrough
    finding = rng.binomial(1, 1 / (1 + np.exp(-lin)))
    yes = np.array(["Yes", "yes", "YES ", "Y"])
    no = np.array(["No", "no", "NO", "N "])
    pick = rng.integers(0, 4, n)
    df = pd.DataFrame({
        "engagement": [f"NB-{31000 + i}" for i in range(n)],
        "risk_tier": np.array(["Low", "Medium", "High"])[risk - 1],
        "control_walkthrough": np.where(walkthrough == 1, yes[pick], no[pick]),
        "material_finding": np.where(finding == 1, "Yes", "No"),
    })
    df.to_csv(D / "northbridge_walkthroughs.csv", index=False)
    coded = df.assign(w=walkthrough, f=finding)
    fit = smf.logit("f ~ w + C(risk_tier)", coded).fit(disp=0)
    row = fit.get_margeff(at="overall", dummy=True).summary_frame().loc["w"]
    return {"file": "northbridge_walkthroughs.csv", "truth": {
        "adjusted_ame": [float(row["dy/dx"]), float(row["Pr(>|z|)"])],
        "adjusted_logodds": float(fit.params["w"]),
        "trap": "outcome and exposure are text with inconsistent case and spaces; riskier engagements get more walkthroughs"}}


def clinic_survival():
    n = 900
    protocol = rng.binomial(1, 0.5, n)
    age = np.clip(rng.normal(68, 10, n), 30, 95).round()
    hazard = 0.006 * np.exp(-0.5 * protocol + 0.02 * (age - 68))
    time = rng.exponential(1 / hazard)
    observed = (time <= 90).astype(int)
    days = np.minimum(np.ceil(time), 90).astype(int)
    df = pd.DataFrame({
        "patient": [f"P{i:04d}" for i in range(n)],
        "age": age.astype(int),
        "new_protocol": protocol,
        "days_followed": days,
        "readmitted": observed,
    })
    df.to_csv(D / "clinic_time_to_readmission.csv", index=False)
    cox = sm.PHReg(df["days_followed"], df[["new_protocol", "age"]], status=df["readmitted"]).fit()
    naive = smf.ols("days_followed ~ new_protocol + age", df).fit()
    return {"file": "clinic_time_to_readmission.csv", "truth": {
        "planted_log_hazard_ratio": -0.5,
        "cox_log_hr": [float(cox.params[0]), float(cox.pvalues[0])],
        "naive_ols_days": [float(naive.params["new_protocol"]), float(naive.pvalues["new_protocol"])],
        "censored_share": float(1 - observed.mean()),
        "trap": "time to readmission censored at 90 days; most patients are never readmitted"}}


def k12_percent():
    classes = 160
    poverty = rng.uniform(0, 1, classes)
    program = rng.binomial(1, 0.3 + 0.4 * poverty)
    prior = np.clip(70 - 25 * poverty + rng.normal(0, 6, classes), 5, 98)
    proficient = np.clip(prior + 3.0 + 5.0 * program - 8 * poverty + rng.normal(0, 5, classes), 0, 100)
    df = pd.DataFrame({
        "class_id": [f"C{i:03d}" for i in range(classes)],
        "pct_free_lunch": np.round(100 * poverty, 1),
        "tutoring_program": program,
        "pct_proficient_last_year": np.round(prior, 1),
        "pct_proficient": np.round(proficient, 1),
    })
    df.to_csv(D / "k12_proficiency_percent.csv", index=False)
    adj = smf.ols("pct_proficient ~ tutoring_program + pct_proficient_last_year + pct_free_lunch", df).fit()
    raw = smf.ols("pct_proficient ~ tutoring_program", df).fit()
    k = "tutoring_program"
    return {"file": "k12_proficiency_percent.csv", "truth": {
        "planted_points": 5.0,
        "adjusted_points": [float(adj.params[k]), float(adj.pvalues[k])],
        "raw_points": [float(raw.params[k]), float(raw.pvalues[k])],
        "trap": "the outcome is already in percent (0-100); the rule asks for percentage points; poorer classes get the program"}}


def bank_eu_format():
    n = 800
    income = np.exp(rng.normal(7.6, 0.5, n))
    waiver = rng.binomial(1, 0.5, n)
    start = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    balance = 0.8 * income + 350 * waiver + rng.normal(0, 600, n)
    df = pd.DataFrame({
        "cliente": [f"CL{i:05d}" for i in range(n)],
        "fecha_alta": start.strftime("%d/%m/%Y"),
        "ingreso_mensual": income,
        "exencion_comision": waiver,
        "saldo_medio": balance,
    })
    text = df.assign(
        ingreso_mensual=[f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in income],
        saldo_medio=[f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in balance],
    )
    text.to_csv(D / "banco_exencion_eu.csv", index=False, sep=";", encoding="utf-8-sig")
    fit = smf.ols("saldo_medio ~ exencion_comision + ingreso_mensual", df).fit(cov_type="HC1")
    k = "exencion_comision"
    return {"file": "banco_exencion_eu.csv", "truth": {
        "planted_euros": 350.0,
        "adjusted_euros": [float(fit.params[k]), float(fit.pvalues[k])],
        "trap": "semicolon CSV with thousands dots and decimal commas (1.234,56) and dd/mm/yyyy dates"}}


if __name__ == "__main__":
    truths = {"audit_text_flags": audit_text_flags(), "clinic_survival": clinic_survival(),
              "k12_percent": k12_percent(), "bank_eu_format": bank_eu_format()}
    old = json.loads((D / "truth.json").read_text())
    old.update(truths)
    (D / "truth.json").write_text(json.dumps(old, indent=1, ensure_ascii=False))
    print(json.dumps({k: v["truth"] for k, v in truths.items()}, indent=1, ensure_ascii=False))
