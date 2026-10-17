export function AiProcessingNotice({ records = false }: { records?: boolean }) {
  return (
    <p className="text-xs leading-5 text-slate-600">
      {records
        ? "When an external AI provider is configured, this request sends it identity-reduced medical record details. Free-text notes may still contain sensitive information."
        : "When an external AI provider is configured, your question is sent to it. Do not include names, contact details, or other identifying information."}
      {" "}Responses are informational, may be inaccurate, and do not replace a clinician.
    </p>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  VISITS: "Clinical visits",
  PRESCRIPTIONS: "Prescriptions",
  LAB_REPORTS: "Diagnostic reports",
  DIAGNOSTIC_REPORTS: "Diagnostic reports",
  EMERGENCY_PROFILE: "Emergency health profile",
  DEMOGRAPHICS: "Basic health information",
  PROFILE: "Basic health information",
};

export function sourceCategoryLabels(categories: string[]) {
  return categories.map((category) => SOURCE_LABELS[category] ?? "HealthLink record").join(", ");
}
