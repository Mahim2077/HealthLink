export type RecordsUsed = Record<string, number>;

export type PrescriptionExplanation = {
  plain_language_summary: string;
  medicine_explanations: Array<{
    medicine_name: string;
    purpose_or_role: string;
    recorded_instructions: string;
    general_education?: string | null;
  }>;
  questions_to_ask_clinician: string[];
  disclaimer: string;
};

export type LabReportExplanation = {
  summary: string;
  parameter_explanations: Array<{
    parameter: string;
    result: string;
    unit: string | null;
    reference_range: string | null;
    flag: string | null;
    explanation: string;
  }>;
  flagged_results: Array<{
    parameter: string;
    result: string;
    unit: string | null;
    reference_range: string | null;
    flag: string;
  }>;
  questions_for_clinician: string[];
  disclaimer: string;
};

export type MedicalHistorySummary = {
  summary: string;
  record_observations: Array<{ statement: string; source_categories: string[] }>;
  questions_for_clinician: string[];
  disclaimer: string;
  records_used: RecordsUsed;
};

export type ChatMode = "GENERAL" | "RECORD_AWARE";

export type AiChatResponse = {
  answer: string;
  record_observations: Array<{
    statement: string;
    source_categories: string[];
  }>;
  questions_for_clinician: string[];
  disclaimer: string;
  records_used: RecordsUsed;
};

export type SymptomGuidance = {
  symptom_summary: string;
  general_information: string[];
  red_flags: string[];
  suggested_next_step: string;
  urgency_category: string;
  disclaimer: string;
};
