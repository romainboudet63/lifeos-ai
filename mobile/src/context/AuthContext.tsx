import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User } from "../api/types";
import { authApi } from "../api/endpoints";
import { getToken, setToken, clearToken } from "../api/client";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const restoreSession = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      if (token) {
        const me = await authApi.me();
        setUser(me);
      }
    } catch {
      await clearToken();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const { access_token } = await authApi.login(email, password);
      await setToken(access_token);
      const me = await authApi.me();
      setUser(me);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connexion impossible");
      throw e;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    setError(null);
    try {
      await authApi.register(email, password, fullName);
      await login(email, password);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Inscription impossible");
      throw e;
    }
  }, [login]);

  const logout = useCallback(async () => {
    await clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, error, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un AuthProvider");
  return ctx;
}
