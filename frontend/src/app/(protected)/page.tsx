import { Suspense } from "react";
import { LoadingState } from "@/components/async-state";
import { ListingExplorer } from "@/components/listing-explorer";
import styles from "../page.module.css";

export default function HomePage() {
  return (
    <div className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Analýza trhu · Česká republika</p>
        <h1>Najděte chatu, která dává smysl.</h1>
        <p className={styles.lead}>Soukromý přehled nabídek, cenových změn a vzdáleností od Prahy. Data jsou pravidelně ukládána, takže u každé nemovitosti uvidíte i její historii.</p>
      </section>
      <Suspense fallback={<LoadingState title="Připravuji filtry…" />}><ListingExplorer /></Suspense>
    </div>
  );
}
