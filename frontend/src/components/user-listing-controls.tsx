"use client";

import { useState } from "react";
import type { UserListingUpdate } from "@/lib/api/contracts";
import { api } from "@/lib/api/client";
import { useAuth } from "./auth-provider";
import styles from "./user-listing-controls.module.css";

export function UserListingControls({ listingId, initialFavorite, initialNote }: { listingId: number; initialFavorite: boolean; initialNote: string | null }) {
  const { state } = useAuth();
  const [favorite, setFavorite] = useState(initialFavorite);
  const [note, setNote] = useState(initialNote ?? "");
  const [busy, setBusy] = useState<"favorite" | "note" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  if (state.status !== "authenticated") return null;
  const save = async (update: UserListingUpdate, kind: "favorite" | "note") => {
    setBusy(kind); setFailed(false); setMessage(null);
    try {
      const result = await api.updateUserListing(listingId, update, state.csrfToken);
      if (update.is_favorite !== undefined) setFavorite(result.is_favorite);
      if (Object.hasOwn(update, "private_note")) setNote(result.private_note ?? "");
      const archiveSummary = result.is_favorite ? ` Archivováno: ${result.archived_images}, chybně: ${result.failed_images}.` : "";
      setMessage(`${kind === "favorite" ? "Oblíbený stav" : "Poznámka"} uložen.${archiveSummary}`);
    } catch { setFailed(true); }
    finally { setBusy(null); }
  };
  return (
    <section className={styles.controls} aria-labelledby="private-data-title">
      <div className={styles.heading}><div><p>Soukromé</p><h2 id="private-data-title">Moje údaje</h2></div><button type="button" className={favorite ? styles.favorite : undefined} aria-pressed={favorite} disabled={busy !== null} onClick={() => void save({ is_favorite: !favorite }, "favorite")}>{busy === "favorite" ? "Ukládám…" : favorite ? "★ V oblíbených" : "☆ Přidat do oblíbených"}</button></div>
      <form onSubmit={(event) => { event.preventDefault(); void save({ private_note: note.trim() || null }, "note"); }}><label htmlFor="private-note">Soukromá poznámka</label><textarea id="private-note" maxLength={10_000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Co je na nabídce zajímavé, co ověřit při prohlídce…" /><div><span>{note.length.toLocaleString("cs-CZ")} / 10 000</span><button type="submit" disabled={busy !== null}>{busy === "note" ? "Ukládám…" : "Uložit poznámku"}</button></div></form>
      <div className={styles.feedback} aria-live="polite">{failed ? <span className={styles.failure}>Uložení se nepodařilo. Zkuste to znovu.</span> : message}</div>
    </section>
  );
}
