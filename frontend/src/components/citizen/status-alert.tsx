export function StatusAlert({
  message,
  tone = "error",
}: {
  message: string;
  tone?: "error" | "success" | "info";
}) {
  const styles = {
    error: "border-rose-200 bg-rose-50 text-rose-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    info: "border-sky-200 bg-sky-50 text-sky-900",
  };

  return (
    <div
      className={"rounded-xl border px-4 py-3 text-sm leading-6 " + styles[tone]}
      role={tone === "error" ? "alert" : "status"}
    >
      {message}
    </div>
  );
}
