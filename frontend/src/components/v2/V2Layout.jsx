import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const navItem = (to, label, icon) => ({ to, label, icon });

const V2Layout = ({ children }) => {
  const { user, logout, role } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const adminNav = [
    navItem('/v2/admin/organizations', 'Organizations', 'business'),
    navItem('/v2/admin/device-owners', 'Device Owners', 'devices'),
  ];

  const customerNav = [
    navItem('/v2/dashboard', 'Dashboard', 'dashboard'),
    navItem('/v2/locations', 'Locations', 'place'),
    navItem('/v2/measurements', 'Measurements', 'assignment'),
    navItem('/v2/pricing', 'Pricing', 'payments'),
    navItem('/v2/alerts', 'Alerts', 'notifications'),
    navItem('/v2/workspace', 'Workspace', 'palette'),
    navItem('/v2/invites', 'Invites', 'person_add'),
  ];

  const retailNav = [
    navItem('/v2/retail/history', 'My Measurements', 'history'),
    navItem('/v2/retail/settings', 'Settings', 'settings'),
  ];

  const getNavItems = () => {
    if (role === 'admin') return adminNav;
    if (role === 'customer') return customerNav;
    if (role === 'retail') return retailNav;
    return [];
  };

  const handleLogout = () => {
    logout();
    navigate('/v2/login');
  };

  const navItems = getNavItems();

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar - desktop */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-white border-r border-slate-200">
        <div className="flex items-center h-16 px-6 border-b border-slate-200">
          <span className="font-bold text-xl text-slate-800">Health V2</span>
        </div>
        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              <span className="material-icons-round text-xl">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3 px-4 py-2 text-sm text-slate-600">
            <span className="material-icons-round text-slate-400">person</span>
            <span className="truncate">{user?.email}</span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full mt-2 flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <span className="material-icons-round text-xl">logout</span>
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 h-14 flex items-center justify-between px-4">
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg hover:bg-slate-100"
        >
          <span className="material-icons-round">menu</span>
        </button>
        <span className="font-bold text-slate-800">Health V2</span>
        <div className="w-10" />
      </div>

      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/30"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <aside
        className={`lg:hidden fixed top-14 left-0 bottom-0 w-64 bg-white border-r border-slate-200 z-40 transform transition-transform ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <nav className="p-4 space-y-1">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
                  isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              <span className="material-icons-round text-xl">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200 bg-white">
          <p className="text-xs text-slate-500 truncate px-2">{user?.email}</p>
          <button
            onClick={() => {
              handleLogout();
              setMobileMenuOpen(false);
            }}
            className="w-full mt-2 flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <span className="material-icons-round">logout</span>
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 lg:pl-64 pt-14 lg:pt-0">
        <div className="p-4 md:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
};

export default V2Layout;
