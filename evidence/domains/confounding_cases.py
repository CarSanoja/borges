import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

OUT = Path(__file__).parent
rng = np.random.default_rng(20261009)
FIRST = ["James", "Maria", "Robert", "Linda", "Michael", "Sarah", "David", "Laura", "Daniel", "Emma",
         "Carlos", "Lucia", "Javier", "Ana", "Pablo", "Elena", "Diego", "Sofia", "Andres", "Paula"]
LAST = ["Smith", "Garcia", "Johnson", "Martinez", "Brown", "Lopez", "Davis", "Gonzalez", "Wilson",
        "Perez", "Taylor", "Sanchez", "Moore", "Ramirez", "Clark", "Torres", "Lewis", "Flores"]


def names(n):
    return [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(n)]


def audit():
    n = 900
    rev = np.exp(rng.normal(5.0, 1.2, n))
    first = rng.binomial(1, 0.18, n)
    p_tool = 1 / (1 + np.exp(-(-0.6 + 0.9 * (np.log(rev) - 5.0))))
    tool = rng.binomial(1, p_tool)
    budget = np.round(np.exp(rng.normal(np.log(400) + 0.35 * (np.log(rev) - 5), 0.4)), -1)
    overrun = 0.14 - 0.035 * (np.log(rev) - 5.0) + 0.07 * first + rng.normal(0, 0.09, n)
    actual = np.round(budget * (1 + overrun), 1)
    partners = names(60)
    pidx = rng.integers(0, 60, n)
    df = pd.DataFrame({
        "engagement_code": [f"ENG-2025-{i:04d}" for i in range(1, n + 1)],
        "partner_name": [partners[i] for i in pidx],
        "partner_email": [partners[i].lower().replace(" ", ".") + "@northbridge-assurance.example" for i in pidx],
        "office": rng.choice(["Boston", "Chicago", "Dallas", "Denver", "Atlanta", "Seattle", "Miami", "Phoenix"], n),
        "industry": rng.choice(["Banking", "Insurance", "Retail", "Manufacturing", "Technology", "Healthcare"], n),
        "client_revenue_musd": np.round(rev, 1),
        "first_year_client": first,
        "team_size": rng.integers(3, 15, n),
        "budget_hours": budget,
        "actual_hours": actual,
        "analytics_tool": tool,
        "review_findings": rng.poisson(1.2 + 0.4 * first),
    })
    df["overrun"] = df.actual_hours / df.budget_hours - 1
    naive = smf.ols("overrun ~ analytics_tool", df).fit(cov_type="HC1")
    adj = smf.ols("overrun ~ analytics_tool + np.log(client_revenue_musd) + first_year_client", df).fit(cov_type="HC1")
    d = naive.params["analytics_tool"]
    df.drop(columns="overrun").to_csv(OUT / "audit_engagements.csv", index=False)
    request = {
        "question": "Did the data-analytics tool reduce budget overruns on our audit engagements?",
        "llm": "nebius",
        "decision_rule": {"metric": "effect of analytics_tool on the budget overrun (actual_hours / budget_hours - 1)",
                          "comparator": "lt", "threshold": 0, "alpha": 0.05,
                          "positive_label": "TOOL CUTS OVERRUNS", "negative_label": "NO CLEAR EFFECT"},
        "analysis": (f"Audit quality memo FY2025: we compared the overrun (actual_hours / budget_hours - 1) of "
                     f"engagements that used the analytics tool with those that did not. Tool engagements ran "
                     f"{abs(d) * 100:.1f} points lower (p < 0.001, n = {n}). We plan to make the tool mandatory."),
        "column_notes": {"actual_hours": "hours charged to the engagement code at sign-off",
                         "budget_hours": "hours approved at the planning stage",
                         "analytics_tool": "1 = the team used the data-analytics tool for journal-entry testing",
                         "client_revenue_musd": "client annual revenue, millions of USD"},
    }
    truth = {"planted_effect": 0.0, "naive": [d, naive.pvalues["analytics_tool"]],
             "adjusted": [adj.params["analytics_tool"], adj.pvalues["analytics_tool"]],
             "trap": "tool assigned to larger clients; larger clients overrun less"}
    return "audit_tool", "audit_engagements.csv", request, truth


def clinic():
    n = 2400
    month = rng.integers(1, 13, n)
    new = (month >= 7).astype(int)
    acuity = rng.choice([1, 2, 3, 4, 5], n, p=[0.05, 0.2, 0.4, 0.25, 0.1])
    site = rng.choice(["North", "Central", "South"], n, p=[0.4, 0.35, 0.25])
    age = np.clip(rng.normal(52, 20, n).round(), 0, 99)
    logm = (np.log(95) - 0.015 * (month - 1) - 0.10 * new + 0.12 * (acuity - 3)
            + np.where(site == "South", 0.15, 0.0) + rng.normal(0, 0.45, n))
    minutes = np.round(np.exp(logm)).astype(int)
    df = pd.DataFrame({
        "visit_id": [f"V{100000 + i}" for i in range(n)],
        "mrn": [f"MRN-{rng.integers(1000000, 9999999)}" for _ in range(n)],
        "patient_name": names(n),
        "age": age.astype(int),
        "sex": rng.choice(["F", "M"], n),
        "site": site,
        "arrival_month": [f"2025-{m:02d}" for m in month],
        "acuity": acuity,
        "protocol": np.where(new == 1, "new", "old"),
        "minutes_to_diagnosis": minutes,
        "admitted": rng.binomial(1, 0.12 + 0.05 * (acuity <= 2)),
    })
    miss = rng.random(n) < 0.03
    df.loc[miss, "minutes_to_diagnosis"] = 999
    ok = df[~miss].assign(m=lambda x: x.arrival_month.str[-2:].astype(int), new=lambda x: (x.protocol == "new").astype(int))
    naive = smf.ols("np.log(minutes_to_diagnosis) ~ new", ok).fit(cov_type="HC1")
    adj = smf.ols("np.log(minutes_to_diagnosis) ~ new + m + C(acuity) + C(site)", ok).fit(cov_type="HC1")
    df.to_csv(OUT / "clinic_triage.csv", index=False)
    request = {
        "question": "Did the new triage protocol reduce the time to diagnosis in our clinics?",
        "llm": "nebius",
        "decision_rule": {"metric": "effect of the new protocol on minutes to diagnosis",
                          "comparator": "lt", "threshold": 0, "alpha": 0.05,
                          "positive_label": "PROTOCOL SPEEDS DIAGNOSIS", "negative_label": "NO CLEAR EFFECT"},
        "column_notes": {"minutes_to_diagnosis": "minutes from arrival to a confirmed diagnosis; 999 means the time was not recorded",
                         "protocol": "the new triage protocol replaced the old one at all three sites in July 2025",
                         "acuity": "triage level, 1 = most urgent, 5 = least urgent"},
    }
    truth = {"planted_log_effect": -0.10, "naive_log": [naive.params["new"], naive.pvalues["new"]],
             "adjusted_log": [adj.params["new"], adj.pvalues["new"]],
             "trap": "before/after with a -1.5%/month staffing trend; 999 sentinel; skewed minutes"}
    return "clinic_triage", "clinic_triage.csv", request, truth


def k12():
    n = 3000
    school = rng.integers(0, 24, n)
    s_eff = rng.normal(0, 4, 24)[school]
    frl = rng.binomial(1, 0.45, n)
    ell = rng.binomial(1, 0.15, n)
    ability = rng.normal(0, 1, n) - 0.3 * frl
    prior = np.clip(60 + 12 * ability + s_eff + rng.normal(0, 6, n), 0, 100).round(1)
    tutor = (prior < np.percentile(prior, 35)).astype(int)
    tutor = np.where(rng.random(n) < 0.15, 1 - tutor, tutor)
    post = np.clip(60 + 12 * ability + s_eff + 3.0 * tutor + rng.normal(0, 6, n), 0, 100).round(1)
    df = pd.DataFrame({
        "student_id": [f"S{200000 + i}" for i in range(n)],
        "student_name": names(n),
        "school": [f"School {chr(65 + s // 2)}{s % 2 + 1}" for s in school],
        "grade": rng.choice([6, 7, 8], n),
        "frl": frl, "ell": ell, "iep": rng.binomial(1, 0.12, n),
        "prior_math_score": prior,
        "tutoring": tutor,
        "post_math_score": post,
        "attendance_rate": np.clip(rng.normal(0.93, 0.05, n), 0.5, 1).round(3),
    })
    drop = rng.random(n) < 0.06
    df.loc[drop, "post_math_score"] = np.nan
    ok = df.dropna()
    naive = smf.ols("post_math_score ~ tutoring", ok).fit(cov_type="HC1")
    gain = smf.ols("I(post_math_score - prior_math_score) ~ tutoring", ok).fit(cov_type="HC1")
    adj = smf.ols("post_math_score ~ tutoring + prior_math_score + frl + ell", ok).fit(
        cov_type="cluster", cov_kwds={"groups": ok.school.astype("category").cat.codes})
    df.to_csv(OUT / "k12_tutoring.csv", index=False)
    request = {
        "question": "¿El programa de tutorías de matemáticas mejoró las notas de los estudiantes?",
        "llm": "nebius",
        "decision_rule": {"metric": "efecto de tutoring sobre post_math_score, en puntos",
                          "comparator": "gt", "threshold": 0, "alpha": 0.05,
                          "positive_label": "LAS TUTORÍAS FUNCIONAN", "negative_label": "SIN EFECTO CLARO"},
        "column_notes": {"tutoring": "1 = el estudiante recibió tutorías; se ofrecieron sobre todo a quienes tenían nota previa baja",
                         "prior_math_score": "nota de matemáticas del curso anterior (0-100)",
                         "post_math_score": "nota de matemáticas a final de curso (0-100); vacía si el estudiante se fue del distrito",
                         "frl": "1 = comedor gratuito o reducido"},
    }
    truth = {"planted_effect": 3.0, "naive_post": [naive.params["tutoring"], naive.pvalues["tutoring"]],
             "naive_gain": [gain.params["tutoring"], gain.pvalues["tutoring"]],
             "ancova_cluster": [adj.params["tutoring"], adj.pvalues["tutoring"]],
             "trap": "selection on low prior score: post-only comparison is negative; gain score inflated by regression to the mean; 24 school clusters; minors' names"}
    return "k12_tutoring", "k12_tutoring.csv", request, truth


def bank():
    n = 6000
    female = rng.binomial(1, 0.48, n)
    income = np.round(np.exp(rng.normal(np.log(2300) - 0.18 * female, 0.45, n)), 2)
    score = np.clip(rng.normal(680, 70, n), 350, 850).round()
    dti = np.clip(rng.normal(0.32, 0.12, n), 0.02, 0.9).round(3)
    z = -9.0 + 0.012 * score + 0.9 * np.log(income / 2300) - 3.0 * dti + 0.75
    approved = rng.binomial(1, 1 / (1 + np.exp(-z)))
    nm = names(n)
    df = pd.DataFrame({
        "solicitud_id": [f"SOL-{300000 + i}" for i in range(n)],
        "nombre": nm,
        "iban": [f"ES{rng.integers(10, 99)} 2100 {rng.integers(1000, 9999)} {rng.integers(10, 99)} {rng.integers(10**9, 10**10 - 1)}" for _ in range(n)],
        "email": [x.lower().replace(" ", ".") + "@correo.example" for x in nm],
        "edad": rng.integers(21, 70, n),
        "sexo": np.where(female == 1, "M", "H"),
        "ingresos_mensuales": income,
        "puntuacion_credito": score.astype(int),
        "ratio_deuda": dti,
        "provincia": rng.choice(["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao", "Malaga"], n),
        "importe_solicitado": np.round(rng.uniform(3000, 30000, n), -2),
        "aprobado": approved,
    })
    naive = smf.ols("aprobado ~ I(sexo == 'M')", df).fit(cov_type="HC1")
    adj = smf.ols("aprobado ~ I(sexo == 'M') + puntuacion_credito + np.log(ingresos_mensuales) + ratio_deuda", df).fit(cov_type="HC1")
    k = "I(sexo == 'M')[T.True]"
    out = df.copy()
    for c in ["ingresos_mensuales", "ratio_deuda"]:
        out[c] = out[c].map(lambda v: f"{v}".replace(".", ","))
    out.to_csv(OUT / "banco_solicitudes.csv", index=False, sep=";")
    request = {
        "question": "¿Aprobamos menos préstamos a mujeres que a hombres con el mismo perfil de riesgo?",
        "llm": "nebius",
        "decision_rule": {"metric": "diferencia en la probabilidad de aprobación, mujeres menos hombres, a igual perfil de riesgo",
                          "comparator": "lt", "threshold": 0, "alpha": 0.05,
                          "positive_label": "SESGO CONTRA MUJERES", "negative_label": "SIN DIFERENCIA CLARA"},
        "column_notes": {"sexo": "M = mujer, H = hombre",
                         "aprobado": "1 = préstamo aprobado",
                         "ingresos_mensuales": "ingresos netos mensuales en euros",
                         "ratio_deuda": "deuda mensual / ingresos mensuales"},
    }
    truth = {"planted_conditional_gap": 0.0, "naive_gap": [naive.params[k], naive.pvalues[k]],
             "adjusted_gap": [adj.params[k], adj.pvalues[k]],
             "trap": "raw gap from lower incomes; semicolon CSV with decimal commas; names, IBAN and email"}
    return "bank_fair_lending", "banco_solicitudes.csv", request, truth


if __name__ == "__main__":
    index = {}
    for make in (audit, clinic, k12, bank):
        name, file, request, truth = make()
        (OUT / f"{name}.request.json").write_text(json.dumps(request, ensure_ascii=False, indent=1))
        index[name] = {"file": file, "truth": truth}
        print(name, json.dumps(truth, default=float)[:300])
    (OUT / "truth.json").write_text(json.dumps(index, default=float, indent=1, ensure_ascii=False))
