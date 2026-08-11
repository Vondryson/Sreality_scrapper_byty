"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "@/lib/api/client";

type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "error" }
  | { status: "authenticated"; email: string; csrfToken: string };

interface AuthContextValue {
  state: AuthState;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadAuthState(): Promise<AuthState> {
  try {
    const session = await api.session();
    return {
      status: "authenticated",
      email: session.email,
      csrfToken: session.csrf_token,
    };
  } catch (error) {
    return error instanceof ApiError && error.status === 401
      ? { status: "unauthenticated" }
      : { status: "error" };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const refresh = useCallback(async () => {
    setState(await loadAuthState());
  }, []);

  useEffect(() => {
    let active = true;
    void loadAuthState().then((nextState) => {
      if (active) setState(nextState);
    });
    const restoreWhenVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", restoreWhenVisible);
    return () => {
      active = false;
      document.removeEventListener("visibilitychange", restoreWhenVisible);
    };
  }, [refresh]);

  const logout = useCallback(async () => {
    if (state.status !== "authenticated") return;
    try {
      await api.logout(state.csrfToken);
      setState({ status: "unauthenticated" });
    } catch {
      setState({ status: "error" });
    }
  }, [state]);

  const value = useMemo(() => ({ state, refresh, logout }), [state, refresh, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
