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
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = async (authToken: string | null) => {
    try {
      const headers: Record<string, string> = {};
      if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
      }
      const response = await api.get<User>("/auth/me", { headers });
      setUser(response.data);
    } catch (error) {
      console.error("Failed to load user profile", error);
      // Clean up invalid token
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser(token);
  }, [token]);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const params = { email, password };
      const response = await api.post<{ access_token: string }>("/auth/login", params);
      const accessToken = response.data.access_token;
      localStorage.setItem("token", accessToken);
      setToken(accessToken);
      await fetchCurrentUser(accessToken);
    } catch (error) {
      setLoading(false);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    fetchCurrentUser(null);
  };

  const refreshUser = async () => {
    await fetchCurrentUser(token);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!user,
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
