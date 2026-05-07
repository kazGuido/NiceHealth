# TODO for Next Agent: V2 UI & Backend Completion

**Context**: Health Data App is being upgraded to a White-Label Health Dashboard SaaS. The V2 backend is partially implemented. This TODO covers everything missing in both backend and frontend for the next agent to implement.

---

## BACKEND GAPS

### 1. Admin: Link Users to Organizations
- [ ] **Endpoint**: `POST /v2/admin/organizations/{id}/users` – Add user to org (as primary or delegate)
- [ ] **Endpoint**: `DELETE /v2/admin/organizations/{id}/users/{user_id}` – Remove user from org
- [ ] **Endpoint**: `GET /v2/admin/organizations/{id}/users` – List users in org
- [ ] When creating org, admin must be able to select existing user (or create user first) as `primary_user_id`
- [ ] Update user role to `customer` when linking to org (or require user to already have role `customer`)

### 2. Retail User List for Assignment
- [ ] **Endpoint**: `GET /v2/organizations/me/retail-users` – List retail users created/invited by this org (for measurement assignment dropdown)
- [ ] Consider: retail users are global (email unique) but we need to filter by "invited by this org" or "has measurements from this org"

### 3. Devices for Organization
- [ ] **Endpoint**: `GET /v2/organizations/me/devices` – List devices owned by my org(s) (for location device assignment)
- [ ] Uses `device_owners` table; join Device to get device_id, name, etc.

### 4. Retail Invite Email
- [ ] Send email when inviting retail user: include registration link `{FRONTEND_URL}/v2/register?token={invite.token}`
- [ ] Use existing `email_service.py`; add template for invite
- [ ] Ensure `RetailUserInvite` is created before sending (already done in `invite_retail_user`)

### 5. V2 Report Endpoint – Use Workspace Branding
- [ ] Current `/v2/report/{id}` uses `Device.owner` (User) for branding
- [ ] When `measurement.organization_id` is set, use `WorkspaceConfig` for branding instead
- [ ] Fallback: Device.owner → WorkspaceConfig(org) → default NiceDay branding

### 6. Branded Report Email
- [ ] **Endpoint**: `POST /v2/measurements/{id}/send-report` – Send branded report to email (for retail user or kiosk flow)
- [ ] Use `WorkspaceConfig` for branding in email template
- [ ] May extend existing `send_report_email` or create v2 variant

### 7. Analytics for Machine Owner
- [ ] **Endpoint**: `GET /v2/organizations/me/analytics` – Revenue (price × count), measurement count, device usage
- [ ] **Endpoint**: `GET /v2/organizations/me/analytics/revenue` – Breakdown by period
- [ ] Price is informational (offline billing); compute from `measurement.price` or `measurement_prices`

### 8. Retail User Login
- [ ] Retail users can use existing `/auth/request-pin` + `/auth/verify-pin` (email + PIN)
- [ ] OR ensure `/v2/auth/retail/register` is the only way to create retail account (invite flow)
- [ ] Document: retail users who registered via invite use standard login with their email

### 9. CORS / Environment
- [ ] Ensure `VITE_API_URL` and `FRONTEND_URL` support v2 frontend routes
- [ ] CORS for v2 app domain if different

### 10. Minor Backend Fixes
- [ ] `GET /v2/measurements/` – Fix filter for non-admin when no device owners exist (avoid empty result for public devices)
- [ ] Add `updated_at` to `OrganizationResponse` schema if missing
- [ ] Validate `organization_id` in `OrganizationCreate` – user must exist and have role `customer` (or allow any user)

---

## FRONTEND GAPS

### 1. V2 API Service Layer
- [ ] Create `src/services/apiV2.js` (or extend `api.js`) with all V2 endpoints:
  - `organizationsApi`: admin CRUD, me/locations, me/pricing, me/alerts, me/workspace, me/retail-users/invite
  - `measurementsApi`: list, get, assign (v2)
  - `deviceOwnersApi`: add, list, remove
  - `retailApi`: me/measurements, me/workspace, delete me, delete me/data
  - `authRetailApi`: request-pin, register
  - `publicApi`: locations, organizations
- [ ] Use same `axios` instance (token from localStorage) for authenticated calls

### 2. Role-Based Auth & Routing
- [ ] Extend `AuthContext`: add `isCustomer`, `isRetail`, `role`
- [ ] Create `RoleRoute` or `V2ProtectedRoute`: restrict by role (admin, customer, retail)
- [ ] Redirect: admin → `/v2/admin`, customer → `/v2/dashboard`, retail → `/v2/retail/history`

### 3. V2 Layout & Navigation
- [ ] Create `V2Layout.jsx` – sidebar/nav for V2 app
- [ ] Admin nav: Organizations, Devices, Device Owners, Users
- [ ] Customer nav: Dashboard, Locations, Measurements (pending/assign), Pricing, Alerts, Workspace, Invites
- [ ] Retail nav: My Measurements, Settings (delete data)

### 4. Admin V2 Pages
- [ ] `/v2/admin/organizations` – List, create, edit organizations
- [ ] `/v2/admin/organizations/:id` – Detail, link users, view devices
- [ ] `/v2/admin/device-owners` – Assign devices to orgs (or from org detail page)
- [ ] User picker: fetch `/admin/users`, filter by role or allow setting role when linking

### 5. Customer (Machine Owner) V2 Pages
- [ ] `/v2/dashboard` – Overview: pending measurements count, recent activity, quick stats
- [ ] `/v2/locations` – CRUD locations, add/remove devices per location
- [ ] `/v2/measurements` – List with filters (status=pending), assign to retail user (dropdown)
- [ ] `/v2/pricing` – Set/update measurement price
- [ ] `/v2/alerts` – Configure email, WhatsApp, etc.
- [ ] `/v2/workspace` – Branding: logo, colors, domain
- [ ] `/v2/invites` – Invite retail users, list invites

### 6. Retail User V2 Pages
- [ ] `/v2/retail/history` – List my measurements (paginated)
- [ ] `/v2/retail/report/:id` – View single measurement (branded)
- [ ] `/v2/retail/settings` – Delete my data, delete account (with confirmation)

### 7. Retail Auth Flow (Invite Registration)
- [ ] `/v2/register` – Page reads `?token=` from URL
- [ ] Step 1: Call `POST /v2/auth/retail/request-pin` with token → PIN sent to email
- [ ] Step 2: User enters PIN → Call `POST /v2/auth/retail/register` with token + pin
- [ ] On success: store token, redirect to `/v2/retail/history`

### 8. Public Pages (No Auth)
- [ ] `/v2/locations` – List locations (filter by org), for end users to find where to get measured
- [ ] `/v2/organizations` – List orgs with branding (browse machine owners)

### 9. V2 Report Page Alignment
- [ ] Current `V2Report.jsx` uses `/v2/report/:id` – verify backend returns correct structure
- [ ] When backend uses `WorkspaceConfig`, ensure frontend displays `brand_name`, `brand_color`, `logo_url`, `cta_text`, `cta_link`
- [ ] Handle `measurement.data` structure (may have `datas` array from device format)

### 10. Entry Point & Routing
- [ ] Add all V2 routes to `App.jsx` under `/v2/*`
- [ ] `/v2` or `/v2/login` – Login (reuse existing Login or create V2-specific)
- [ ] `/v2/admin/*` – Admin only
- [ ] `/v2/dashboard`, `/v2/locations`, etc. – Customer only
- [ ] `/v2/retail/*` – Retail only
- [ ] `/v2/register` – Public (invite token required)
- [ ] `/v2/report/:id` – Public (already exists)
- [ ] `/v2/locations`, `/v2/organizations` – Public discovery

### 11. UI/UX Details
- [ ] Loading states, error handling, empty states for all lists
- [ ] Form validation (e.g. email for invite, price > 0)
- [ ] Toast/notification for success (e.g. "Measurement assigned", "Invite sent")
- [ ] Responsive design (mobile-friendly for retail users)

### 12. Environment
- [ ] `VITE_API_URL` – ensure points to backend (e.g. `https://niceq.nicedaytech.com` for prod)
- [ ] Optional: `VITE_V2_ENABLED` to gate V2 routes

---

## IMPLEMENTATION ORDER (Suggested)

1. **Backend**: Analytics, retail user list, devices for org, invite email, report branding
2. **Frontend**: apiV2 service, AuthContext role extension, V2 layout
3. **Frontend**: Admin V2 pages (organizations, device owners)
4. **Frontend**: Customer V2 pages (dashboard, measurements, locations, pricing, alerts, workspace, invites)
5. **Frontend**: Retail pages (history, report, settings)
6. **Frontend**: Retail registration flow, public discovery pages
7. **Polish**: Error handling, loading states, responsive

---

## REFERENCE FILES

- **Backend**: `app/routers/v2/`, `app/models_v2.py`, `app/schemas_v2.py`, `app/auth_v2.py`
- **Frontend**: `src/App.jsx`, `src/services/api.js`, `src/contexts/AuthContext.jsx`, `src/components/v2/V2Report.jsx`
- **API spec**: `V2_API_SUMMARY.md`
- **Docker**: `docker-compose.yml` – backend port 8002, frontend 5173
