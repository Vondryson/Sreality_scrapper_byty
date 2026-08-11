const missing = "Neuvedeno";
const integer = new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 1 });
const currency = new Intl.NumberFormat("cs-CZ", {
  style: "currency",
  currency: "CZK",
  maximumFractionDigits: 0,
});
const date = new Intl.DateTimeFormat("cs-CZ", {
  dateStyle: "medium",
  timeZone: "Europe/Prague",
});
const dateTime = new Intl.DateTimeFormat("cs-CZ", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Prague",
});

export const formatPrice = (value: number | null) => (value === null ? missing : currency.format(value));
export const formatArea = (value: number | null) => (value === null ? missing : `${integer.format(value)} m²`);
export const formatDistance = (value: number | null) =>
  value === null ? missing : `${decimal.format(value)} km`;
export const formatDuration = (minutes: number | null) => {
  if (minutes === null) return missing;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours === 0 ? `${remainder} min` : `${hours} h ${remainder} min`;
};
export const formatDate = (value: string | Date | null) =>
  value === null ? missing : date.format(new Date(value));
export const formatDateTime = (value: string | Date | null) =>
  value === null ? missing : dateTime.format(new Date(value));
export const formatCount = (value: number) => integer.format(value);
export { missing as missingValueLabel };
