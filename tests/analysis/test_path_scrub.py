from __future__ import annotations

from borges.analysis.path_scrub import scrub_paths


def test_site_packages_frame_is_shortened() -> None:
    text = 'File "/Users/a/proj/.venv/lib/python3.13/site-packages/pandas/x.py", line 3'
    assert scrub_paths(text) == 'File "site-packages/pandas/x.py", line 3'


def test_other_absolute_frame_keeps_the_file_name() -> None:
    assert scrub_paths('File "/home/u/work/step.py", line 2') == 'File "step.py", line 2'


def test_bare_absolute_paths_are_reduced() -> None:
    assert "/Users" not in scrub_paths("cannot open /Users/a/b/data.csv now")


def test_plain_text_is_untouched() -> None:
    assert scrub_paths("KeyError: 'nope' in column a/b") == "KeyError: 'nope' in column a/b"
