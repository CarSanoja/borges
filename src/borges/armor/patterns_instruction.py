from __future__ import annotations

FILLER = r"(?:\W+\w+){0,4}?\W+"

OVERRIDE_VERBS = (
    r"(?:ignor(?:e|es|ing|a|ar|en)|disregard|forget|override|overrule|bypass|skip|drop|"
    r"discard|neglect|olvida(?:r)?|descarta(?:r)?|omite|omitir|anula(?:r)?|salta(?:te|r)?|"
    r"desestima(?:r)?|deja de seguir|stop following|do not follow|don'?t follow|no sigas|"
    r"no apliques|no sigan)"
)
RULE_NOUNS = (
    r"(?:instructions?|rules?|prompts?|guidelines?|constraints?|directives?|decision[ -]?rules?|"
    r"criteria|safeguards?|filters?|guardrails?|restrictions?|instrucciones|reglas?|"
    r"regla de decision|restricciones|indicaciones|directrices|criterios|salvaguardas?|"
    r"filtros?|politicas?)"
)

OVERRIDE = (
    ("override.ignore_rules", rf"\b{OVERRIDE_VERBS}\b{FILLER}{RULE_NOUNS}\b"),
    (
        "override.previous",
        r"\b(?:ignor\w+|disregard|forget|olvida\w*)\b.{0,30}\b(?:previous|prior|above|earlier|anterior\w*|previas?)\b",
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
