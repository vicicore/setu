"use client";

import { useCallback, useEffect, useState } from "react";
import { authApi } from "./api";

const TOKEN_KEY = "setu-auth-token";
const CITIZEN_ID_KEY = "setu-auth-citizen-id";
const ROLE_KEY = "setu-auth-role";

export interface AuthState {
  token: string | null;
  citizenId: string | null;
  role: "citizen" | "admin" | null;
  isLoggedIn: boolean;
}

function readStoredAuth(): AuthState {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const citizenId = localStorage.getItem(CITIZEN_ID_KEY);
    const role = localStorage.getItem(ROLE_KEY) as "citizen" | "admin" | null;
    return { token, citizenId, role, isLoggedIn: Boolean(token && citizenId) };
  } catch {
    return { token: null, citizenId: null, role: null, isLoggedIn: false };
  }
}

// NavBar and whichever page the citizen is on each call useAuth()
// independently — plain useState alone would leave every instance but
// the one that actually called login()/logout() showing stale state
// (e.g. NavBar still showing "Log in" right after /login redirects
// away). This event is how every other instance in the same tab knows
// to re-read localStorage.
const AUTH_CHANGED_EVENT = "setu-auth-changed";

/** There is no Supabase Auth wired up yet (see docs/DECISIONS.md) — this
 * is real server-verified authentication (a bearer token the backend
 * issues and checks on every request), just not Aadhaar/Supabase-backed
 * yet. Token is stored in localStorage; api.ts reads it directly for
 * the Authorization header on every citizen-scoped call. */
export function useAuth() {
  const [state, setState] = useState<AuthState>({
    token: null,
    citizenId: null,
    role: null,
    isLoggedIn: false,
  });

  useEffect(() => {
    // Reading localStorage — unavailable during SSR — is the documented
    // "synchronize with an external system" case.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(readStoredAuth());
    const resync = () => setState(readStoredAuth());
    window.addEventListener(AUTH_CHANGED_EVENT, resync);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, resync);
  }, []);

  const login = useCallback(async (identifier: string) => {
    const session = await authApi.login(identifier);
    try {
      localStorage.setItem(TOKEN_KEY, session.token);
      localStorage.setItem(CITIZEN_ID_KEY, session.citizen_id);
      localStorage.setItem(ROLE_KEY, session.role);
    } catch {
      // best-effort only
    }
    setState({
      token: session.token,
      citizenId: session.citizen_id,
      role: session.role as "citizen" | "admin",
      isLoggedIn: true,
    });
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
    return session;
  }, []);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(CITIZEN_ID_KEY);
      localStorage.removeItem(ROLE_KEY);
    } catch {
      // best-effort only
    }
    setState({ token: null, citizenId: null, role: null, isLoggedIn: false });
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
  }, []);

  return { ...state, login, logout };
}

/** Read directly (not via the hook) for api.ts's request() helper, which
 * is a plain module outside React. */
export function getStoredAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
