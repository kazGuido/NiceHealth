import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Dashboard from './components/Dashboard';
import ReportDetail from './components/ReportDetail';
import V2Report from './components/v2/V2Report';
import MeasurementForm from './components/MeasurementForm';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import CustomerList from './components/CustomerList';
import CustomerDetail from './components/CustomerDetail';
import DeviceList from './components/DeviceList';
import UserList from './components/UserList';

// V2 imports
import V2ProtectedRoute from './components/v2/V2ProtectedRoute';
import V2Login from './components/v2/V2Login';
import V2Register from './components/v2/V2Register';
import V2Dashboard from './components/v2/pages/V2Dashboard';
import V2AdminOrganizations from './components/v2/pages/V2AdminOrganizations';
import V2AdminOrganizationDetail from './components/v2/pages/V2AdminOrganizationDetail';
import V2AdminDeviceOwners from './components/v2/pages/V2AdminDeviceOwners';
import V2Locations from './components/v2/pages/V2Locations';
import V2Measurements from './components/v2/pages/V2Measurements';
import V2Pricing from './components/v2/pages/V2Pricing';
import V2Alerts from './components/v2/pages/V2Alerts';
import V2Workspace from './components/v2/pages/V2Workspace';
import V2Invites from './components/v2/pages/V2Invites';
import V2RetailHistory from './components/v2/pages/V2RetailHistory';
import V2RetailSettings from './components/v2/pages/V2RetailSettings';
import V2PublicLocations from './components/v2/pages/V2PublicLocations';
import V2PublicOrganizations from './components/v2/pages/V2PublicOrganizations';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* V1 routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customers"
            element={
              <ProtectedRoute>
                <CustomerList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/:id"
            element={
              <ProtectedRoute>
                <CustomerDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/devices"
            element={
              <ProtectedRoute>
                <DeviceList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute requireAdmin>
                <UserList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/report/:id"
            element={
              <ProtectedRoute>
                <ReportDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/add"
            element={
              <ProtectedRoute>
                <MeasurementForm />
              </ProtectedRoute>
            }
          />

          {/* V2 routes */}
          <Route path="/v2" element={<Navigate to="/v2/login" replace />} />
          <Route path="/v2/login" element={<V2Login />} />
          <Route path="/v2/register" element={<V2Register />} />

          {/* V2 public (no auth) */}
          <Route path="/v2/report/:id" element={<V2Report />} />
          <Route path="/v2/discover/locations" element={<V2PublicLocations />} />
          <Route path="/v2/discover/organizations" element={<V2PublicOrganizations />} />

          {/* V2 admin */}
          <Route
            path="/v2/admin/organizations"
            element={
              <V2ProtectedRoute allowedRoles={['admin']}>
                <V2AdminOrganizations />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/admin/organizations/:id"
            element={
              <V2ProtectedRoute allowedRoles={['admin']}>
                <V2AdminOrganizationDetail />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/admin/device-owners"
            element={
              <V2ProtectedRoute allowedRoles={['admin']}>
                <V2AdminDeviceOwners />
              </V2ProtectedRoute>
            }
          />

          {/* V2 customer (machine owner) */}
          <Route
            path="/v2/dashboard"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Dashboard />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/locations"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Locations />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/measurements"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Measurements />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/pricing"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Pricing />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/alerts"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Alerts />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/workspace"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Workspace />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/invites"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'customer']}>
                <V2Invites />
              </V2ProtectedRoute>
            }
          />

          {/* V2 retail */}
          <Route
            path="/v2/retail/history"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'retail']}>
                <V2RetailHistory />
              </V2ProtectedRoute>
            }
          />
          <Route
            path="/v2/retail/settings"
            element={
              <V2ProtectedRoute allowedRoles={['admin', 'retail']}>
                <V2RetailSettings />
              </V2ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
