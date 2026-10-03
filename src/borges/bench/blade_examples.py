from __future__ import annotations

CVAR_QUESTION = (
    "What is the effect of hormonal fluctuations associated with fertility on women's religiosity?"
)
CVAR_SCHEMA = (
    "ReportedCycleLength: answer to how many days long are your menstrual cycles; "
    "Relationship: relationship status; Rel1, Rel2, Rel3: religiosity items"
)
CVAR_A = {
    "1": "IV: fertility",
    "2": "IV: Answer to 'How many days long are your menstrual cycles?",
    "3": "DV: Women's religiosity",
    "4": "DV: Combination of three religious scores",
    "5": "Control: Relationship status of the individual",
    "6": "Control: Is in committed Relationship.",
    "7": "Control: In reference to `StartDateofPeriodBeforeLast`, how sure are you about it.",
}
CVAR_B = {
    "1": "Women's Reported Cycle Length",
    "2": "Relationship status of the individual",
    "3": "Women's religiosity",
    "4": "Women's fertility",
}
CVAR_RESULT = {
    "A1-B4": {
        "rationale": "Both speak about women's fertility; the first is a bit more ambiguous.",
        "similarity": 9,
    },
    "A2-B1": {"rationale": "Both speak about the length of menstrual cycles.", "similarity": 10},
    "A3-B3": {"rationale": "Both speak about how religious a woman is.", "similarity": 10},
    "A4-B3": {
        "rationale": "Both speak about religiosity; A4 explains how it is computed.",
        "similarity": 8,
    },
    "A5-B2": {"rationale": "Both speak about the relationship status.", "similarity": 10},
    "A6-B2": {"rationale": "Both speak about the relationship status.", "similarity": 10},
}

MODEL_A = {
    "1": "Linear regression",
    "2": "logistic regression",
    "3": "Two sample t-test without considering relationship",
    "4": "Linear regression with interaction effect",
    "5": "Ordinary Least Squares (OLS) Regression",
    "6": "Linear Mixed Model",
    "7": "Mixed Effects Model with Polynomial Terms",
}
MODEL_B = {
    "1": "Linear regression",
    "2": "Logistic regression",
    "3": "Two sample t-test",
    "4": "Two-way ANOVA",
    "5": "Linar Mixed-effects model",
    "6": "Polynomial Mixed-effects model",
}
MODEL_RESULT = {
    "A1-B1": {"rationale": "Both models are linear regression models."},
    "A2-B2": {"rationale": "Both models are logistic regression models."},
    "A3-B3": {"rationale": "Both models are t-tests."},
    "A4-B1": {"rationale": "Both models are linear regression models."},
    "A5-B1": {"rationale": "OLS is the same as a linear regression model."},
    "A6-B5": {"rationale": "Both models are linear mixed effects models."},
    "A7-B6": {"rationale": "Both models are polynomial mixed effects models."},
}

TRANSFORM_QUESTION = "Does income affect the risk of dying?"
TRANSFORM_SCHEMA = (
    "age: years; income: yearly income; deaths: number of deaths; height: cm; country"
)
TRANSFORM_A = {
    "1": "Convert the number of deaths to a binary indicator (df['died'] = (df['deaths'] > 0))",
    "2": "Drop rows where age is missing (df = df.dropna(subset=['age']))",
    "3": "Natural log of income (df['log_income'] = np.log(df['income']))",
    "4": "Standardize height (df['height_z'] = (df['height'] - df['height'].mean()) / sd)",
    "5": "Group by country (g = df.groupby('country'))",
}
TRANSFORM_B = {
    "1": "Filter records: remove rows with a missing age. df = df[df['age'].notna()]",
    "2": "Encode outcome: 1 if at least one death, else 0. df['any_death'] = df['deaths'] >= 1",
    "3": "Select covariates: age and income. ctx['covariates'] = ['age', 'income']",
    "4": "Filter records: keep every row. df = df.copy()",
    "5": "Derive income on the log1p scale. df['log_income'] = np.log1p(df['income'])",
}
TRANSFORM_RESULT = {
    "A1-B2": {"rationale": "Both make a 0/1 indicator of at least one death.", "similarity": 10},
    "A2-B1": {"rationale": "Both remove the rows with a missing age.", "similarity": 10},
    "A3-B5": {
        "rationale": "Both log-transform income; log1p differs slightly from log.",
        "similarity": 8,
    },
}
