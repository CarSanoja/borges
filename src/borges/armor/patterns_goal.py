from __future__ import annotations

OUTCOME = r"(?:ship|don'?t ship|do not ship|positive label|negative label|significant(?!\s+(?:digits|figures))|not significant|flip|no flip|no clear evidence|bias detected|depends on norms|cap the calls|no case for a cap|significativ[oa]s?)"
VERB = r"(?:report|state|say|write|output|return|conclude|declare|claim|answer|respond|recommend|decide|reporta|reportar|concluye|concluir|responde|afirma|declara|recomienda|escribe|di)"

STEERING = (
    (
        "steering.p_value",
        rf"\b{VERB}\b(?:\W+\w+){{0,3}}?\W+(?:p(?:[- _]?value)?|valor[- ]p)\s*(?:<|<=|=|==|es|is|of|de|menor)\s*(?:que\s+)?0?[.,]\d+",
    ),
    (
        "steering.set_p",
        r"\b(?:set|make|force|fija|haz|forzar?)\s+(?:the\s+|el\s+)?(?:p[- _]?value|valor[- ]p|estimate|estimado|ci|interval)\b.{0,20}\b(?:to|=|a|en)\b",
    ),
    (
        "steering.always",
        rf"\b(?:always|must|should|just|siempre|debes|tienes que)\s+(?:conclude|report|answer|return|say|output|recommend|decide|declare|concluye|reporta|responde|recomienda|declara)\b(?:\W+\w+){{0,3}}?\W+{OUTCOME}",
    ),
    (
        "steering.report_label",
        rf"\b{VERB}\b\W+(?:(?:that|the|decision|result|as|is|que|la|el|decision|resultado)\W+){{0,4}}[\"']?{OUTCOME}\b",
    ),
    (
        "steering.the_flip",
        r"\bthe\s+(?:minimal\s+|smallest\s+)?flip\s+(?:is|was|=)\b|\bel\s+(?:flip|cambio\s+minimo)\s+es\b",
    ),
    (
        "steering.result_must",
        r"\b(?:result|results|estimate|effect|analysis|resultado|efecto|analisis)\s+(?:is|are|must\s+be|should\s+be|es|son|debe\s+ser)\s+(?:always\s+)?(?:significant|robust|significativ[oa]s?|robust[oa])\b",
    ),
    (
        "steering.no_flip",
        r"\b(?:never|do\s+not|don'?t|nunca|no)\s+(?:report|find|propose|accept|reporte|encuentres?|propongas?|aceptes?)\s+(?:a\s+|any\s+|ningun\s+|un\s+)?(?:flip|alternative|cambio|alternativa)\b",
    ),
    (
        "steering.hardcode",
        r"\bhard[- ]?cod\w*\b.{0,30}\b(?:result|estimate|p[- _]?value|ci|output|resultado|estimado)\b",
    ),
    (
        "steering.reject_all",
        r"\b(?:reject|accept|approve|rechaza|acepta|aprueba)\s+(?:all|every|everything|todas?|todo)\b",
    ),
    (
        "steering.score",
        r"\b(?:give|assign|set|rate|da|asigna|pon)\b.{0,25}\bdefensibility\b.{0,15}\b(?:1(?:\.0)?|0?[.,]9\d*|max\w*)\b",
    ),
)

SENSITIVE = (
    r"(?:environment(?:\s+variables?)?|env(?:ironment)?\s+vars?|\.env\b|secrets?|api[ _-]?keys?|"
    r"(?:access|auth|api|bearer)\s+tokens?|credentials?|passwords?|passwd|system\s+prompt|"
    r"hidden\s+prompt|your\s+(?:instructions|rules|prompt)|private\s+keys?|ssh\s+keys?|"
    r"(?:variables?\s+de\s+)?entorno|claves?|contrasenas?|credenciales|"
    r"tus\s+(?:instrucciones|reglas)|prompt\s+del\s+sistema)"
)
LEAK_VERB = r"(?:print|show|dump|reveal|display|echo|leak|list|read|cat|send|post|upload|exfiltrate|forward|write|repeat|tell|imprime|muestra|revela|lee|envia|manda|sube|escribe|repite|dime)"

EXFIL = (
    (
        "exfil.leak",
        rf"\b{LEAK_VERB}\b(?:\W+\w+){{0,4}}?\W+(?:the\s+|your\s+|all\s+|el\s+|la\s+|las\s+|los\s+|tu\s+)?{SENSITIVE}",
    ),
    (
        "exfil.env_file",
        r"(?:\.env\b|\bos\.environ|\bgetenv\b|/etc/passwd|/etc/shadow|~/\.ssh|\bid_rsa\b|\.aws/credentials)",
    ),
    (
        "exfil.send_url",
        r"\b(?:send|post|upload|forward|curl|wget|exfiltrat\w*|fetch|envia|manda|sube)\b.{0,50}\b(?:https?://|ftp://|www\.)",
    ),
    ("exfil.to_url", r"\b(?:to|a)\s+https?://\S+"),
    (
        "exfil.reveal_prompt",
        r"\b(?:reveal|show|print|repeat|tell\s+me|revela|muestrame|repite)\b.{0,30}\b(?:system\s+prompt|your\s+instructions|your\s+rules|initial\s+prompt|hidden\s+prompt|prompt\s+del\s+sistema|tus\s+instrucciones)\b",
    ),
    ("exfil.dns", r"\b(?:nslookup|dig|ping)\s+\S+\.\S+|\bcurl\s+-|\bwget\s+"),
)
