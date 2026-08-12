"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { api } from "@/lib/api/client";
import type { ListingDetail, ListingEvent, ListingHistory } from "@/lib/api/contracts";
import { formatArea, formatDate, formatDateTime, formatDistance, formatDuration, formatPrice } from "@/lib/format";
import { safeSourceImageUrl, safeSourceListingUrl } from "@/lib/images";
import { ErrorState, LoadingState } from "./async-state";
import { UserListingControls } from "./user-listing-controls";
import styles from "./listing-detail-view.module.css";

type DetailState = { detail: ListingDetail; history: ListingHistory } | "failed" | null;

export function ListingDetailView({ listingId }: { listingId: number }) {
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${listingId}:${attempt}`;
  const [result, setResult] = useState<{ key: string; value: DetailState }>({ key: "", value: null });
  useEffect(() => {
    let active = true;
    void Promise.all([api.listing(listingId), api.history(listingId)]).then(
      ([detail, history]) => { if (active) setResult({ key: requestKey, value: { detail, history } }); },
      () => { if (active) setResult({ key: requestKey, value: "failed" }); },
    );
    return () => { active = false; };
  }, [listingId, requestKey]);
  const value = result.key === requestKey ? result.value : null;
  if (value === null) return <LoadingState title="Načítám detail nabídky…" />;
  if (value === "failed") return <ErrorState title="Detail se nepodařilo načíst" onRetry={() => setAttempt((current) => current + 1)}>Nabídka mohla být odstraněna nebo je backend dočasně nedostupný.</ErrorState>;
  return <DetailContent detail={value.detail} history={value.history} />;
}

function DetailContent({ detail, history }: { detail: ListingDetail; history: ListingHistory }) {
  const images = detail.images.map((image) => ({ ...image, safeUrl: safeSourceImageUrl(image.source_url) })).filter((image): image is typeof image & { safeUrl: string } => image.safeUrl !== null).slice(0, 12);
  const sourceUrl = safeSourceListingUrl(detail.source_url);
  return (
    <article className={styles.detail}>
      <Link className={styles.back} href="/">← Zpět na přehled</Link>
      <header className={styles.header}><div><p>{detail.kind === "chata" ? "Chata" : "Chalupa"} · {detail.is_active ? "Aktivní nabídka" : "Neaktivní nabídka"}</p><h1>{detail.name ?? `${detail.kind === "chata" ? "Chata" : "Chalupa"} #${detail.sreality_id}`}</h1><span>{detail.locality ?? "Lokalita neuvedena"}</span></div><div className={styles.price}><strong>{detail.price_on_request ? "Cena na vyžádání" : formatPrice(detail.price_czk)}</strong><span>Nabídková cena{detail.price_per_sqm_czk !== null ? ` · ${formatPrice(detail.price_per_sqm_czk)} / m²` : ""}</span></div></header>
      {images.length > 0 && <section className={styles.gallery} aria-label="Fotografie nabídky">{images.map((image, index) => { const archived = image.archive_object_key !== null; const imageUrl = archived ? `/api/v1/listings/${detail.id}/images/${image.position}/archive` : image.safeUrl; return <figure key={`${image.source_url}:${image.position}`} className={index === 0 ? styles.heroImage : styles.image}><Image src={imageUrl} alt={`${detail.name ?? "Nemovitost"} – fotografie ${index + 1}`} width={image.width ?? 800} height={image.height ?? 600} sizes={index === 0 ? "(max-width: 800px) 100vw, 66vw" : "(max-width: 800px) 50vw, 25vw"} unoptimized={archived} />{archived && <figcaption>Soukromě archivováno</figcaption>}</figure>; })}</section>}
      <section className={styles.facts} aria-label="Základní parametry"><Fact label="Užitná plocha" value={formatArea(detail.usable_area_m2)} /><Fact label="Pozemek" value={formatArea(detail.land_area_m2)} /><Fact label="Vzdušně od Prahy" value={formatDistance(detail.air_distance_km)} /><Fact label="Po silnici" value={formatDistance(detail.road_distance_km)} /><Fact label="Doba jízdy" value={formatDuration(detail.drive_duration_minutes)} /><Fact label="Sledováno od" value={formatDate(detail.first_seen_at)} /></section>
      <div className={styles.columns}><section><h2>Popis nabídky</h2><p className={styles.description}>{detail.description ?? "Popis není k dispozici."}</p>{detail.price_note && <p className={styles.priceNote}>{detail.price_note}</p>}{sourceUrl && <a className={styles.source} href={sourceUrl} target="_blank" rel="noreferrer">Otevřít původní inzerát ↗</a>}</section><section><h2>Další parametry</h2><dl className={styles.params}>{Object.entries(detail.params).map(([label, raw]) => <div key={label}><dt>{label}</dt><dd>{displayParam(raw)}</dd></div>)}</dl></section></div>
      <UserListingControls listingId={detail.id} initialFavorite={detail.is_favorite} initialNote={detail.private_note} />
      <PriceHistory history={history} />
      {history.events.length > 0 && <section><h2>Události nabídky</h2><ol className={styles.events}>{history.events.map((event) => <li key={`${event.run_id}:${event.occurred_at}:${event.event_type}`}><span>{formatDateTime(event.occurred_at)}</span><strong>{eventLabel(event)}</strong></li>)}</ol></section>}
    </article>
  );
}

function Fact({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function displayParam(value: unknown): string { if (value === null || value === undefined || value === "") return "Neuvedeno"; if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value); return JSON.stringify(value); }

function PriceHistory({ history }: { history: ListingHistory }) {
  const titleId = useId();
  const priced = history.prices.filter((point): point is typeof point & { price_czk: number } => point.price_czk !== null);
  if (priced.length === 0) return <section><h2>Historie nabídkové ceny</h2><p>Cenová historie zatím není dostupná.</p></section>;
  const width = 760, height = 250, padding = 28;
  const minimum = Math.min(...priced.map((point) => point.price_czk));
  const maximum = Math.max(...priced.map((point) => point.price_czk));
  const spread = maximum - minimum || 1;
  const coordinates = priced.map((point, index) => ({ ...point, x: padding + (priced.length === 1 ? (width - 2 * padding) / 2 : index / (priced.length - 1) * (width - 2 * padding)), y: padding + (maximum - point.price_czk) / spread * (height - 2 * padding) }));
  return <section className={styles.history}><div><h2>Historie nabídkové ceny</h2><span>{priced.length} pozorování</span></div><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={titleId}><title id={titleId}>Historie nabídkové ceny od {formatPrice(priced[0]?.price_czk ?? null)} do {formatPrice(priced.at(-1)?.price_czk ?? null)}</title><polyline points={coordinates.map(({ x, y }) => `${x},${y}`).join(" ")} /><line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} />{coordinates.map((point) => <circle key={point.run_id} cx={point.x} cy={point.y} r="5"><title>{formatDate(point.observed_at)}: {formatPrice(point.price_czk)}</title></circle>)}</svg><div className={styles.historyLabels}><span>{formatDate(priced[0]?.observed_at ?? null)}</span><span>{formatDate(priced.at(-1)?.observed_at ?? null)}</span></div></section>;
}

function eventLabel(event: ListingEvent): string {
  const labels: Record<ListingEvent["event_type"], string> = { created: "Nabídka poprvé zachycena", price_decreased: `Zlevněno z ${formatPrice(event.old_price_czk)} na ${formatPrice(event.new_price_czk)}`, price_increased: `Zdraženo z ${formatPrice(event.old_price_czk)} na ${formatPrice(event.new_price_czk)}`, details_changed: "Změna detailu nabídky", deactivated: "Nabídka deaktivována", reactivated: "Nabídka znovu aktivní" };
  return labels[event.event_type];
}
