"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { ListingFilters, MapListings } from "@/lib/api/contracts";
import { formatCount } from "@/lib/format";
import { ErrorState, LoadingState } from "./async-state";
import styles from "./map-panel.module.css";

const MapCanvas = dynamic(() => import("./map-canvas").then((module) => module.MapCanvas), {
  ssr: false,
  loading: () => <LoadingState title="Připravuji mapu…" />,
});

export function MapPanel({ filters, matchingTotal }: { filters: ListingFilters; matchingTotal: number | undefined }) {
  const serializedFilters = JSON.stringify(filters);
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${serializedFilters}:${attempt}`;
  const [result, setResult] = useState<{ key: string; data?: MapListings; failed?: true }>({ key: "" });
  useEffect(() => {
    let active = true;
    void api.mapListings(JSON.parse(serializedFilters) as ListingFilters).then(
      (data) => { if (active) setResult({ key: requestKey, data }); },
      () => { if (active) setResult({ key: requestKey, failed: true }); },
    );
    return () => { active = false; };
  }, [serializedFilters, requestKey]);
  const current = result.key === requestKey ? result : { key: requestKey };
  if (current.failed) return <ErrorState title="Mapu se nepodařilo načíst" onRetry={() => setAttempt((value) => value + 1)}>Tabulku můžete dál používat beze změny.</ErrorState>;
  if (!current.data) return <LoadingState title="Načítám body na mapě…" />;
  const missingGps = matchingTotal === undefined ? undefined : Math.max(0, matchingTotal - current.data.total);
  return (
    <section className={styles.panel} aria-labelledby="map-title">
      <div className={styles.heading}><div><p>Mapa</p><h2 id="map-title">Kde nabídky leží</h2></div><span>{formatCount(current.data.total)} bodů{missingGps ? ` · ${formatCount(missingGps)} bez GPS` : ""}</span></div>
      {current.data.items.length === 0 ? <div className={styles.empty}>Žádná nabídka ve výběru nemá použitelné GPS souřadnice.</div> : <MapCanvas items={current.data.items} />}
    </section>
  );
}
