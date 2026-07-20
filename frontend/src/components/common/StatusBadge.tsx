interface StatusBadgeProps<T extends string> {
  status: T;
  classMap: Record<T, string>;
  label?: string;
}

/** Generic status badge - pass a class map from statusMaps.ts and it
 * renders consistently everywhere in the app. */
export function StatusBadge<T extends string>({ status, classMap, label }: StatusBadgeProps<T>) {
  return <span className={`badge ${classMap[status]}`}>{label ?? status}</span>;
}
