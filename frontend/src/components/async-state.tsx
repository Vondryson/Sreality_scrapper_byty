import type { ReactNode } from "react";
import styles from "./async-state.module.css";

interface StateProps {
  title: string;
  children?: ReactNode;
}

export function LoadingState({ title = "Načítám data…" }: Partial<StateProps>) {
  return (
    <section className={styles.state} role="status" aria-live="polite" aria-busy="true">
      <span className={styles.spinner} aria-hidden="true" />
      <div><h2>{title}</h2><p>Chvíli strpení, připravujeme aktuální přehled.</p></div>
    </section>
  );
}

export function EmptyState({ title, children }: StateProps) {
  return (
    <section className={styles.state}>
      <span className={styles.icon} aria-hidden="true">⌂</span>
      <div><h2>{title}</h2>{children && <p>{children}</p>}</div>
    </section>
  );
}

interface ErrorStateProps extends StateProps { onRetry?: () => void }

export function ErrorState({ title, children, onRetry }: ErrorStateProps) {
  return (
    <section className={`${styles.state} ${styles.error}`} role="alert">
      <span className={styles.icon} aria-hidden="true">!</span>
      <div>
        <h2>{title}</h2>
        {children && <p>{children}</p>}
        {onRetry && <button className={styles.button} type="button" onClick={onRetry}>Zkusit znovu</button>}
      </div>
    </section>
  );
}
