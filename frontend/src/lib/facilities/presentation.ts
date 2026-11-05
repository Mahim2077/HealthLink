type FacilityLabelDetails = {
  id: string;
  name: string;
  area?: string | null;
  address?: string | null;
  registration_number?: string | null;
};

/** Public registry details distinguish facilities, never internal IDs or coordinates. */
export function facilityOptionLabels<T extends FacilityLabelDetails>(facilities: readonly T[]): Map<string, string> {
  const nameCounts = new Map<string, number>();
  const normalize = (value: string) => value.trim().toLocaleLowerCase();
  for (const facility of facilities) {
    const key = normalize(facility.name);
    nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
  }
  const labels = facilities.map((facility) => {
    const details = [facility.name];
    const area = facility.area?.trim();
    const address = facility.address?.trim();
    if (area || address) details.push(area || address!);
    if ((nameCounts.get(normalize(facility.name)) ?? 0) > 1) {
      if (area && address && normalize(area) !== normalize(address)) details.push(address);
      if (facility.registration_number?.trim()) details.push(`Registration ${facility.registration_number.trim()}`);
    }
    return details.join(" · ");
  });
  const labelCounts = new Map<string, number>();
  for (const label of labels) labelCounts.set(normalize(label), (labelCounts.get(normalize(label)) ?? 0) + 1);
  const listingNumbers = new Map<string, number>();
  return new Map(facilities.map((facility, index) => {
    const label = labels[index];
    const key = normalize(label);
    if ((labelCounts.get(key) ?? 0) < 2) return [facility.id, label];
    const listing = (listingNumbers.get(key) ?? 0) + 1;
    listingNumbers.set(key, listing);
    return [facility.id, `${label} · Listing ${listing} (details need confirmation)`];
  }));
}
