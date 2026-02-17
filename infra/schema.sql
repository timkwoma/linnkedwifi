-- LINKEDWIFI PostgreSQL schema reference. ORM creates the same structure.
create extension if not exists "uuid-ossp";

create table if not exists tenants (
    tenant_id uuid primary key default uuid_generate_v4(),
    name varchar(120) not null,
    email varchar(255) not null unique,
    plan varchar(64) not null default 'starter',
    active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists accounts (
    account_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid null references tenants(tenant_id),
    role varchar(32) not null,
    full_name varchar(120) not null,
    phone varchar(20) not null,
    email varchar(255),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    constraint uq_accounts_phone_tenant unique (tenant_id, phone)
);

create table if not exists users (
    user_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    phone varchar(20) not null,
    mac_address varchar(32),
    ip_address varchar(64),
    status varchar(32) not null default 'active',
    created_at timestamptz not null default now(),
    constraint uq_users_phone_tenant unique (tenant_id, phone)
);

create table if not exists packages (
    package_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    name varchar(120) not null,
    duration_minutes int not null,
    speed_limit_rx int not null,
    speed_limit_tx int not null,
    price numeric(10,2) not null,
    category varchar(32) not null,
    active boolean not null default true,
    constraint uq_package_name_tenant unique (tenant_id, name)
);

create table if not exists sessions (
    session_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    user_id uuid not null references users(user_id),
    package_id uuid not null references packages(package_id),
    phone varchar(20) not null,
    mac_address varchar(32),
    ip_address varchar(64),
    start_time timestamptz not null default now(),
    end_time timestamptz not null,
    status varchar(32) not null default 'pending',
    last_reconnected_at timestamptz
);
create index if not exists ix_sessions_lookup on sessions (tenant_id, phone, status, end_time);

create table if not exists payments (
    payment_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    user_id uuid not null references users(user_id),
    package_id uuid not null references packages(package_id),
    phone varchar(20) not null,
    mpesa_checkout_request_id varchar(128),
    mpesa_receipt varchar(64),
    amount numeric(10,2) not null,
    status varchar(32) not null default 'pending',
    created_at timestamptz not null default now()
);

create table if not exists devices (
    device_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    device_type varchar(64) not null default 'mikrotik',
    name varchar(120) not null,
    ip varchar(64) not null,
    mac varchar(32) not null,
    status varchar(32) not null default 'offline',
    last_seen timestamptz,
    created_at timestamptz not null default now(),
    constraint uq_device_mac_tenant unique (tenant_id, mac)
);

create table if not exists tickets (
    ticket_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    user_id uuid not null references users(user_id),
    subject varchar(255) not null,
    status varchar(32) not null default 'open',
    created_at timestamptz not null default now(),
    resolved_at timestamptz
);

create table if not exists messages (
    message_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references tenants(tenant_id),
    sender varchar(120) not null,
    receiver varchar(120) not null,
    type varchar(64) not null default 'notification',
    content text not null,
    timestamp timestamptz not null default now()
);

create table if not exists otp_codes (
    otp_id uuid primary key default uuid_generate_v4(),
    tenant_id uuid null references tenants(tenant_id),
    phone varchar(20) not null,
    role varchar(32) not null,
    code_hash varchar(255) not null,
    expires_at timestamptz not null,
    failed_attempts int not null default 0,
    lock_until timestamptz,
    used boolean not null default false,
    created_at timestamptz not null default now()
);
create index if not exists ix_otp_lookup on otp_codes (phone, role, tenant_id, used);
