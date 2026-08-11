"use client";

import type { ReactNode } from "react";
import { ErrorState, LoadingState } from "./async-state";
import { useAuth } from "./auth-provider";
import styles from "./protected-content.module.css";

export function ProtectedContent({ children }: { children: ReactNode }) {
  const { state, refresh } = useAuth();
  if (state.status === "loading") return <LoadingState title="Ověřuji přihlášení…" />;
  if (state.status === "error") {
    return <ErrorState title="Přihlášení se nepodařilo ověřit" onRetry={() => void refresh()}>Zkontrolujte, zda běží backend, a zkuste to znovu.</ErrorState>;
  }
  if (state.status === "unauthenticated") {
    return (
      <div className={styles.login}>
        <p className={styles.eyebrow}>Soukromá aplikace</p>
        <h1>Přihlaste se ke svému přehledu</h1>
        <p>Data, oblíbené nabídky i poznámky jsou dostupné pouze povolenému Google účtu.</p>
        <a className={styles.loginButton} href="/api/v1/auth/google/login">Pokračovat přes Google</a>
      </div>
    );
  }
  return children;
}
