"use client";
import { useEffect } from "react";
import { ErrorState } from "@/components/async-state";
export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return <ErrorState title="Přehled se nepodařilo načíst" onRetry={reset}>Zkontrolujte připojení a zkuste požadavek zopakovat.</ErrorState>;
}
