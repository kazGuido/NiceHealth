import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

/**
 * Protects V2 routes by role.
 * @param {Object} props
 * @param {React.ReactNode} props.children
 * @param {string[]} props.allowedRoles - e.g. ['admin'], ['admin','customer'], ['retail']
 * @param {string} props.fallbackPath - where to redirect if not allowed (default /v2/login)
 */
const V2ProtectedRoute = ({ children, allowedRoles = [], fallbackPath = '/v2/login' }) => {
  const { isAuthenticated, loading, role } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  const hasRole = allowedRoles.length === 0 || (role && allowedRoles.includes(role));
  if (!hasRole) {
    // Redirect to role-appropriate home
    if (role === 'admin') return <Navigate to="/v2/admin/organizations" replace />;
    if (role === 'customer') return <Navigate to="/v2/dashboard" replace />;
    if (role === 'retail') return <Navigate to="/v2/retail/history" replace />;
    return <Navigate to={fallbackPath} replace />;
  }

  return <>{children}</>;
};

export default V2ProtectedRoute;
