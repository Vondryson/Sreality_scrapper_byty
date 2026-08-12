"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { ListingFilters, ListingPage, ListingSort } from "@/lib/api/contracts";
import { formatArea, formatCount, formatDistance, formatDuration, formatPrice } from "@/lib/format";
import { analyticsFilters, formDataToListingFilters, listingFiltersToParams, parseListingFilters } from "@/lib/listing-filters";
import { EmptyState, ErrorState, LoadingState } from "./async-state";
import { PriceDashboard } from "./price-dashboard";
import { MapPanel } from "./map-panel";
import styles from "./listing-explorer.module.css";

type LoadState =
  | { key: string; status: "loading" }
  | { key: string; status: "failed" }
  | { key: string; status: "loaded"; data: ListingPage };

export function ListingExplorer() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryKey = searchParams.toString();
  const filters = useMemo(() => parseListingFilters(new URLSearchParams(queryKey)), [queryKey]);
  const [requestAttempt, setRequestAttempt] = useState(0);
  const requestKey = `${queryKey}:${requestAttempt}`;
  const [load, setLoad] = useState<LoadState>({ key: "", status: "loading" });

  useEffect(() => {
    let active = true;
    void api.listings(filters).then(
      (data) => { if (active) setLoad({ key: requestKey, status: "loaded", data }); },
      () => { if (active) setLoad({ key: requestKey, status: "failed" }); },
    );
    return () => { active = false; };
  }, [filters, requestKey]);

  const navigate = (next: ListingFilters) => router.push(`/?${listingFiltersToParams(next)}`);
  const submitFilters = (formData: FormData) => navigate(formDataToListingFilters(formData));
  const changeSort = (sort: ListingSort) => navigate({ ...filters, page: 1, sort });
  const current = load.key === requestKey ? load : { key: requestKey, status: "loading" as const };

  return (
    <div className={styles.stack}>
      <PriceDashboard filters={analyticsFilters(filters)} />
      <FilterPanel key={queryKey} filters={filters} submit={submitFilters} />
      <MapPanel filters={analyticsFilters(filters)} matchingTotal={current.status === "loaded" ? current.data.total : undefined} />
      <div className={styles.listingHeader}>
        <div><p className={styles.kicker}>Výsledky</p><h2>Nabídky</h2></div>
        <label>Řazení
          <select value={filters.sort} onChange={(event) => changeSort(event.target.value as ListingSort)}>
            <option value="newest">Nejnovější</option><option value="price_asc">Cena od nejnižší</option><option value="price_desc">Cena od nejvyšší</option><option value="usable_area_desc">Největší užitná plocha</option><option value="land_area_desc">Největší pozemek</option><option value="price_per_sqm_asc">Cena za m²</option><option value="air_distance_asc">Vzdušná vzdálenost</option><option value="road_distance_asc">Silniční vzdálenost</option><option value="drive_duration_asc">Doba jízdy</option>
          </select>
        </label>
      </div>
      {current.status === "loading" && <LoadingState title="Načítám nabídky…" />}
      {current.status === "failed" && <ErrorState title="Nabídky se nepodařilo načíst" onRetry={() => setRequestAttempt((value) => value + 1)}>Zkuste požadavek zopakovat.</ErrorState>}
      {current.status === "loaded" && current.data.items.length === 0 && <EmptyState title="Žádné nabídky neodpovídají filtrům">Zkuste některé podmínky odebrat.</EmptyState>}
      {current.status === "loaded" && current.data.items.length > 0 && <ListingResults page={current.data} filters={filters} />}
    </div>
  );
}

function FilterPanel({ filters, submit }: { filters: ListingFilters; submit: (form: FormData) => void }) {
  return (
    <details className={styles.filters} open={Object.keys(filters).length > 4}>
      <summary>Filtry <span>Upravit výběr</span></summary>
      <form action={submit}>
        <label>Stav<select name="status" defaultValue={filters.status}><option value="active">Aktivní</option><option value="new">Nové</option><option value="price_decreased">Zlevněné</option><option value="reactivated">Obnovené</option><option value="inactive">Neaktivní</option><option value="all">Všechny</option></select></label>
        <label>Typ<select name="kind" defaultValue={filters.kind ?? ""}><option value="">Chata i chalupa</option><option value="chata">Chata</option><option value="chalupa">Chalupa</option></select></label>
        <label>Kraj<input name="region" defaultValue={filters.region ?? ""} maxLength={120} /></label>
        <label>Okres<input name="district" defaultValue={filters.district ?? ""} maxLength={120} /></label>
        <NumberFilter name="price_min" label="Cena od (Kč)" value={filters.price_min} />
        <NumberFilter name="price_max" label="Cena do (Kč)" value={filters.price_max} />
        <NumberFilter name="usable_area_min" label="Užitná plocha od (m²)" value={filters.usable_area_min} />
        <NumberFilter name="usable_area_max" label="Užitná plocha do (m²)" value={filters.usable_area_max} />
        <NumberFilter name="land_area_min" label="Pozemek od (m²)" value={filters.land_area_min} />
        <NumberFilter name="land_area_max" label="Pozemek do (m²)" value={filters.land_area_max} />
        <NumberFilter name="price_per_sqm_min" label="Cena za m² od" value={filters.price_per_sqm_min} />
        <NumberFilter name="price_per_sqm_max" label="Cena za m² do" value={filters.price_per_sqm_max} />
        <NumberFilter name="air_distance_max_km" label="Vzdušně max. km" value={filters.air_distance_max_km} step="0.1" />
        <NumberFilter name="road_distance_max_km" label="Po silnici max. km" value={filters.road_distance_max_km} step="0.1" />
        <NumberFilter name="drive_duration_max_minutes" label="Jízda max. minut" value={filters.drive_duration_max_minutes} />
        <label>Oblíbené<select name="favorite" defaultValue={filters.favorite === undefined ? "" : String(filters.favorite)}><option value="">Všechny</option><option value="true">Pouze oblíbené</option><option value="false">Bez oblíbených</option></select></label>
        <input type="hidden" name="page_size" value={filters.page_size} /><input type="hidden" name="sort" value={filters.sort} />
        <div className={styles.filterActions}><button type="submit">Použít filtry</button><Link href="/">Vymazat vše</Link></div>
      </form>
    </details>
  );
}

function NumberFilter({ name, label, value, step = "1" }: { name: string; label: string; value: number | undefined; step?: string }) {
  return <label>{label}<input type="number" name={name} min="0" step={step} defaultValue={value} /></label>;
}

function ListingResults({ page, filters }: { page: ListingPage; filters: ListingFilters }) {
  return <div className={styles.results}><p className={styles.total}>{formatCount(page.total)} výsledků · strana {page.page} z {page.pages}</p><div className={styles.tableWrap}><table><thead><tr><th>Nabídka</th><th>Cena</th><th>Plochy</th><th>Vzdálenost od Prahy</th><th>Stav</th></tr></thead><tbody>{page.items.map((item) => <tr key={item.id}><td><Link href={`/nabidky/${item.id}`}><strong>{item.name ?? `${item.kind === "chata" ? "Chata" : "Chalupa"} #${item.sreality_id}`}</strong></Link><span>{item.locality ?? item.municipality ?? "Lokalita neuvedena"}</span></td><td><strong>{formatPrice(item.price_czk)}</strong><span>{formatPrice(item.price_per_sqm_czk)} / m²</span></td><td><span>Užitná {formatArea(item.usable_area_m2)}</span><span>Pozemek {formatArea(item.land_area_m2)}</span></td><td><span>Vzdušně {formatDistance(item.air_distance_km)}</span><span>Silnice {formatDistance(item.road_distance_km)} · {formatDuration(item.drive_duration_minutes)}</span></td><td><span className={item.is_active ? styles.active : styles.inactive}>{item.is_active ? "Aktivní" : "Neaktivní"}</span>{item.is_favorite && <span className={styles.favorite}>★ Oblíbená</span>}</td></tr>)}</tbody></table></div><Pagination page={page} filters={filters} /></div>;
}

function Pagination({ page, filters }: { page: ListingPage; filters: ListingFilters }) {
  const href = (number: number) => `/?${listingFiltersToParams({ ...filters, page: number })}`;
  return <nav className={styles.pagination} aria-label="Stránkování nabídek"><Link aria-disabled={page.page <= 1} tabIndex={page.page <= 1 ? -1 : undefined} href={page.page <= 1 ? href(1) : href(page.page - 1)}>Předchozí</Link><span>Strana {page.page} z {page.pages}</span><Link aria-disabled={page.page >= page.pages} tabIndex={page.page >= page.pages ? -1 : undefined} href={page.page >= page.pages ? href(page.pages) : href(page.page + 1)}>Další</Link></nav>;
}
