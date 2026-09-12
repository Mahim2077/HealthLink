import { LabReportPage } from "@/components/diagnostics/lab-report-page";
export default async function Page({ params }: { params: Promise<{ test_id: string }> }) {
  const { test_id } = await params;
  return <LabReportPage testId={test_id} portal="PROFESSIONAL" />;
}
