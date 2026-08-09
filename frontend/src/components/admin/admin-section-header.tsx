import Link from "next/link";


export function AdminSectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="border-b border-slate-200 pb-7">
      <Link className="text-sm font-bold text-indigo-700 hover:text-indigo-900" href="/admin/dashboard">← Admin Dashboard</Link>
      <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">{eyebrow}</p>
      <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">{title}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
    </header>
  );
}
