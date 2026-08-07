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

// Default mock doctor profile matching seed doctor user profile
const DEFAULT_DOCTOR_USER: User = {
  id: "7d7e379f-e7bd-4fda-a770-7064a02ce0db",
  email: "doctor@clinicstock.com",
  first_name: "Admin",
  last_name: "Doctor",
  role: "doctor",
  default_branch_id: "2032a036-792d-4931-8910-ebf26a9cc80e",
  default_branch: {
    id: "2032a036-792d-4931-8910-ebf26a9cc80e",
    name: "Gudivada",
    code: "GDV"
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = "demo-mode-token";
  const [user, setUser] = useState<User>(DEFAULT_DOCTOR_USER);

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get<User>("/auth/me");
      setUser(response.data);
    } catch (error) {
      console.error("Failed to load user profile", error);
      setUser(DEFAULT_DOCTOR_USER);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const login = async (_email: string, _password: string) => {
    return Promise.resolve();
  };

  const logout = () => {
    fetchCurrentUser();
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: true,
        loading: false,
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
