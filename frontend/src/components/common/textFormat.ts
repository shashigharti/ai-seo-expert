/** Turns an agent/capability identifier into a consistent, readable label -
 * the one shared convention for "machine name" -> "display name" used by
 * both the Findings panel (grouping by `agent_name`, e.g. "TechnicalSEOAgent")
 * and the SEO/GitHub PR Agent Execution panels (`agent_name` once known,
 * `capability` as a snake_case fallback before it is, e.g. "technical_seo").
 * Both inputs collapse to the same output ("Technical Seo") so a given
 * agent reads identically everywhere it appears.
 *
 * "Technical Seo", not "Technical SEO" - deliberately title-cased rather
 * than acronym-preserving, so the rule stays a single, simple "first letter
 * of each word" convention instead of needing an acronym dictionary.
 */
export function humanizeAgentLabel(raw: string): string {
  const withoutAgentSuffix = raw.replace(/Agent$/, "");
  const spaced = withoutAgentSuffix
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");

  return spaced
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}
