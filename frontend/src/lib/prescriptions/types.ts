export type PrescriptionItemPayload = {
  medicine_name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions: string | null;
};

export type PrescriptionItemView = PrescriptionItemPayload & {
  id: string;
};

export type PrescriptionPayload = {
  chief_complaint: string | null;
  clinical_notes: string | null;
  diagnosis: string | null;
  follow_up_instructions: string | null;
  items: PrescriptionItemPayload[];
  diagnostic_information: string | null;
  medical_advice: string | null;
  notes: string | null;
};

export type PrescriptionView = Omit<PrescriptionPayload, "items"> & {
  id: string;
  visit_id: string;
  citizen_id: string;
  author_doctor_role_registration_id: string;
  items: PrescriptionItemView[];
  can_edit: boolean;
  created_at: string;
  updated_at: string;
};
