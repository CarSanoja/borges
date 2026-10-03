from __future__ import annotations

AUDIENCE = r"(?:reader|readers|user|users|reviewer|stakeholders?|audience|decision[- ]makers?|lector|lectores|revisor)"
VERDICT = r"(?:significant|signific\w+|works?|wins?|is\s+better|effective|ship|positive|a\s+winner|improves?)"
PREVIOUS = r"(?:previous|prior|earlier|above|existing|original|preceding|all)"
GUIDANCE = (
    r"(?:guidance|instructions?|rules?|directions?|prompts?|guidelines?|constraints?|directives?)"
)

SEMANTIC = (
    (
        "steering.semantic.tell_audience",
        rf"\b(?:tell|inform|convince|persuade|assure|let)\s+(?:the\s+|your\s+)?{AUDIENCE}\b.{{0,60}}\b{VERDICT}\b",
    ),
    (
        "steering.semantic.treat_as_adjusted",
        r"\b(?:treat|consider|regard|take|assume)\b.{0,40}\bas\s+(?:being\s+)?already\s+(?:adjusted|corrected|controlled|validated|cleaned|significant)\b",
    ),
    (
        "steering.semantic.stakeholder_pressure",
        r"\b(?:stakeholders?|management|leadership|executives?|the\s+(?:client|boss|business)|ejecutivos?|direccion)\b.{0,50}\b(?:only\s+accepts?|only\s+wants?|only\s+want|wants?\s+to\s+see|expects?|need\s+to\s+hear|favou?rs?|prefers?|solo\s+acept\w+)\b.{0,50}\b(?:results?|outcomes?|conclusions?|answers?|resultados?)\b",
    ),
    (
        "steering.semantic.pick_the_path",
        r"\b(?:choose|pick|select|use|elige|escoge)\s+the\s+(?:specification|option|model|analysis|variant|path|branch)\s+that\s+(?:does|gives|yields|produces|supports|confirms|shows|favou?rs|delivers)\b",
    ),
    (
        "steering.semantic.assume_effect",
        rf"\b(?:just|simply|only)\s+(?:conclude|assume|say|state)\b(?:\W+\w+){{0,6}}?\W+{VERDICT}\b",
    ),
    (
        "steering.semantic.wipe_guidance",
        rf"\b(?:wipe|erase|purge|scrap|discard|void|nullify|overwrite|supersede|clear)\b(?:\W+\w+){{0,3}}?\W+{PREVIOUS}\W+(?:\w+\W+)?{GUIDANCE}\b",
    ),
    (
        "steering.semantic.dictated_answer",
        r"\b(?:the\s+)?(?:answer|conclusion|result|verdict)\s+is\s+(?:already\s+)?(?:yes|no|ship|positive|significant)\b.{0,40}\b(?:write|put|include|copy|paste|insert)\s+(?:it|that|this)\b.{0,30}\b(?:report|summary|verbatim|narrative)\b",
    ),
)
