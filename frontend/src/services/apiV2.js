/**
 * V2 API Service - White-Label Health Dashboard SaaS
 * All endpoints under /v2 prefix
 */
import api from './api';

const v2 = (path) => `/v2${path}`;

// Admin - Organizations
export const organizationsAdminApi = {
  list: () => api.get(v2('/admin/organizations/')).then((r) => r.data),
  get: (id) => api.get(v2(`/admin/organizations/${id}`)).then((r) => r.data),
  create: (data) => api.post(v2('/admin/organizations/'), data).then((r) => r.data),
  update: (id, data) => api.patch(v2(`/admin/organizations/${id}`), data).then((r) => r.data),
  delete: (id) => api.delete(v2(`/admin/organizations/${id}`)).then((r) => r.data),
};

// Device Owners (Admin)
export const deviceOwnersApi = {
  add: (deviceId, organizationId) =>
    api.post(v2('/device-owners/'), { device_id: deviceId, organization_id: organizationId }).then((r) => r.data),
  listByDevice: (deviceId) => api.get(v2(`/device-owners/device/${deviceId}`)).then((r) => r.data),
  remove: (deviceId, organizationId) =>
    api.delete(v2(`/device-owners/device/${deviceId}/organization/${organizationId}`)).then((r) => r.data),
};

// Customer - Locations
export const locationsApi = {
  list: () => api.get(v2('/organizations/me/locations')).then((r) => r.data),
  get: (id) => api.get(v2(`/organizations/me/locations/${id}`)).then((r) => r.data),
  create: (data) => api.post(v2('/organizations/me/locations'), data).then((r) => r.data),
  update: (id, data) => api.patch(v2(`/organizations/me/locations/${id}`), data).then((r) => r.data),
  delete: (id) => api.delete(v2(`/organizations/me/locations/${id}`)).then((r) => r.data),
  addDevice: (locationId, deviceId) =>
    api.post(v2(`/organizations/me/locations/${locationId}/devices`), { device_id: deviceId }).then((r) => r.data),
  removeDevice: (locationId, deviceId) =>
    api.delete(v2(`/organizations/me/locations/${locationId}/devices/${deviceId}`)).then((r) => r.data),
};

// Customer - Pricing, Alerts, Workspace
export const pricingApi = {
  get: () => api.get(v2('/organizations/me/pricing')).then((r) => r.data),
  create: (data) => api.post(v2('/organizations/me/pricing'), data).then((r) => r.data),
  update: (id, data) => api.patch(v2(`/organizations/me/pricing/${id}`), data).then((r) => r.data),
};

export const alertsApi = {
  get: () => api.get(v2('/organizations/me/alerts')).then((r) => r.data),
  update: (data) => api.patch(v2('/organizations/me/alerts'), data).then((r) => r.data),
};

export const workspaceApi = {
  get: () => api.get(v2('/organizations/me/workspace')).then((r) => r.data),
  update: (data) => api.patch(v2('/organizations/me/workspace'), data).then((r) => r.data),
};

// Customer - Retail User Invites
export const retailInvitesApi = {
  invite: (email) => api.post(v2('/organizations/me/retail-users/invite'), { email }).then((r) => r.data),
  list: () => api.get(v2('/organizations/me/retail-users/invites')).then((r) => r.data),
};

// Measurements (Customer)
export const measurementsV2Api = {
  list: (params = {}) => api.get(v2('/measurements/'), { params }).then((r) => r.data),
  get: (id) => api.get(v2(`/measurements/${id}`)).then((r) => r.data),
  assign: (id, retailUserId) =>
    api.patch(v2(`/measurements/${id}/assign`), { retail_user_id: retailUserId }).then((r) => r.data),
};

// Retail User
export const retailApi = {
  getMeasurements: (params = {}) => api.get(v2('/retail/me/measurements'), { params }).then((r) => r.data),
  getMeasurement: (id) => api.get(v2(`/retail/me/measurements/${id}`)).then((r) => r.data),
  getWorkspace: () => api.get(v2('/retail/me/workspace')).then((r) => r.data),
  deleteMe: () => api.delete(v2('/retail/me')).then((r) => r.data),
  deleteMyData: () => api.delete(v2('/retail/me/data')).then((r) => r.data),
};

// Retail Auth (invite flow)
export const authRetailApi = {
  requestPin: (token) => api.post(v2('/auth/retail/request-pin'), { token }).then((r) => r.data),
  register: (token, pinCode) =>
    api.post(v2('/auth/retail/register'), { token, pin_code: pinCode }).then((r) => r.data),
};

// Public (no auth)
export const publicApi = {
  getLocations: (params = {}) => api.get(v2('/public/locations'), { params }).then((r) => r.data),
  getOrganizations: (params = {}) =>
    api.get(v2('/public/organizations'), { params }).then((r) => r.data),
};

// V2 Report (public)
export const reportV2Api = {
  get: (id) => api.get(v2(`/report/${id}`)).then((r) => r.data),
};

export default {
  organizationsAdminApi,
  deviceOwnersApi,
  locationsApi,
  pricingApi,
  alertsApi,
  workspaceApi,
  retailInvitesApi,
  measurementsV2Api,
  retailApi,
  authRetailApi,
  publicApi,
  reportV2Api,
};
