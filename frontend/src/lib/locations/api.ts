"use client";

import { apiClient } from "@/lib/api/client";
import type { BangladeshAreaOptions } from "./types";

export async function loadBangladeshAreas(): Promise<BangladeshAreaOptions> {
  return apiClient.get<BangladeshAreaOptions>("locations/bangladesh", { auth: false });
}
