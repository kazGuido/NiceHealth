"""
V2 database migrations - additive only, safe for production.
Runs at startup. Uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def run_v2_migrations(engine):
    """Apply v2 schema changes. Safe to run multiple times."""
    with engine.begin() as conn:
        # --- New tables ---
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR NOT NULL,
                workspace_url VARCHAR,
                primary_user_id UUID REFERENCES users(id),
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_organizations_created_by ON organizations(created_by)"))
        conn.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS primary_user_id UUID REFERENCES users(id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS device_owners (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                is_primary BOOLEAN NOT NULL DEFAULT false,
                assigned_by UUID REFERENCES users(id),
                assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(device_id, organization_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_device_owners_device_id ON device_owners(device_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_device_owners_organization_id ON device_owners(organization_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS locations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                address TEXT,
                phone VARCHAR,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_locations_organization_id ON locations(organization_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS location_devices (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
                device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(location_id, device_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_location_devices_location_id ON location_devices(location_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_location_devices_device_id ON location_devices(device_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS measurement_prices (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                price DECIMAL(12, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'XAF',
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_measurement_prices_organization_id ON measurement_prices(organization_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                email_enabled BOOLEAN NOT NULL DEFAULT true,
                email_address VARCHAR,
                whatsapp_enabled BOOLEAN NOT NULL DEFAULT false,
                whatsapp_number VARCHAR,
                sms_enabled BOOLEAN NOT NULL DEFAULT false,
                sms_number VARCHAR,
                telegram_enabled BOOLEAN NOT NULL DEFAULT false,
                telegram_chat_id VARCHAR,
                webhook_url VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(organization_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alert_preferences_organization_id ON alert_preferences(organization_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workspace_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                brand_name VARCHAR,
                brand_color VARCHAR,
                logo_url VARCHAR,
                favicon_url VARCHAR,
                custom_domain VARCHAR,
                primary_language VARCHAR(10) DEFAULT 'en',
                dashboard_theme VARCHAR(20) DEFAULT 'light',
                metrics_display JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(organization_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workspace_configs_organization_id ON workspace_configs(organization_id)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS retail_user_invites (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                email VARCHAR NOT NULL,
                token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                is_used BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                used_at TIMESTAMP WITH TIME ZONE
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retail_user_invites_organization_id ON retail_user_invites(organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retail_user_invites_token ON retail_user_invites(token)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retail_user_invites_email ON retail_user_invites(email)"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_primary BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(organization_id, user_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_organization_users_organization_id ON organization_users(organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_organization_users_user_id ON organization_users(user_id)"))

        # --- Add columns to health_measurements ---
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS retail_user_id UUID REFERENCES users(id)"))
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id)"))
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES locations(id)"))
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending'"))
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS price DECIMAL(12, 2)"))
        conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))

        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_retail_user_id ON health_measurements(retail_user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_organization_id ON health_measurements(organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_status ON health_measurements(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_deleted_at ON health_measurements(deleted_at)"))

    logger.info("V2 migrations applied successfully")
