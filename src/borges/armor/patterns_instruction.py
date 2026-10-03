from __future__ import annotations

FILLER = r"(?:\W+\w+){0,4}?\W+"

OVERRIDE_VERBS = (
    r"(?:ignor(?:e|es|ing|a|ar|en)|disregard|forget|override|overrule|bypass|skip|drop|"
    r"discard|neglect|olvida(?:r)?|descarta(?:r)?|omite|omitir|anula(?:r)?|salta(?:te|r)?|"
    r"desestima(?:r)?|deja de seguir|stop following|do not follow|don'?t follow|no sigas|"
    r"no apliques|no sigan|"
    r"ignorez|oubliez|oublie|ne tenez pas compte|ne tiens pas compte|passez outre|"
    r"faites abstraction|desactivez|contournez|"
    r"ignoriere|ignorieren|ignorieren sie|vergiss|vergessen sie|missachte|missachten sie|"
    r"uebergehe|umgehe|umgehen sie|"
    r"esqueca|esquecer|desconsidere|desconsidera|descarte|ignore|"
    r"ignora|ignorare|dimentica|dimenticare|trascura|scarta|aggira|"
    r"disregard(?:s|ing|ed)?|overrid(?:e|es|ing)|set aside)"
)
RULE_NOUNS = (
    r"(?:instructions?|rules?|prompts?|guidelines?|constraints?|directives?|decision[ -]?rules?|"
    r"criteria|safeguards?|filters?|guardrails?|restrictions?|instrucciones|reglas?|"
    r"regla de decision|restricciones|indicaciones|directrices|criterios|salvaguardas?|"
    r"filtros?|politicas?|rubrics?|"
    r"consignes|regles|contraintes|garde-fous|"
    r"anweisungen|regeln|vorgaben|richtlinien|instruktionen|kriterien|beschraenkungen|"
    r"instrucoes|regras|diretrizes|orientacoes|restricoes|"
    r"istruzioni|regole|direttive|criteri|vincoli|indicazioni)"
)

OVERRIDE = (
    ("override.ignore_rules", rf"\b{OVERRIDE_VERBS}\b{FILLER}{RULE_NOUNS}\b"),
    (
        "override.previous",
        r"\b(?:ignor\w+|disregard|forget|olvida\w*|oubli\w+|vergiss\w*|esqueca\w*|dimentica\w*)\b.{0,30}\b(?:previous|prior|above|earlier|anterior\w*|previas?|precedent\w*|vorherig\w*|fruher\w*|zuvor|anteriori)\b",
    ),
    (
        "override.new_instructions",
        r"\b(?:new|updated|revised|real|actual|nuevas?|nuevos?)\s+(?:instructions?|rules?|orders?|instrucciones|reglas|ordenes)\s*[:\-]",
    ),
    (
        "override.instead",
        r"\binstead,?\s+(?:you\s+(?:must|should|will)|do\s+not|report|conclude|always|answer)\b",
    ),
    (
        "override.en_lugar",
        r"\ben lugar de eso,?\s+(?:debes|tienes que|reporta|concluye|responde)\b",
    ),
    (
        "override.not_apply",
        r"\b(?:rules?|guidelines?|instructions?|reglas|instrucciones)\s+(?:do(?:es)?\s+not|don'?t|no)\s+(?:apply|aplican?|valen)\b",
    ),
    (
        "override.reset",
        r"\b(?:reset|wipe|clear|borra(?:r)?|reinicia(?:r)?)\s+(?:your|all|tus|todas?)\s+(?:instructions?|memory|context|rules|instrucciones|memoria|contexto|reglas)\b",
    ),
)

OVERRIDE = (
    *OVERRIDE,
    (
        "override.delimiter",
        r"(?:end of (?:the )?(?:data|input|document|dataset|context|prompt|notes?)|#{2,}\s*end\b)\W{1,12}(?:new|next|real|actual)\s+(?:task|instructions?|prompt|objective|assignment)\b",
    ),
    (
        "override.obey",
        r"\b(?:translate|translation)\b.{0,60}\b(?:then|and)\s+(?:obey|follow|execute|apply|comply)\b|\b(?:obey|execute|comply\s+with)\s+(?:the\s+)?(?:following|these|this)\s+(?:instructions?|commands?|orders?)\b",
    ),
    (
        "override.ignore_idiom",
        r"\b(?:haz|hacer|hagas|hazle)\s+caso\s+omiso\b|\b(?:pasa|pasar|pases)\s+por\s+alto\b|\bno\s+(?:tengas|tomes|tengan)\s+en\s+(?:cuenta|consideracion)\b|\bturn\s+a\s+blind\s+eye\b",
    ),
    (
        "override.void",
        r"\btreat\b.{0,40}\b(?:earlier|previous|prior|above|original)\b.{0,40}\b(?:void|null|invalid|irrelevant|obsolete|superseded)\b|\b(?:set|put)\s+aside\b.{0,40}\b(?:you\s+were\s+told|you(?:'ve| have)\s+been\s+told|everything|rules|instructions|methodology|guidelines)\b",
    ),
)

ROLE = (
    (
        "role.system_note",
        r"\b(?:system|developer|admin(?:istrator)?|operator|sistema|desarrollador|administrador|operador)\s+(?:note|message|prompt|override|instruction|instructions|notice|update|mensaje|nota|aviso|instruccion|instrucciones|actualizacion)\b",
    ),
    (
        "role.header",
        r"(?:^|\n)\s*(?:system|assistant|developer|sistema|asistente|desarrollador)\s*:",
    ),
    ("role.bracket", r"[\[<]\s*/?\s*(?:system|sistema|inst|admin|assistant)\s*[\]>]"),
    ("role.chat_tokens", r"<\|?\s*(?:im_start|im_end|system|endoftext)\s*\|?>"),
    (
        "role.you_are_now",
        r"\b(?:you\s+are\s+now|from\s+now\s+on,?\s+you|ahora\s+eres|a\s+partir\s+de\s+ahora\s+eres|desde\s+ahora\s+eres)\b",
    ),
    (
        "role.act_as",
        r"\b(?:act\s+as\s+(?:a|an|the|if|my)|pretend\s+(?:to\s+be|you\s+are)|roleplay\s+as|take\s+on\s+the\s+role|behave\s+as\s+if|actua\s+como\s+(?:un|una|el|la|si)|comportate\s+como|finge\s+ser|asume\s+el\s+rol)\b",
    ),
    (
        "role.mode",
        r"\b(?:developer|debug|admin|god|jailbreak|dan)\s+mode\b|\bmodo\s+(?:desarrollador|depuracion|administrador|dios)\b",
    ),
    (
        "role.authority",
        r"\b(?:i\s+am\s+(?:the|your)\s+(?:admin\w*|developer|owner|engineer|operator)|soy\s+(?:el|tu)\s+(?:administrador|desarrollador|dueno|operador|ingeniero)|this\s+is\s+(?:the\s+)?(?:engineering|security)\s+team)\b",
    ),
    (
        "role.disable_safety",
        r"\b(?:disable|turn\s+off|deactivate|desactiva(?:r)?|apaga(?:r)?)\s+(?:the\s+|your\s+|tus?\s+|el\s+|la\s+)?(?:safety|guardrails?|filters?|armor|checks?|verification|seguridad|filtros?|verificacion|controles)\b",
    ),
)

STRICT_OVERRIDE_VERBS = (
    r"(?:ignor(?:e|es|ing|a|ar|en)|disregard(?:s|ing|ed)?|forget|overrid(?:e|es|ing)|overrule|"
    r"bypass|olvida(?:r)?|desestima(?:r)?|deja de seguir|stop following|do not follow|"
    r"don'?t follow|no sigas|no apliques|no sigan|ignorez|oubliez|oublie|ne tenez pas compte|"
    r"ne tiens pas compte|passez outre|contournez|ignoriere|ignorieren|vergiss|vergessen sie|"
    r"missachte|missachten sie|umgehe|umgehen sie|esqueca|esquecer|desconsidere|desconsidera|"
    r"ignorare|dimentica|dimenticare|aggira|set aside)"
)

COMPOSED_OVERRIDE = (
    ("override.ignore_rules", rf"\b{STRICT_OVERRIDE_VERBS}\b{FILLER}{RULE_NOUNS}\b"),
    *(entry for entry in OVERRIDE if entry[0] != "override.ignore_rules"),
)
