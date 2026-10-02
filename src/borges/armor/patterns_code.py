from __future__ import annotations

MODULES = r"(?:os|sys|subprocess|socket|shutil|requests|urllib\w*|http\w*|ctypes|pathlib|builtins|importlib|pty|pickle|marshal|multiprocessing|threading|signal|resource|glob|tempfile|ftplib|smtplib)"

CODE = (
    ("code.import", rf"\b(?:import|from)\s+{MODULES}\b"),
    (
        "code.subprocess",
        r"\bsubprocess\b|\bos\.(?:system|popen|exec\w*|spawn\w*|environ|getenv|listdir|remove|unlink|walk)\b",
    ),
    ("code.dynamic", r"\b(?:eval|exec|__import__)\s*\("),
    ("code.open_abs", r"\bopen\s*\(\s*[rbuf]*[\"']\s*(?:/|\.\./|~|[a-z]:\\)"),
    ("code.dunder", r"__(?:builtins|class|subclasses|globals|bases|mro|loader|dict)__"),
    ("code.network", r"\b(?:socket\.|requests\.(?:get|post|put)|urllib\.request|http\.client)"),
    ("code.shell_words", r"\b(?:rm\s+-rf|chmod\s+\d{3}|/bin/(?:ba)?sh|powershell|cmd\.exe)\b"),
)

CODE_STEERING = (
    (
        "steering.fabricate",
        r"\b(?:fabricate|make\s+up|invent|fake|forge|falsif\w+|fabrica|inventa|falsea)\b.{0,30}\b(?:result|estimate|p[- _]?value|data|numbers?|resultado|estimado|datos|numeros)\b",
    ),
    (
        "steering.skip_fit",
        r"\b(?:skip|do\s+not\s+run|don'?t\s+run|omit|omite|no\s+ejecutes)\b.{0,25}\b(?:the\s+)?(?:test|fit|model|regression|estimation|prueba|modelo|regresion|estimacion)\b",
    ),
    (
        "steering.constant",
        r"\breturn\s+(?:a\s+)?(?:fixed|constant|preset|hard[- ]?coded|fijo|constante)\s+(?:result|estimate|value|resultado|valor)\b",
    ),
    (
        "steering.write_result",
        r"\b(?:write|set|assign)\s+(?:the\s+)?(?:estimate|p[_ -]?value|ci_low|ci_high)\s*(?:=|to)\b",
    ),
    ("steering.ctx_overwrite", r"\bctx\s*\[[^\]]*\]\s*=\s*(?:\d|[\"']ship)"),
)
