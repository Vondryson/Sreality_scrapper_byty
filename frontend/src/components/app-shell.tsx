import Link from "next/link";
import type { ReactNode } from "react";
import { UserMenu } from "./user-menu";
import styles from "./app-shell.module.css";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.frame}>
      <a className={styles.skipLink} href="#main-content">Přeskočit na hlavní obsah</a>
      <header className={styles.header}>
        <Link className={styles.brand} href="/" aria-label="Sreality Tracker – úvod">
          <span className={styles.mark} aria-hidden="true">ST</span>
          <span><strong>Sreality Tracker</strong><small>Chaty a chalupy</small></span>
        </Link>
        <UserMenu />
      </header>
      <main className={styles.main} id="main-content" tabIndex={-1}>{children}</main>
      <footer className={styles.footer}>
        Uvedené ceny jsou nabídkové ceny inzerátů, nikoli odhad skutečné prodejní ceny.
      </footer>
    </div>
  );
}
