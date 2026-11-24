import type { SlotValue } from "./types";

export const CRIME_NAMES: Record<string, string> = {
  kesehatan_farmasi: "Health and pharmacy",
  kesehatan: "Health and pharmacy",
  kesusilaan: "Sexual offence",
  korupsi: "Corruption",
  lainnya: "Other",
  lalu_lintas: "Traffic",
  narkotika: "Narcotics",
  pemalsuan: "Forgery",
  pembunuhan: "Homicide",
  pemerasan_pengancaman: "Extortion and threats",
  pemerasan: "Extortion and threats",
  penadahan: "Receiving stolen goods",
  pencurian: "Theft",
  penganiayaan: "Assault",
  penggelapan: "Embezzlement",
  penipuan: "Fraud",
  perdagangan_orang: "Human trafficking",
  perjudian: "Gambling",
  senjata: "Weapons",
  sumber_daya_alam: "Natural resources",
};

export const crimeName = (label: string | null | undefined) =>
  label ? CRIME_NAMES[label] ?? label.replaceAll("_", " ") : "Unknown";

export const SLOT_LABELS: Record<string, string> = {
  defendant_age: "Defendant age",
  prosecutor_demand_type: "Demand type",
  prosecutor_demand_months: "Prosecutor demand",
  article_charged: "Articles charged",
  victim_count: "Victims",
  victim_injury: "Victim injury",
  weapon_used: "Weapon used",
  loss_value: "Loss value",
  prior_conviction: "Prior conviction",
  confession: "Confession",
  remorse: "Remorse",
  cooperative: "Cooperative",
  aggravating_factors: "Aggravating factors",
  mitigating_factors: "Mitigating factors",
};

export const SLOT_GROUPS: { title: string; slots: string[] }[] = [
  { title: "Defendant and demand", slots: ["defendant_age", "prosecutor_demand_type", "prosecutor_demand_months", "article_charged"] },
  { title: "Victim and harm", slots: ["victim_count", "victim_injury", "weapon_used", "loss_value"] },
  { title: "Conduct in court", slots: ["prior_conviction", "confession", "remorse", "cooperative"] },
];

export const FACTOR_NAMES: Record<string, string> = {
  public_unrest: "Public unrest",
  against_gov_program: "Against government program",
  victim_loss: "Loss to the victim",
  victim_harm: "Harm to the victim",
  harm_to_youth: "Harm to young people",
  prior_conviction: "Prior conviction",
  enjoyed_proceeds: "Enjoyed the proceeds",
  evasive_or_denial: "Evasive or denial",
  no_reconciliation: "No reconciliation",
  abuse_of_position: "Abuse of position",
  use_of_violence: "Use of violence",
  premeditated: "Premeditated",
  repeated_act: "Repeated act",
  against_norms: "Against norms",
  other_aggravating: "Other aggravating",
  no_prior_conviction: "No prior conviction",
  admission: "Admission",
  remorse: "Remorse",
  polite_conduct: "Polite in court",
  cooperative: "Cooperative",
  breadwinner: "Breadwinner",
  victim_forgiveness: "Victim forgiveness",
  restitution: "Restitution",
  young_age: "Young age",
  old_age_or_health: "Old age or illness",
  caregiver: "Caregiver",
  no_proceeds_enjoyed: "No proceeds enjoyed",
  other_mitigating: "Other mitigating",
};

export const SECTION_NAMES: Record<string, string> = {
  identitas: "Identity",
  tuntutan: "Prosecutor demand",
  dakwaan: "Indictment",
  pembuktian: "Evidence",
  fakta_hukum: "Legal facts",
  pertimbangan: "Considerations",
  keadaan_memberatkan: "Aggravating",
  keadaan_meringankan: "Mitigating",
  memperhatikan: "Legal basis",
};

export const isMissing = (v: SlotValue) => v === "not_mentioned" || v === "not_applicable";

export function formatSlot(slot: string, value: SlotValue): string {
  if (value === "not_mentioned") return "Not mentioned";
  if (value === "not_applicable") return "Not applicable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (slot === "defendant_age") return `${value} years`;
  if (slot === "prosecutor_demand_months") return formatMonths(Number(value));
  if (slot === "loss_value") return `Rp ${Number(value).toLocaleString("id-ID")}`;
  if (typeof value === "string") return value.replaceAll("_", " ");
  return String(value);
}

export function formatMonths(months: number | null | undefined): string {
  if (months === null || months === undefined || Number.isNaN(months)) return "Not available";
  const m = Math.round(months * 10) / 10;
  if (m < 12) return `${m} months`;
  const years = Math.floor(m / 12);
  const rest = Math.round((m - years * 12) * 10) / 10;
  return rest ? `${years} yr ${rest} mo` : `${years} years`;
}

export const FEATURE_NAMES: Record<string, string> = {
  crime_type: "Crime type (Task 1)",
  demand_type: "Demand type",
  demand_months: "Demand in months (Task 2)",
  regex_demand_months: "Demand in months (parser)",
  demand_any: "Demand used",
  log_demand: "Log demand",
  age: "Defendant age",
  victim_count: "Victims",
  injury: "Injury level",
  weapon: "Weapon",
  log_loss: "Log loss value",
  n_aggravating: "Aggravating count",
  n_mitigating: "Mitigating count",
  n_articles: "Article count",
};

export const featureName = (f: string) => {
  if (FEATURE_NAMES[f]) return FEATURE_NAMES[f];
  if (f.startsWith("agg_")) return `Aggravating: ${FACTOR_NAMES[f.slice(4)] ?? f.slice(4)}`;
  if (f.startsWith("mit_")) return `Mitigating: ${FACTOR_NAMES[f.slice(4)] ?? f.slice(4)}`;
  if (f.startsWith("art_")) return `Article ${f.split("_").slice(2).join(" ")}`;
  return f.replaceAll("_", " ");
};
