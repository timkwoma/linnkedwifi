-- Minimal FreeRADIUS SQL tables for auth/reply checks.
create table if not exists radcheck (
    id serial primary key,
    username varchar(64) not null,
    attribute varchar(64) not null,
    op char(2) not null default ':=',
    value varchar(253) not null
);
create index if not exists ix_radcheck_username on radcheck (username);

create table if not exists radreply (
    id serial primary key,
    username varchar(64) not null,
    attribute varchar(64) not null,
    op char(2) not null default ':=',
    value varchar(253) not null
);
create index if not exists ix_radreply_username on radreply (username);
