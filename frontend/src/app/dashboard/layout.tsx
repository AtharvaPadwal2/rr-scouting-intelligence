
import type { ReactNode } from "react";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <main className="min-h-screen w-full overflow-x-hidden bg-[#071426]">
      {children}
    </main>
  );
}
