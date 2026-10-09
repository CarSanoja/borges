import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

D = Path(__file__).parent
rng = np.random.default_rng(20261009)
FIRST = ["Alex", "Maria", "Jordan", "Priya", "Tomas", "Lucia", "Kenji", "Amara", "Diego", "Sofia",
         "Noah", "Elena", "Omar", "Hana", "Lucas", "Ines", "Ravi", "Clara", "Mateo", "Zoe"]
LAST = ["Moreno", "Okafor", "Lindqvist", "Tanaka", "Haddad", "Novak", "Castillo", "Brennan",
        "Duarte", "Ivanova", "Mensah", "Keller", "Sato", "Ferreira", "Walsh", "Rojas"]


def audit():
    n, partners = 1200, 40
    pid = rng.integers(0, partners, n)
    names = [f"{FIRST[i % 20]} {LAST[(i * 7) % 16]}" for i in range(partners)]
    partner_effect = rng.normal(0, 0.25, partners)
    risk = rng.integers(1, 6, n)
    revenue = np.round(np.exp(rng.normal(4, 1.1, n)), 1)
    p_eqr = 1 / (1 + np.exp(-(-2.2 + 0.75 * risk)))
    eqr = rng.binomial(1, p_eqr)
    rate = np.exp(-0.2 + 0.32 * risk + 0.12 * np.log(revenue) - 0.16 * eqr + partner_effect[pid])
    adj = rng.poisson(rate)
    df = pd.DataFrame({
        "engagement_id": [f"E{100000 + i}" for i in range(n)],
        "partner_id": [f"P{p:03d}" for p in pid],
        "partner_name": [names[p] for p in pid],
        "client_risk_rating": risk,
        "client_revenue_musd": revenue,
        "eqr_review": eqr,
        "audit_adjustments": adj,
    })
    df.to_csv(D / "northbridge_adjustments.csv", index=False)
    naive = smf.poisson("audit_adjustments ~ eqr_review", df).fit(disp=0)
    adjm = smf.poisson("audit_adjustments ~ eqr_review + client_risk_rating + np.log(client_revenue_musd)", df).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": df["partner_id"].astype("category").cat.codes})
    return {"file": "northbridge_adjustments.csv", "truth": {
        "planted_log_rate": -0.16,
        "naive": [float(naive.params["eqr_review"]), float(naive.pvalues["eqr_review"])],
        "adjusted_clustered": [float(adjm.params["eqr_review"]), float(adjm.pvalues["eqr_review"])],
        "trap": "reviews go to riskier clients; loaded question; engagements nested in 40 partners; partner_name"}}


def clinic():
    n = 2000
    ward = rng.choice(["A", "B", "C", "D"], n)
    new = np.isin(ward, ["A", "B"]).astype(int)
    comorb = rng.poisson(np.where(new == 1, 3.2, 2.2))
    age = np.clip(rng.normal(np.where(new == 1, 71, 64), 11), 18, 99).round()
    lin = -2.3 + 0.28 * comorb + 0.02 * (age - 65) - 0.45 * new
    any_r = rng.binomial(1, 1 / (1 + np.exp(-lin)))
    extra = rng.poisson(0.6 + 0.15 * comorb)
    readm = any_r * (1 + extra)
    los = np.round(np.exp(rng.normal(1.4 + 0.08 * comorb, 0.45)), 1)
    df = pd.DataFrame({
        "mrn": [f"MRN{rng.integers(1000000, 9999999)}" for _ in range(n)],
        "ward": ward,
        "age": age.astype(int),
        "comorbidity_index": comorb,
        "length_of_stay_days": los,
        "discharge_protocol_new": new,
        "readmissions_90d": readm,
    })
    df.to_csv(D / "clinic_readmissions.csv", index=False)
    df["any"] = (df.readmissions_90d > 0).astype(int)
    naive = smf.logit("any ~ discharge_protocol_new", df).fit(disp=0)
    adjm = smf.logit("any ~ discharge_protocol_new + comorbidity_index + age", df).fit(disp=0)
    count = smf.poisson("readmissions_90d ~ discharge_protocol_new + comorbidity_index + age", df).fit(disp=0)
    return {"file": "clinic_readmissions.csv", "truth": {
        "planted_logodds_any": -0.45,
        "naive_any": [float(naive.params.iloc[1]), float(naive.pvalues.iloc[1])],
        "adjusted_any": [float(adjm.params.iloc[1]), float(adjm.pvalues.iloc[1])],
        "adjusted_count_lograte": [float(count.params.iloc[1]), float(count.pvalues.iloc[1])],
        "trap": "likelihood question on a count; sicker, older patients on the new-protocol wards; MRN"}}


def k12():
    schools, per = 10, 6
    school = np.repeat(np.arange(schools), per)
    treated_school = np.isin(np.arange(schools), [0, 2, 3, 6, 8]).astype(int)
    new = treated_school[school]
    school_effect = rng.normal(0, 5, schools)
    prior = rng.normal(210, 8, schools * per)
    score = 40 + 0.8 * prior + 2.0 * new + school_effect[school] + rng.normal(0, 3, schools * per)
    df = pd.DataFrame({
        "classroom_id": [f"C{i:03d}" for i in range(schools * per)],
        "school_id": [f"S{s:02d}" for s in school],
        "new_curriculum": new,
        "prior_year_reading": prior.round(1),
        "reading_score": score.round(1),
        "class_size": rng.integers(18, 31, schools * per),
    })
    df.to_csv(D / "k12_curriculum_small.csv", index=False)
    ols = smf.ols("reading_score ~ new_curriculum + prior_year_reading", df).fit()
    cl = smf.ols("reading_score ~ new_curriculum + prior_year_reading", df).fit(
        cov_type="cluster", cov_kwds={"groups": df["school_id"].astype("category").cat.codes})
    return {"file": "k12_curriculum_small.csv", "truth": {
        "planted_effect": 2.0,
        "ols": [float(ols.params["new_curriculum"]), float(ols.pvalues["new_curriculum"])],
        "school_clustered": [float(cl.params["new_curriculum"]), float(cl.pvalues["new_curriculum"])],
        "trap": "60 classrooms, curriculum assigned by school (10 schools): classroom rows are not independent"}}


def bank():
    clients, per = 3000, 4
    n = clients * per
    cid = np.repeat(np.arange(clients), per)
    canal = rng.choice(["web", "app", "oficina"], n, p=[0.4, 0.45, 0.15])
    alerta = np.where(canal == "app", rng.binomial(1, 0.75, n), rng.binomial(1, 0.2, n))
    importe = np.round(np.exp(rng.normal(4.2, 1.0, n)), 2)
    base = np.select([canal == "app", canal == "web"], [-3.6, -4.4], -5.4)
    lin = base + 0.25 * (np.log(importe) - 4.2) - 0.8 * alerta
    fraude = rng.binomial(1, 1 / (1 + np.exp(-lin)))
    df = pd.DataFrame({
        "id_cliente": [f"CL{c:05d}" for c in cid],
        "canal": canal,
        "importe_eur": importe,
        "alerta_nueva": alerta,
        "fraude": fraude,
    })
    text = df.to_csv(index=False, sep=";", decimal=",")
    (D / "banco_fraude_es.csv").write_bytes(text.encode("utf-8-sig"))
    naive = smf.logit("fraude ~ alerta_nueva", df).fit(disp=0)
    adjm = smf.logit("fraude ~ alerta_nueva + C(canal) + np.log(importe_eur)", df).fit(disp=0)
    return {"file": "banco_fraude_es.csv", "truth": {
        "planted_logodds": -0.8, "fraud_rate": float(df.fraude.mean()),
        "naive": [float(naive.params["alerta_nueva"]), float(naive.pvalues["alerta_nueva"])],
        "adjusted": [float(adjm.params["alerta_nueva"]), float(adjm.pvalues["alerta_nueva"])],
        "trap": "Spanish ';' CSV with decimal comma and BOM; alerts rolled out on the riskier app channel; rare outcome; 4 rows per client"}}


truths = {"audit_adjustments": audit(), "clinic_readmissions": clinic(),
          "k12_small": k12(), "bank_fraud_es": bank()}
old = json.loads((D / "truth.json").read_text())
old.update(truths)
(D / "truth.json").write_text(json.dumps(old, indent=1))
print(json.dumps({k: v["truth"] for k, v in truths.items()}, indent=1))
