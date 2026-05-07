# V2 API Summary - White-Label Health Dashboard SaaS

V2 backend runs alongside V1. Same database, additive migrations. All V2 endpoints are under `/v2` prefix.

## Roles

| Role | Description |
|------|-------------|
| `admin` | Platform admin (NiceDayTech) |
| `customer` | Machine owner (manages locations, pricing, assigns measurements) |
| `retail` | End user (has measurement history, can request data deletion) |

## Authentication

- **Admin/Customer**: Use existing `/auth/register`, `/auth/request-pin`, `/auth/verify-pin`
- **Retail**: Invite flow via `/v2/auth/retail/request-pin` + `/v2/auth/retail/register`

## V2 Endpoints

### Admin (Machine Owner Management)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/admin/organizations/` | Create organization |
| GET | `/v2/admin/organizations/` | List organizations |
| GET | `/v2/admin/organizations/{id}` | Get organization |
| PATCH | `/v2/admin/organizations/{id}` | Update organization |
| DELETE | `/v2/admin/organizations/{id}` | Deactivate organization |

### Device Ownership (Admin)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/device-owners/` | Add org as device owner |
| GET | `/v2/device-owners/device/{device_id}` | List device owners |
| DELETE | `/v2/device-owners/device/{id}/organization/{id}` | Remove device owner |

### Customer (Machine Owner) - Locations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/organizations/me/locations` | Create location |
| GET | `/v2/organizations/me/locations` | List locations |
| GET | `/v2/organizations/me/locations/{id}` | Get location |
| PATCH | `/v2/organizations/me/locations/{id}` | Update location |
| DELETE | `/v2/organizations/me/locations/{id}` | Deactivate location |
| POST | `/v2/organizations/me/locations/{id}/devices` | Add device to location |
| DELETE | `/v2/organizations/me/locations/{id}/devices/{device_id}` | Remove device |

### Customer - Pricing, Alerts, Workspace
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/organizations/me/pricing` | Set measurement price |
| GET | `/v2/organizations/me/pricing` | Get pricing |
| PATCH | `/v2/organizations/me/pricing/{id}` | Update pricing |
| GET | `/v2/organizations/me/alerts` | Get alert preferences |
| PATCH | `/v2/organizations/me/alerts` | Update alert preferences |
| GET | `/v2/organizations/me/workspace` | Get workspace branding |
| PATCH | `/v2/organizations/me/workspace` | Update workspace branding |

### Customer - Retail User Invites
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/organizations/me/retail-users/invite` | Invite retail user |
| GET | `/v2/organizations/me/retail-users/invites` | List invites |

### Measurements (Customer)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/measurements/` | List measurements (filter by status, org) |
| GET | `/v2/measurements/{id}` | Get measurement |
| PATCH | `/v2/measurements/{id}/assign` | Assign to retail user |

### Retail User
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/retail/me/measurements` | My measurement history |
| GET | `/v2/retail/me/measurements/{id}` | Get my measurement |
| GET | `/v2/retail/me/workspace` | Get workspace branding |
| DELETE | `/v2/retail/me` | Soft delete account |
| DELETE | `/v2/retail/me/data` | Soft delete all my data |

### Retail Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/auth/retail/request-pin` | Request PIN (body: `{token}`) |
| POST | `/v2/auth/retail/register` | Register with token + PIN |

### Public (No Auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/public/locations` | List locations (filter by org) |
| GET | `/v2/public/organizations` | List orgs with branding |

## Database (V2 Additions)

- `organizations` - Machine owners
- `organization_users` - Links users to orgs
- `device_owners` - Device ↔ Organization (many-to-many)
- `locations` - Per-organization
- `location_devices` - Location ↔ Device (many-to-many)
- `measurement_prices` - Per-org pricing
- `alert_preferences` - Per-org alerts
- `workspace_configs` - Per-org branding
- `retail_user_invites` - Invite tokens

## Measurement Flow

1. Kiosk sends measurement → stored as `pending` (existing `/receive-measurement`, `/health-data/receive-measurement`)
2. Machine owner assigns measurement to retail user → `status=assigned`, `retail_user_id` set
3. Retail user logs in → sees history at `/v2/retail/me/measurements`
4. Retail user can request data deletion (soft delete)

## Next Steps

- [ ] Link User (role=customer) to Organization via admin
- [ ] Send invite email with registration link
- [ ] Branded report email + app page
- [ ] Location discovery map/nearby
