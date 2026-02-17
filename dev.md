# LINKEDWIFI Multi-Tenant SaaS Development Guide (dev.md)

This document contains the complete development plan and instructions for building LINKEDWIFI, a multi-tenant SaaS system for managing ISP hotspots and home routers. It is intended to be read by OpenCode AI or any developer to implement the system exactly as specified.

---

## 1. Project Overview

LINKEDWIFI is a professional SaaS system designed to manage hotspot and home router internet services. It provides:

* Multi-tenant support (Super-Admin, ISP Admin, Users)
* Multi-router and device management
* Reliable session handling with phone + OTP login
* Time-based HOTSPOT packages
* Long-term HOME router packages
* Payment integration with M-Pesa Paybill
* FreeRADIUS authentication for MikroTik Hotspot
* Professional landing page and dashboards

---

## 2. Multi-Tenant Architecture

### 2.1 Roles

1. **Super-Admin**

   * Manage all tenants
   * Global statistics
   * Add/remove tenants and ISP Admins

2. **ISP Admin**

   * Manage own tenant
   * Dashboard for users, devices, payments, packages, tickets

3. **Users**

   * Connect via captive portal
   * Login via phone + OTP
   * Buy packages and access internet

### 2.2 Multi-Tenant Database

All tables must include `tenant_id` to ensure data isolation.

Tables include:

* tenants
* users
* packages
* sessions
* payments
* devices
* messages
* tickets

---

## 3. Backend Specification

### 3.1 Tech Stack

* Python 3.11+ (FastAPI)
* PostgreSQL 15+
* Redis (for background jobs and session cleanup)
* FreeRADIUS 3.x
* Nginx (reverse proxy for production)

### 3.2 Folder Structure

```
linkedwifi_saas/
├─ main.py
├─ database.py
├─ models.py
├─ routers/
│   ├─ superadmin.py
│   ├─ ispadmin.py
│   ├─ devices.py
│   ├─ sessions.py
│   ├─ auth.py
│   └─ payments.py
├─ utils/
│   ├─ otp.py
│   ├─ freeradius.py
│   └─ mpesa.py
└─ requirements.txt
```

### 3.3 Backend Features

* Authentication: Phone + OTP
* Session engine: MAC + IP + phone binding, reconnect logic
* Payment: M-Pesa Paybill STK push + callback
* Devices: MikroTik routers, active sessions
* Finance: Packages CRUD, payments, invoices, expenses
* Tickets & messages
* Admin dashboards (Super-Admin, ISP Admin)

---

## 4. Frontend Specification

### 4.1 Tech Stack

* React + Next.js
* TailwindCSS
* Recharts / ApexCharts for dashboards

### 4.2 Features

* Super-Admin Dashboard: global stats, tenant management
* ISP Admin Dashboard: active users, packages, payments, devices, tickets
* Landing Page / Pitch Page: CTA, features, testimonials, pricing
* Multi-tenant login UI (Super-Admin vs ISP Admin)

---

## 5. Database Schema (PostgreSQL)

Tables with multi-tenant support:

### tenants

* tenant_id, name, email, plan, created_at

### users

* tenant_id, phone, mac_address, ip_address, created_at, status

### packages

* tenant_id, name, duration_minutes, speed_limit_rx, speed_limit_tx, price, category

### sessions

* tenant_id, user_id, package_id, start_time, end_time, status

### payments

* tenant_id, user_id, package_id, mpesa_receipt, amount, status, created_at

### devices

* tenant_id, device_type, ip, mac, status, last_seen

### tickets

* tenant_id, user_id, subject, status, created_at, resolved_at

### messages

* tenant_id, sender, receiver, type, content, timestamp

---

## 6. FreeRADIUS Integration

* Each tenant session validated via FreeRADIUS
* MAC + IP + phone binding
* Expired sessions auto-blocked
* FreeRADIUS must use DB auth for MVP testing

---

## 7. Session & Reconnect Logic

1. User logs in via phone + OTP
2. Selects HOTSPOT package
3. Payment success → session created in DB → FreeRADIUS authorization
4. On reconnect:

   * Check session by phone
   * If active, rebind MAC/IP
   * If expired, deny access

---

## 8. M-Pesa Integration

* Paybill STK push + callback
* Sync phone, package, and session
* Only activate session after payment success

---

## 9. Development Roadmap & AI Workflow

1. **Database & ORM models**

   * Generate PostgreSQL tables and FastAPI ORM models with multi-tenant support
   * Seed sample data (2 MikroTik devices, 5 HOTSPOT packages)

2. **Authentication Module**

   * Phone + OTP login API
   * OTP generator + validator

3. **Session Engine Module**

   * Create session on payment success
   * MAC + IP + phone binding
   * Reconnection logic
   * FreeRADIUS integration

4. **Payment Integration Module**

   * M-Pesa Paybill STK push + callback API
   * Update payments table, activate sessions

5. **Devices & Admin Module**

   * ISP Admin dashboard APIs for devices, users, packages, finance, tickets, messages
   * Super-Admin APIs for tenant management, global stats

6. **Frontend Module**

   * Landing page / pitch page (Next.js + Tailwind)
   * Super-Admin & ISP Admin dashboards
   * Multi-tenant login

7. **Testing Module**

   * Local testing instructions for PostgreSQL + FreeRADIUS + MikroTik
   * Sample user login, package purchase, session activation, reconnect

8. **Deployment Module**

   * Instructions for VPS deployment
   * Environment setup, Nginx, SSL, FastAPI production server

**AI Workflow Instructions for OpenCode:**

* Read `dev.md`
* Start with **Database & ORM** → test
* Then **Authentication module** → test OTP flow
* Then **Session engine + FreeRADIUS** → test reconnects
* Then **Payment integration** → test M-Pesa flow
* Then **Admin dashboards** → verify stats & multi-tenant data
* Then **Frontend** → landing page + dashboards
* Generate code **module by module**, ensure each module works before next
* Include comments + setup instructions for every module

---

## 10. Testing Instructions

* Run PostgreSQL + FreeRADIUS on PC (WSL2 or Ubuntu VM)
* Connect PC to MikroTik LAN (ether2)
* Seed test packages + devices
* Test login → session → reconnect → payment flow
* Verify dashboards display correct stats

---

# End of dev.md

This file must be used by OpenCode AI to generate the system **exactly as specified**, following the AI workflow step-by-step for a production-ready multi-tenant SaaS system.
