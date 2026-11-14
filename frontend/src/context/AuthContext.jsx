import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { busApi } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      const data = await busApi.getMe();
      setUser(data.user || null);
      setSession(data.session || null);
      return data;
    } catch {
      setUser(null);
      setSession(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const registerUser = useCallback(async (payload) => {
    return busApi.register(payload);
  }, []);

  const loginUser = useCallback(async (credentials) => {
    const data = await busApi.loginUser(credentials);
    setUser(data.user || null);
    setSession(data.session || null);
    return data;
  }, []);

  const loginAdmin = useCallback(async (credentials) => {
    const data = await busApi.loginAdmin(credentials);
    setUser(data.user || null);
    setSession(data.session || null);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await busApi.logout();
    } finally {
      setUser(null);
      setSession(null);
    }
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      await busApi.logoutAll();
    } finally {
      setUser(null);
      setSession(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isAuthenticated: Boolean(user),
        isAdmin: user?.role === "ADMIN",
        isUser: user?.role === "USER",
        setUser,
        refreshMe,
        registerUser,
        loginUser,
        loginAdmin,
        logout,
        logoutAll,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
