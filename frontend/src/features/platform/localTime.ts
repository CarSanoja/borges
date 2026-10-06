export type Stamp = number | string | null | undefined;

export function toDate(value: Stamp): Date | null {
  if (value === null || value === undefined || value === "") return null;
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

const two = (n: number): string => String(n).padStart(2, "0");

export function localDate(value: Stamp): string | null {
  const date = toDate(value);
  if (!date) return null;
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`;
}

export function localDateTime(value: Stamp): string | null {
  const date = toDate(value);
  if (!date) return null;
  const clock = `${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`;
  const zone = new Intl.DateTimeFormat(undefined, { timeZoneName: "short" })
    .formatToParts(date)
    .find((part) => part.type === "timeZoneName")?.value;
  return `${localDate(value)} ${clock}${zone ? ` ${zone}` : ""}`;
}
