# UPGRADE - Financial Assistant Platform

## Overview

UPGRADE is a Django-based financial assistant platform that helps users plan and track purchases for projects (PC builds, home renovations, electronics, etc.). The system features an AI-powered chatbot that analyzes user financial profiles against project costs to provide intelligent purchasing recommendations, comparing prices across multiple Brazilian retailers and suggesting optimal payment strategies based on the user's income and cash flow.

The platform supports three user roles: regular users who track personal projects, partners who earn affiliate commissions, and administrators who manage the system.

## Recent Changes (December 2025)

### Unified Dashboard Architecture
- **Unified base_dashboard.html**: Single template with left sidebar navigation for all user roles (admin, partner, regular user)
- **Role-based navigation**: Sidebar dynamically shows different menu items based on user role
- **HTMX integration**: Async loading of "For You" recommendations panel
- **Context processors**: Global financial data and user role context available across all templates

### New Features
- **Finance Engine**: Smart Choice algorithm for product recommendations based on user's financial profile
- **For You Recommendations**: AI-powered suggestions for missing items in projects using Groq
- **Ghost Mode**: Admin can view/edit other users' projects (admin_user_projects)
- **Master Links**: Admin can configure global affiliate tags used as fallback

### Admin Panel Restructuring  
- **New sidebar layout**: Created `base_dashboard.html` with fixed left sidebar navigation
- **Separate admin pages**: 
  - Visao Geral (dashboard) - metrics + recent activity widget
  - Usuarios - full users table with role badges and "Ver Projetos" links
  - Projetos - all projects with values and monthly installments
  - Auditoria - complete audit logs table
  - Links Mestres - global affiliate tag management
- **Security**: Added `@admin_required` decorator for admin-only views
- **Edit Mode button**: Moved to header (top right)
- **Django Admin link**: Moved to sidebar footer (discreet location)

### Security Fix
- **Login page cleaned**: Removed insecure "Criar dados de demonstracao" link and associated `setup_demo` view/URL
- **Test users management command**: Created `python manage.py setup_test_users` for controlled test user creation via terminal
- **Admin-only decorators**: Protected all admin endpoints with `@admin_required`

### Test Users (created via management command)
- Admin: `ADM-MASTER-01` / `Sup3r_S3cur3_P@ssw0rd!`
- Partner: `PRT-TEST-ALPHA` / `P@rtner_M0ney_2025`
- User: `USR-CLIENT-007` / `My_Dr3am_S3tup_Go!`

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Django 5.0** with Python as the primary backend framework
- Custom user model extending `AbstractUser` with role-based access (user, partner, admin)
- Custom authentication backend (`UnifiedAuthBackend`) supporting login via username, email, or corporate ID

### Database Design
- SQLite for development (Django default), easily migrated to PostgreSQL
- Key models: `User`, `Project`, `Item`, `PartnerProfile`, `AdminSettings`, `AuditLog`, `PartnerClick`
- Projects contain Items with detailed pricing info (cash price, installment price, number of installments)
- Users have financial profile fields: `monthly_income`, `fixed_expenses`, `safety_margin`

### AI/Chatbot Integration
- **Groq API** for LLM-powered chat responses (financial advice)
- **SerpAPI** for real-time product price searches (Google Shopping)
- Financial analysis logic in `core/financial_services.py`:
  - `DollarQuoteService`: Real-time USD/BRL exchange rates from AwesomeAPI
  - `ImportTaxCalculator`: Brazilian import tax calculations (ICMS, Remessa Conforme rules)
  - `FinancialSniper`: Core recommendation engine comparing user income vs project costs
  - `IncomeProjectAnalyzer`: Contextual affordability analysis (income vs item price)

### Chatbot Intelligence Features
- Full financial profile sent to AI: monthly income, expenses, free cash flow, commitments
- Database automation commands via AI:
  - `[SALVAR_ITEM]` - Add items to projects
  - `[TROCAR_ITEM]` - Replace items with alternatives
  - `[ATUALIZAR_ITEM]` - Update item fields
  - `[ANALISAR_ACESSIBILIDADE]` - Analyze if item fits user budget

### Dashboard Alerts
- Smart financial alerts on user dashboard:
  - Critical alert (red): Over-committed finances
  - Warning alert (yellow): >50% commitment
  - Positive alert (green): Healthy finances with >R$500 available and <=30% commitment

### Frontend Architecture
- Server-side rendered Django templates with Tailwind CSS (via CDN)
- Chat widget implemented as a floating FAB button (`templates/partials/chat_widget.html`)
- Responsive design with mobile support

### API Endpoints
- RESTful JSON APIs under `/api/` prefix for chatbot interactions:
  - `/api/chatbot/message/` - Main chat endpoint
  - `/api/chatbot/dollar/` - Dollar quote
  - `/api/chatbot/import/` - Import tax calculations
  - `/api/chatbot/payment/` - Payment analysis
  - `/api/chatbot/context/` - User financial context

### Affiliate System
- Partners have custom affiliate tags per store (Amazon, Kabum, Pichau, Terabyte, AliExpress)
- Links are dynamically rewritten with affiliate tags via `generate_affiliate_link()` utility
- Click tracking via `PartnerClick` model

## External Dependencies

### APIs (Requires Environment Variables)
- **GROQ_API_KEY**: Groq LLM API for intelligent chat responses
- **SERPAPI_KEY**: SerpAPI for Google Shopping price searches
- **AwesomeAPI**: Free Brazilian currency API (economia.awesomeapi.com.br) - no key required

### Python Packages
- `django` - Web framework
- `groq` - Groq AI client library
- `google-search-results` (serpapi) - Price search functionality
- `requests` - HTTP client for external APIs

### Affiliate Store Integrations
- Amazon Brazil (affiliate tag system)
- Kabum
- Pichau
- Terabyte
- AliExpress
- Mercado Livre

### Frontend Dependencies
- Tailwind CSS (loaded via CDN, no build step required)