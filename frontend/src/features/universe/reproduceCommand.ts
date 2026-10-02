const RUNNER = "uv run ";

export function reproduceCommand(command: string): string {
  const trimmed = command.trim();
  return trimmed.startsWith("borges ") ? `${RUNNER}${trimmed}` : trimmed;
}
