from __future__ import annotations


def recode_instruction(errors: list[str]) -> str:
    listed = "\n".join(f"- {error}" for error in errors)
    return (
        "Every earlier version of this option's code failed its smoke run. The errors seen so "
        f"far, oldest first:\n{listed}\n"
        "Do not patch earlier code: write new code from the spec, in a different way if the "
        "errors point at your approach."
    )
