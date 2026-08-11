"use client";

import Link from "next/link";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import type { MapListing } from "@/lib/api/contracts";
import { formatDistance, formatPrice } from "@/lib/format";
import { mapTileConfig } from "@/lib/map-config";
import styles from "./map-panel.module.css";

export function MapCanvas({ items }: { items: MapListing[] }) {
  const bounds = items.map((item) => [item.latitude, item.longitude]) as LatLngBoundsExpression;
  const tiles = mapTileConfig();
  return (
    <MapContainer className={styles.map ?? ""} bounds={bounds} boundsOptions={{ padding: [24, 24], maxZoom: 13 }} scrollWheelZoom>
      <TileLayer url={tiles.url} attribution={tiles.attribution} />
      {items.map((item) => (
        <CircleMarker key={item.id} center={[item.latitude, item.longitude]} radius={item.is_favorite ? 9 : 7} pathOptions={{ color: item.is_favorite ? "#8a6100" : "#176b4b", fillColor: item.is_favorite ? "#f2bd35" : "#32a675", fillOpacity: 0.9 }}>
          <Popup><div className={styles.popup}><strong>{item.name ?? `${item.kind === "chata" ? "Chata" : "Chalupa"} #${item.sreality_id}`}</strong><span>{item.locality ?? "Lokalita neuvedena"}</span><span>{formatPrice(item.price_czk)}</span><span>Vzdušně {formatDistance(item.air_distance_km)}</span><Link href={`/nabidky/${item.id}`}>Zobrazit detail</Link></div></Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
