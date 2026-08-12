import Link from "next/link";
import { EmptyState } from "@/components/async-state";
export default function NotFound() { return <EmptyState title="Tato stránka neexistuje"><Link href="/">Vrátit se na přehled</Link></EmptyState>; }
