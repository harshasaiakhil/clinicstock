import React, { createContext, useState, useEffect, useContext } from "react";
import api from "../api";

export interface Branch {
  id: string;
  name: string;
  code: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  default_branch_id: string;
  default_branch?: Branch;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("clinicstock_token"));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get<User>("/auth/me");
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem("clinicstock_token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const storedToken = localStorage.getItem("clinicstock_token");
    if (storedToken) {
      setToken(storedToken);
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await api.post<{ access_token: string; token_type: string }>("/auth/login", {
        email,
        password,
      });
      const receivedToken = response.data.access_token;
      localStorage.setItem("clinicstock_token", receivedToken);
      setToken(receivedToken);

      // Fetch user profile immediately with the new token
      const profileRes = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${receivedToken}` },
      });
      setUser(profileRes.data);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("clinicstock_token");
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      await fetchCurrentUser();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token && !!user,
        loading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
