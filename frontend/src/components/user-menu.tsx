"use client";

import { useState } from "react";
import { useAuth } from "./auth-provider";
import styles from "./user-menu.module.css";

export function UserMenu() {
  const { state, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  if (state.status !== "authenticated") return <span className={styles.private}>Soukromý přehled</span>;
  const handleLogout = async () => {
    setBusy(true);
    await logout();
    setBusy(false);
  };
  return (
    <div className={styles.menu}>
      <span className={styles.email}>{state.email}</span>
      <button type="button" disabled={busy} onClick={() => void handleLogout()}>{busy ? "Odhlašuji…" : "Odhlásit"}</button>
    </div>
  );
}
