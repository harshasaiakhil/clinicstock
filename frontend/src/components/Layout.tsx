import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import {
  LayoutDashboard,
  Pill,
  Menu,
  X,
  User,
  Building,
  FolderOpen,
  LineChart,
  Settings,
} from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user } = useUser();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = [
    {
      name: "Dashboard",
      path: "/",
      icon: LayoutDashboard,
    },
    {
      name: "Medicines",
      path: "/medicines",
      icon: Pill,
    },
    ...(user?.role === "doctor"
      ? [
          {
            name: "Master Config",
            path: "/masters",
            icon: FolderOpen,
          },
        ]
      : []),
    {
      name: "Reports & Logs",
      path: "/reports",
      icon: LineChart,
    },
    ...(user?.role === "doctor"
      ? [
          {
            name: "System Settings",
            path: "/settings",
            icon: Settings,
          },
        ]
      : []),
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar for Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Component */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-slate-100 bg-teal-900 text-white">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500 shadow-md">
              <Pill className="h-5 w-5 text-teal-950" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-white block leading-none">ClinicStock</span>
              <span className="text-[10px] text-teal-300 font-medium tracking-wider uppercase">Homeopathy ERP</span>
            </div>
          </div>
          <button
            className="rounded-lg p-1 text-teal-200 hover:bg-teal-800 hover:text-white lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* User context card inside Sidebar */}
        {user && (
          <div className="p-4 mx-4 mt-4 rounded-xl bg-slate-50 border border-slate-100">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-semibold shadow-inner">
                {(user?.first_name?.[0] ?? "")}{(user?.last_name?.[0] ?? "")}
              </div>
              <div className="overflow-hidden">
                <span className="block text-sm font-semibold text-slate-800 truncate">
                  {user?.first_name ?? ""} {user?.last_name ?? ""}
                </span>
                <span className="inline-flex items-center rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-medium text-teal-700 capitalize border border-teal-100">
                  {user.role}
                </span>
              </div>
            </div>
            {user.default_branch && (
              <div className="mt-3 flex items-center space-x-2 text-xs text-slate-500">
                <Building className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                <span className="truncate font-medium">{user.default_branch.name} Branch</span>
              </div>
            )}
          </div>
        )}

        {/* Sidebar Nav links */}
        <nav className="flex-1 space-y-1 px-4 py-4 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const linkClass = `flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${
              isActive
                ? "bg-teal-50 text-teal-700 font-bold shadow-sm"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`;

            return (
              <Link
                key={item.name}
                to={item.path}
                className={linkClass}
                onClick={() => setSidebarOpen(false)}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`h-5 w-5 shrink-0 ${isActive ? "text-teal-600" : "text-slate-400"}`} />
                  <span>{item.name}</span>
                </div>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
          <div className="flex items-center space-x-4">
            <button
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-50 hover:text-slate-900 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            <h1 className="text-xl font-bold text-slate-800 hidden sm:block">
              {location.pathname === "/" ? "Dashboard Analytics" : "ClinicStock"}
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            {/* Branch pill tag */}
            {user?.default_branch && (
              <div className="text-xs font-semibold text-slate-500 bg-slate-100/75 border border-slate-200/50 rounded-lg px-2.5 py-1.5 hidden sm:flex items-center space-x-1.5 shadow-sm">
                <Building className="h-3.5 w-3.5 text-teal-600" />
                <span>Active Branch: <strong className="text-slate-800">{user.default_branch.name}</strong></span>
              </div>
            )}

            {/* Quick Profile Tag */}
            <div className="h-8 w-px bg-slate-200" />
            <div className="flex items-center space-x-2.5">
              <span className="text-xs font-semibold text-slate-700 hidden md:block">
                Welcome, ClinicStock
              </span>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-600 shadow-sm border border-slate-200">
                <User className="h-4 w-4" />
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard/Page Body */}
        <main className="flex-1 overflow-y-auto bg-slate-50 p-6 sm:p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
