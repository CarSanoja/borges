"""What the report says about the check of the starting point."""

from __future__ import annotations

REPAIRED = (
    "The step-by-step code of your analysis first gave {ours}; two independent implementations "
    "of it, each written as one script, gave {theirs}. The code of {steps} was repaired ({why}) "
    "and the starting point now matches them."
)
DISAGREES = (
    "The starting point does not match your analysis as two independent implementations of it "
    "compute it: the step-by-step code gives {ours} and both implementations give {theirs}; "
    "repairing the steps did not close the gap. Read the original result with care."
)
UNRESOLVED = (
    "The starting point could not be confirmed: the step-by-step code gives {ours}, and no two "
    "independent implementations of your analysis agreed with each other ({listed})."
)
CONFIRMED_GAPS = (
    "Before the code was written, a comparison of the plan with your analysis listed {n} possible "
    "difference{s}; an independent implementation of your analysis gives the same estimate, "
    "interval and n as the starting point, so on this data {they} not change the original result."
)
UNCHECKED = (
    "The starting point was not checked against an independent implementation of your analysis, "
    "which could not be run ({error})."
)
