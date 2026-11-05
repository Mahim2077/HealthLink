import { expect, it } from "vitest";
import { citizenHistoryPath, citizenPrescriptionBackPath, historyQueryFromSearch } from "./navigation";

it("round-trips only supported history filters and page", () => {
  const query = historyQueryFromSearch(new URLSearchParams("resource_type=PRESCRIPTION&date_from=2026-10-01&date_to=2026-10-24&page=3&unexpected=private"));
  expect(query).toEqual({ resource_type: "PRESCRIPTION", date_from: "2026-10-01", date_to: "2026-10-24", page: 3, page_size: 10 });
  expect(citizenPrescriptionBackPath(citizenHistoryPath(query))).toBe("/citizen/medical-history?resource_type=PRESCRIPTION&date_from=2026-10-01&date_to=2026-10-24&page=3");
});

it("ignores invalid dates, unknown types and oversized pages", () => {
  expect(historyQueryFromSearch(new URLSearchParams("date_from=2026-02-30&resource_type=ALL&page=999999999999"))).toEqual({ page: 1, page_size: 10 });
  expect(historyQueryFromSearch(new URLSearchParams("date_from=2026-10-24&date_to=2026-10-01&page=-1"))).toEqual({ date_from: "2026-10-24", page: 1, page_size: 10 });
});

it("matches the API's maximum supported history page", () => {
  expect(historyQueryFromSearch(new URLSearchParams("page=1000")).page).toBe(1000);
  expect(historyQueryFromSearch(new URLSearchParams("page=1001")).page).toBe(1);
});

it.each(["/citizen/medical-history/../login", "/citizen/medical-history-evil", "/\\external.example/citizen/medical-history"])("rejects a disguised non-history destination: %s", (value) => {
  expect(citizenPrescriptionBackPath(value)).toBe("/citizen/appointments");
});
