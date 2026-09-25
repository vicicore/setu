"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "setu-citizen-id";
const DEFAULT_CITIZEN_ID = "citizen-guest-001";

/** There is no Supabase Auth wired up yet (see docs/DECISIONS.md), so
 * there is no real logged-in citizen. This stands in for it: a
 * browser-local identifier, editable on /profile, so the product's
 * non-demo pages (Journeys, Vault, Profile) have something concrete to
 * scope requests to. It is not a security boundary — the backend does
 * not currently verify who's asking. */
export function useCitizenId(): [string, (id: string) => void] {
  const [citizenId, setCitizenIdState] = useState(DEFAULT_CITIZEN_ID);

  useEffect(() => {
    // Reading localStorage — an external system unavailable during SSR
    // — is the documented "synchronize with an external system" case.
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (stored) setCitizenIdState(stored);
    } catch {
      // ignore — default stands
    }
  }, []);

  const setCitizenId = useCallback((id: string) => {
    setCitizenIdState(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // best-effort only
    }
  }, []);

  return [citizenId, setCitizenId];
}
