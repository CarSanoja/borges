import type {
  Option,
  RunSnapshot,
  Step,
  UniverseDetail,
  UniverseStepDetail,
} from "../../shared/types/contracts";

function pickOption(step: Step, optionId: string | undefined): Option | null {
  const chosen = step.options.find((option) => option.id === optionId);
  return chosen ?? step.options.find((option) => option.is_default) ?? step.options[0] ?? null;
}

export function reproduceCommandFor(snapshot: RunSnapshot, universeId: string, runId: string | null): string {
  const flip = snapshot.flip;
  if (flip && flip.universe_id === universeId && flip.reproduce_command) return flip.reproduce_command;
  return `borges reproduce --run ${runId ?? snapshot.run_id} --universe ${universeId}`;
}

export function deriveDetail(
  snapshot: RunSnapshot,
  universeId: string,
  runId: string | null = null,
): UniverseDetail | null {
  const universe = snapshot.garden.universes[universeId];
  const plan = snapshot.plan;
  if (!universe || !plan) return null;

  const steps: UniverseStepDetail[] = [];
  plan.steps.forEach((step, index) => {
    const option = pickOption(step, universe.choices[step.id]);
    if (!option) return;
    const node = snapshot.checkpoints.find(
      (checkpoint) => checkpoint.step_id === step.id && checkpoint.option_id === option.id,
    );
    steps.push({
      step,
      option,
      trace: universe.traces.find((trace) => trace.step_id === step.id) ?? null,
      changed: universe.changed.includes(step.id) || !option.is_default,
      checkpoint_id: universe.checkpoints[index] ?? node?.checkpoint_id ?? null,
    });
  });

  return { universe, steps, reproduce_command: reproduceCommandFor(snapshot, universeId, runId) };
}
