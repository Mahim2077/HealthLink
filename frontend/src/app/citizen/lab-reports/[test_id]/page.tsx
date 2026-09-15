import { permanentRedirect } from "next/navigation";

export default async function Page({ params }: { params: Promise<{ test_id: string }> }) {
  const { test_id } = await params;
  permanentRedirect(`/citizen/diagnostic-tests/${encodeURIComponent(test_id)}`);
}
