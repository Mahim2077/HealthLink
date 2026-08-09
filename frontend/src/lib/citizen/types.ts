import type { AccessTokenResponse } from "@/lib/auth/types";

export type CitizenIdentityKind = "NID" | "BCN";

type CitizenRegistrationBaseRequest = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  blood_group?: string | null;
  address?: string | null;
};

export type CitizenRegistrationRequest = CitizenRegistrationBaseRequest &
  (
    | {
        nid_number: string;
        birth_certificate_number?: never;
      }
    | {
        birth_certificate_number: string;
        nid_number?: never;
      }
  );

export type CitizenRegistrationResponse = {
  user_id: string;
  citizen_id: string;
  email: string;
  first_name: string;
  last_name: string;
  registered_with: CitizenIdentityKind;
  created_at: string;
};

export type CitizenLoginRequest = {
  email: string;
  password: string;
};

export type CitizenLoginResponse = AccessTokenResponse & {
  portal: "CITIZEN";
};

export type CitizenProfile = {
  user_id: string;
  citizen_id: string;
  email: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  blood_group: string | null;
  address: string | null;
  created_at: string;
  updated_at: string;
};

export type CitizenIdentity = {
  registered_with: CitizenIdentityKind;
  nid_number: string | null;
  birth_certificate_number: string | null;
  nid_added_at: string | null;
};

export type CitizenDashboardData = {
  profile: CitizenProfile;
  identity: CitizenIdentity;
};

export type CitizenProfileUpdateRequest = Pick<
  CitizenProfile,
  | "first_name"
  | "last_name"
  | "date_of_birth"
  | "gender"
  | "blood_group"
  | "address"
>;

export type CitizenAddNidRequest = {
  nid_number: string;
  confirmation: string;
};
