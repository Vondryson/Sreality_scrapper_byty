"use client";

import { useEffect, useId, useState } from "react";
import { ErrorState, LoadingState } from "./async-state";
import { api } from "@/lib/api/client";
import type { ListingFilters, PriceMedians } from "@/lib/api/contracts";
import { formatCount, formatDate, formatPrice } from "@/lib/format";
import styles from "./price-dashboard.module.css";

interface PriceDashboardProps { filters?: ListingFilters }

export function PriceDashboard({ filters = { status: "active" } }: PriceDashboardProps) {
  const [data, setData] = useState<PriceMedians | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const serializedFilters = JSON.stringify(filters);

  useEffect(() => {
    let active = true;
    void api.priceMedians(JSON.parse(serializedFilters) as ListingFilters).then(
      (response) => { if (active) setData(response); },
      () => { if (active) setFailed(true); },
    );
    return () => { active = false; };
  }, [serializedFilters, attempt]);
  const retry = () => { setData(null); setFailed(false); setAttempt((value) => value + 1); };
  if (failed) return <ErrorState title="Medián se nepodařilo načíst" onRetry={retry}>Ostatní data zůstávají v bezpečí. Zkuste analytiku načíst znovu.</ErrorState>;
  if (data === null) return <LoadingState title="Načítám cenový přehled…" />;
  if (data.current_median_price_czk === null) {
    return <section className={styles.empty}><p className={styles.kicker}>Nabídkové ceny</p><h2>Pro tento výběr nemáme cenová data</h2><p>Zkuste rozšířit filtry nebo zahrnout další typ nemovitosti.</p></section>;
  }
  return (
    <section className={styles.dashboard} aria-labelledby="median-title">
      <div className={styles.summary}>
        <div>
          <p className={styles.kicker}>Aktuální medián nabídkových cen</p>
          <h2 id="median-title">{formatPrice(data.current_median_price_czk)}</h2>
          <p className={styles.sample}>Z {formatCount(data.current_sample_size)} aktuálních nabídek s uvedenou cenou</p>
        </div>
        <div className={styles.notice}><strong>Co číslo znamená?</strong><span>Polovina inzerátů je levnější a polovina dražší. Nejde o realizované prodejní ceny.</span></div>
      </div>
      {data.history.length > 0 ? <MedianChart data={data} /> : <p className={styles.noHistory}>Historie vznikne po dalších úspěšných bězích scraperu.</p>}
    </section>
  );
}

function MedianChart({ data }: { data: PriceMedians }) {
  const titleId = useId();
  const width = 760;
  const height = 260;
  const padding = 28;
  const values = data.history.map((point) => point.median_price_czk);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = maximum - minimum || 1;
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  const coordinates = data.history.map((point, index) => ({
    ...point,
    x: padding + (data.history.length === 1 ? plotWidth / 2 : (index / (data.history.length - 1)) * plotWidth),
    y: padding + ((maximum - point.median_price_czk) / spread) * plotHeight,
  }));
  return (
    <div className={styles.chartBlock}>
      <div className={styles.chartHeading}><h3>Vývoj v čase</h3><span>{formatDate(data.history[0]?.observed_at ?? null)} – {formatDate(data.history.at(-1)?.observed_at ?? null)}</span></div>
      <svg className={styles.chart} viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={titleId}>
        <title id={titleId}>Vývoj mediánu nabídkových cen v {data.history.length} úspěšných bězích</title>
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} className={styles.axis} />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className={styles.axis} />
        <polyline points={coordinates.map(({ x, y }) => `${x},${y}`).join(" ")} className={styles.line} />
        {coordinates.map((point) => <circle key={point.run_id} cx={point.x} cy={point.y} r="5" className={styles.point}><title>{formatDate(point.observed_at)}: {formatPrice(point.median_price_czk)}, {formatCount(point.sample_size)} nabídek</title></circle>)}
      </svg>
      <div className={styles.range}><span>{formatPrice(minimum)}</span><span>{formatPrice(maximum)}</span></div>
    </div>
  );
}
