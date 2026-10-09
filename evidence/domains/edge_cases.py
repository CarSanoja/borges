import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D = Path(__file__).parent
rng = np.random.default_rng(20261010)


def audit_hours():
    n, managers = 1500, 45
    complexity = rng.integers(1, 6, n)
    revenue = np.round(np.exp(rng.normal(4.2, 1.0, n)), 1)
    hours = np.round(np.clip(rng.normal(20 + 6 * complexity, 8), 2, None), 1)
    lin = -3.0 + 0.55 * complexity - 0.04 * hours + 0.1 * np.log(revenue)
    restated = rng.binomial(1, 1 / (1 + np.exp(-lin)))
    missing = rng.random(n) < np.where(complexity >= 4, 0.25, 0.05)
    logged = np.where(missing, np.nan, hours)
    df = pd.DataFrame({
        "engagement_id": [f"NB-{24000 + i}" for i in range(n)],
        "manager_id": [f"M{m:02d}" for m in rng.integers(0, managers, n)],
        "client_complexity": complexity,
        "client_revenue_musd": revenue,
        "manager_review_hours": logged,
        "restatement_within_2y": restated,
    })
    df.to_csv(D / "northbridge_review_hours.csv", index=False)
    full = df.assign(manager_review_hours=hours)
    naive = smf.logit("restatement_within_2y ~ manager_review_hours", df.dropna()).fit(disp=0)
    adj = smf.logit(
        "restatement_within_2y ~ manager_review_hours + client_complexity + np.log(client_revenue_musd)",
        df.dropna(),
    ).fit(disp=0)
    oracle = smf.logit(
        "restatement_within_2y ~ manager_review_hours + client_complexity + np.log(client_revenue_musd)",
        full,
    ).fit(disp=0)
    k = "manager_review_hours"
    return {"file": "northbridge_review_hours.csv", "truth": {
        "planted_logodds_per_hour": -0.04,
        "naive_complete_cases": [float(naive.params[k]), float(naive.pvalues[k])],
        "adjusted_complete_cases": [float(adj.params[k]), float(adj.pvalues[k])],
        "adjusted_all_rows": [float(oracle.params[k]), float(oracle.pvalues[k])],
        "missing_share": float(missing.mean()),
        "trap": "continuous exposure; complex clients get more hours and restate more; hours missing mostly for complex clients"}}


def clinic_bleeding():
    sites = ["North", "South", "East", "West", "Rural"]
    n = 3000
    site = rng.choice(sites, n, p=[0.3, 0.25, 0.2, 0.2, 0.05])
    new_drug = np.where(site == "Rural", 0, rng.binomial(1, 0.5, n))
    age = np.clip(rng.normal(70, 9, n), 40, 95).round()
    kidney = rng.binomial(1, 0.2, n)
    lin = -4.6 + 0.7 * new_drug + 0.03 * (age - 70) + 0.8 * kidney
    lin = np.where(site == "Rural", -30.0, lin)
    bleed = rng.binomial(1, 1 / (1 + np.exp(-lin)))
    df = pd.DataFrame({
        "patient_mrn": [f"MRN{rng.integers(1000000, 9999999)}" for _ in range(n)],
        "site": site,
        "age": age.astype(int),
        "chronic_kidney_disease": kidney,
        "new_anticoagulant": new_drug,
        "major_bleed_90d": bleed,
    })
    df.to_csv(D / "clinic_bleeding.csv", index=False)
    keep = df[df.site != "Rural"]
    adj = smf.logit("major_bleed_90d ~ new_anticoagulant + age + chronic_kidney_disease", keep).fit(disp=0)
    k = "new_anticoagulant"
    return {"file": "clinic_bleeding.csv", "truth": {
        "planted_logodds": 0.7,
        "adjusted_without_rural": [float(adj.params[k]), float(adj.pvalues[k])],
        "event_rate": float(bleed.mean()),
        "rural_events": int(bleed[site == "Rural"].sum()),
        "trap": "rare outcome; the rural site has no events and never used the new drug, so site dummies separate perfectly"}}


def k12_paired():
    students = 24
    ability = rng.normal(100, 12, students)
    gain = 4.0 + rng.normal(0, 2.5, students)
    before = ability + rng.normal(0, 2, students)
    after = ability + gain + rng.normal(0, 2, students)
    ids = [f"A{i:02d}" for i in range(students)]
    df = pd.DataFrame({
        "alumno": ids * 2,
        "momento": ["antes"] * students + ["despues"] * students,
        "puntaje_lectura": np.round(np.concatenate([before, after]), 1),
        "grado": list(rng.choice([3, 4, 5], students)) * 2,
    }).sample(frac=1, random_state=3).reset_index(drop=True)
    df.to_csv(D / "k12_verano_pareado.csv", index=False)
    wide = df.pivot(index="alumno", columns="momento", values="puntaje_lectura")
    diff = wide["despues"] - wide["antes"]
    from scipy import stats

    paired = stats.ttest_rel(wide["despues"], wide["antes"])
    unpaired = stats.ttest_ind(wide["despues"], wide["antes"])
    return {"file": "k12_verano_pareado.csv", "truth": {
        "planted_gain": 4.0,
        "paired": [float(diff.mean()), float(paired.pvalue)],
        "unpaired": [float(diff.mean()), float(unpaired.pvalue)],
        "trap": "long format, two rows per student: only a paired analysis sees the gain"}}


def bank_staggered():
    branches, months = 30, 24
    start = rng.choice([8, 12, 16, 99], branches, p=[0.25, 0.25, 0.25, 0.25])
    rows = []
    level = rng.normal(20, 4, branches)
    for b in range(branches):
        for m in range(months):
            treated = int(m >= start[b])
            mean = level[b] + 0.15 * m - 3.0 * treated
            rows.append({
                "sucursal": f"S{b:02d}",
                "mes": f"2024-{m % 12 + 1:02d}" if m < 12 else f"2025-{m % 12 + 1:02d}",
                "mes_indice": m,
                "guion_nuevo": treated,
                "reclamos": int(max(0, round(rng.normal(mean, 2.5)))),
            })
    df = pd.DataFrame(rows).drop(columns="mes_indice")
    df.to_csv(D / "banco_reclamos_escalonado.csv", index=False)
    df["t"] = pd.to_datetime(df["mes"]).rank(method="dense")
    twfe = smf.ols("reclamos ~ guion_nuevo + C(sucursal) + C(mes)", df).fit(
        cov_type="cluster", cov_kwds={"groups": df["sucursal"].astype("category").cat.codes})
    pooled = smf.ols("reclamos ~ guion_nuevo", df).fit()
    k = "guion_nuevo"
    return {"file": "banco_reclamos_escalonado.csv", "truth": {
        "planted_effect": -3.0,
        "two_way_fixed_effects": [float(twfe.params[k]), float(twfe.pvalues[k])],
        "pooled": [float(pooled.params[k]), float(pooled.pvalues[k])],
        "trap": "staggered rollout by branch and month with an upward trend: comparing months mixes the trend into the effect"}}


if __name__ == "__main__":
    truths = {"audit_hours": audit_hours(), "clinic_bleeding": clinic_bleeding(),
              "k12_paired": k12_paired(), "bank_staggered": bank_staggered()}
    old = json.loads((D / "truth.json").read_text())
    old.update(truths)
    (D / "truth.json").write_text(json.dumps(old, indent=1, ensure_ascii=False))
    print(json.dumps({k: v["truth"] for k, v in truths.items()}, indent=1, ensure_ascii=False))
