import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  getBlob: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: apiMocks,
}));

import {
  createPrescription,
  downloadPrescriptionPdf,
  readPrescription,
  updatePrescription,
} from "./api";

const payload = {
  items: [
    {
      medicine_name: "Paracetamol",
      dosage: "500 mg",
      frequency: "1+0+1",
      duration: "5 days",
      instructions: "After meals",
    },
  ],
  diagnostic_information: "Viral fever",
  medical_advice: "Rest",
  notes: null,
};

describe("prescriptions API", () => {
  beforeEach(() => {
    Object.values(apiMocks).forEach((mock) => mock.mockReset());
  });

  it("uses the canonical create, read, and update routes", async () => {
    apiMocks.post.mockResolvedValue({ id: "rx-1" });
    apiMocks.get.mockResolvedValue({ id: "rx-1" });
    apiMocks.put.mockResolvedValue({ id: "rx-1" });

    await createPrescription("visit-1", payload);
    await readPrescription("rx-1");
    await updatePrescription("rx-1", payload);

    expect(apiMocks.post).toHaveBeenCalledWith(
      "visits/visit-1/prescription",
      payload,
    );
    expect(apiMocks.get).toHaveBeenCalledWith("prescriptions/rx-1");
    expect(apiMocks.put).toHaveBeenCalledWith("prescriptions/rx-1", payload);
  });

  it("downloads the protected PDF through the authenticated API client", async () => {
    const pdf = new Blob(["%PDF"], { type: "application/pdf" });
    apiMocks.getBlob.mockResolvedValue(pdf);

    await expect(downloadPrescriptionPdf("rx-1")).resolves.toBe(pdf);
    expect(apiMocks.getBlob).toHaveBeenCalledWith("prescriptions/rx-1/pdf");
  });
});
