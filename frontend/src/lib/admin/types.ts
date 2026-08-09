import type { AccessTokenResponse } from "@/lib/auth/types";

export type AdminLoginRequest = {
  email: string;
  password: string;
};

export type AdminLoginResponse = AccessTokenResponse & {
  portal: "ADMIN";
};

export type AdminMe = {
  user_id: string;
  admin_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_super_admin: boolean;
};
