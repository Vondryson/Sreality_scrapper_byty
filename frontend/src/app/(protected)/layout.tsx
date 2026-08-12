import type { ReactNode } from "react";
import { ProtectedContent } from "@/components/protected-content";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return <ProtectedContent>{children}</ProtectedContent>;
}
