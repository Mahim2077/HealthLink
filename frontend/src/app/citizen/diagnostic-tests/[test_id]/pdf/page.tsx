import { DiagnosticPdfPage } from "@/components/diagnostics/diagnostic-pdf";

export default async function Page({ params }: { params: Promise<{ test_id: string }> }) {
  const { test_id } = await params;
  return <DiagnosticPdfPage id={test_id} portal="CITIZEN" />;
}
