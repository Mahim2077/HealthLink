export type MedicalHistoryResourceType = "VISIT" | "PRESCRIPTION";

export type MedicalHistoryQuery = {
  resource_type?: MedicalHistoryResourceType;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
};

export type MedicalHistoryEvent = {
  id: string;
  resource_type: MedicalHistoryResourceType;
  resource_id: string;
  occurred_at: string;
  title: string;
  subtitle: string | null;
  facility: string | null;
  professional: string | null;
  status: string;
  summary: string | null;
  appointment_id: string | null;
  serial_number: number | null;
};

export type MedicalHistoryPage = {
  items: MedicalHistoryEvent[];
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
};

export type MedicalHistoryLoadAction = (
  query?: MedicalHistoryQuery,
) => Promise<MedicalHistoryPage>;
