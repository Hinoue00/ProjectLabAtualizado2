# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Django Management
- `python manage.py runserver` - Start development server
- `python manage.py makemigrations` - Create database migrations
- `python manage.py migrate` - Apply database migrations
- `python manage.py createsuperuser` - Create admin superuser
- `python manage.py collectstatic` - Collect static files
- `python manage.py test` - Run all tests
- `python manage.py test <app_name>` - Run tests for specific app

### Custom Management Commands
- `python manage.py create_default_technician` - Create default technician user
- `python manage.py test_emails` - Test email functionality
- `python manage.py setup_departments` - Setup department structure
- `python manage.py debug_chart_data` - Debug dashboard charts
- `python manage.py clean_old_departments` - Clean deprecated department data

### Environment Setup
- Requires PostgreSQL database with connection details in `.env` file
- Uses development settings by default (`LabConnect.settings.development`)
- Logging directory `logs/` created automatically

### Chatbot Configuration
- **CHATBOT_ENABLED**: Set to 'True' to enable AI chatbot functionality (default: 'False')
- When disabled, chatbot UI is hidden and API endpoints return 503 status
- Recommended to keep disabled on production servers with limited CPU resources

### Production Optimization (Janeiro 2025)
- **Files Removed**: All test files (`tests.py`), debug commands, temporary files, and development documentation
- **Requirements Optimized**: Created `requirements-production-light.txt` without heavy AI dependencies
- **Chatbot Disabled**: Default configuration for production performance
- **Size Reduction**: Removed ~30+ development/test files for cleaner production deployment

## Architecture Overview

### Core Django Apps
- **accounts** - Custom user authentication with email-based login, supports professors and technicians with approval workflow
- **laboratories** - Laboratory management with departments and technician assignments
- **inventory** - Material inventory with AI-powered categorization using Docling/spaCy NLP
- **scheduling** - Laboratory scheduling system with calendar interface and approval workflow
- **dashboard** - Role-based dashboards with different views for professors vs technicians
- **reports** - Report generation system
- **api** - REST API endpoints and AI chatbot integration
- **whatsapp** - WhatsApp integration for notifications

### Key Architecture Patterns

#### Custom User Model
- Uses email instead of username for authentication
- Role-based access (professor/technician) with approval system
- Domain-restricted registration (@cogna.com.br, @kroton.com.br)

#### AI/ML Integration
- **Inventory AI**: Uses Docling service with spaCy Portuguese model for material categorization
- **Chatbot**: Ollama integration for AI assistant functionality
- **Document Processing**: Automated analysis of uploaded materials and documents

#### Multi-tenant Laboratory System
- Laboratories belong to departments with color coding
- Multiple technicians can be assigned to laboratories
- Complex scheduling system with conflict detection

#### Settings Architecture
- Split settings: `base.py`, `development.py`, `production.py`
- Environment-based configuration using python-dotenv
- Feature flags for AI services (DOCLING_ENABLED, WHATSAPP_ENABLED)

### Database Schema Highlights
- Custom User model with approval workflow
- Laboratory-Department relationship with legacy field migration
- Material inventory with AI analysis data storage (JSONField)
- Schedule requests with draft/approval states and file attachments

### Frontend Architecture
- Bootstrap 5 with Crispy Forms
- Custom CSS variables system for theming
- Modular JavaScript (calendar-module.js, dashboard-main.js, chatbot.js)
- Responsive design with mobile-specific CSS

### Key Configuration
- Uses PostgreSQL in development/production
- Static files served from `staticfiles/` (dev) and `staticfiles_collected/` (prod)
- Media files in `media/` directory
- Comprehensive logging to `logs/labconnect.log`
- File upload limits configured via environment variables

### AI Service Dependencies
- spaCy with Portuguese model (pt_core_news_sm)
- Docling for document processing
- OpenAI integration for advanced AI features
- Ollama for local LLM integration

## Recent Updates & New Features

### GitHub Actions CI/CD (Agosto 2024)
- **Deploy Automático**: Configurado deploy automático via GitHub Actions com testes e validação
- **PostgreSQL 14**: Atualizado CI para usar PostgreSQL 14 conforme requisitos do Django
- **Secrets Configurados**: SSH keys e credenciais configuradas para deploy em produção
- **Chave SSH Corrigida**: Formato da chave SSH privada ajustado para funcionamento correto

### UI/UX Improvements (ATT0.1 Branch)
- **Dark Theme Standardization**: Consistent dark mode across all pages using centralized CSS variables
- **Mobile Responsive Design**: Enhanced mobile layout fixes for calendar and dashboard views
- **Professor Calendar Enhancement**: Aligned professor calendar cards with technician interface styling patterns
- **Navigation Consistency**: Standardized sidebar styling and navigation colors across all modules

### Inventory System Enhancements
- **Read-Only Access for Professors**: Professors can now view laboratory materials but cannot modify inventory
- **Bulk Material Operations**: Added mass selection and batch operations for material management
- **Inter-Laboratory Material Transfer**: Ability to move materials between different laboratories
- **Stock Alert Logic Improvements**: Fixed minimum stock alert logic (now uses < instead of <=)
- **Enhanced Material Organization**: Improved inventory organization with better categorization

### Scheduling System Updates
- **Class/Semester Field**: Added class_semester field to both ScheduleRequest and DraftScheduleRequest models
- **Enhanced Request Forms**: Updated scheduling forms to include semester/class information
- **Improved Data Tracking**: Better tracking of which classes/semesters are using laboratory resources

### CI/CD & Deployment Infrastructure
- **GitHub Actions Integration**: Automated CI/CD pipeline with testing and deployment
- **Automated Testing**: Tests run on every push/PR to main branch
- **Production Deploy Automation**: Automatic deployment to production server after successful tests
- **Server Health Monitoring**: Integrated health checks and service verification
- **Backup Integration**: Automatic backup before deployment using existing git-deploy.sh script

### Development & Maintenance
- **Log Management**: Added logs/labconnect.log to .gitignore for cleaner repository
- **Server Documentation**: Comprehensive production server analysis and documentation
- **Deployment Scripts**: Enhanced deployment automation with monitoring and health checks
- **Infrastructure Monitoring**: Detailed server resource monitoring and status tracking

## Deployment & CI/CD

### GitHub Actions Workflow
The project now includes automated CI/CD pipeline (`.github/workflows/deploy.yml`):

#### Test Stage
- Runs on all pushes and pull requests to main
- Uses PostgreSQL 13 service container for testing
- Python 3.11 environment with dependency caching
- Automated database migrations and test execution
- Environment variables automatically configured for testing

#### Deploy Stage
- Triggered only on successful tests for main branch pushes
- SSH deployment to production server (custom port 2222)
- Integrates with existing `git-deploy.sh` script
- Automatic service health checks and restart if needed
- Post-deployment verification of service status

### Production Server Infrastructure
Detailed server analysis documented in `labconnect-server-analysis.md`:

#### Server Specifications
- **OS**: Ubuntu 24.04.2 LTS with Intel Celeron J1800
- **Stack**: Django + PostgreSQL + Redis + Nginx + Gunicorn
- **Security**: SSL/HTTPS enforced, HSTS enabled, corporate domain restrictions
- **Monitoring**: Ngrok integration for external access with automated URL updates

#### Key Production Features
- **Multi-department Support**: Color-coded departments with assigned technicians
- **Automated Backup**: Pre-deployment backup system with 5-backup rotation
- **Health Monitoring**: Service status verification and automatic recovery
- **AI Integration**: Docling + spaCy for Portuguese document processing
- **Role-based Access**: Separate interfaces for professors vs technicians

#### Service Management
- **Application**: Gunicorn WSGI server (3 workers) on port 8000
- **External Access**: Ngrok tunneling with automatic URL monitoring
- **Logs**: Centralized logging to `/var/www/labconnect/logs/labconnect.log`
- **Deploy Scripts**: Automated deployment via `/home/labadm/git-deploy.sh`

## Technical Specifications Update

### Enhanced Database Schema
Recent migrations added:
- **scheduling_0009**: Added `class_semester` field to ScheduleRequest model
- **scheduling_0010**: Added `class_semester` field to DraftScheduleRequest model

### New URL Patterns
- **Professor Material Views**: Read-only access routes for professors to view laboratory materials
- **Inventory Management**: Enhanced bulk operations and inter-laboratory transfers
- **API Endpoints**: Extended chatbot and assistant functionality

### CSS Architecture Improvements
- **Centralized Variables**: `variables.css` for consistent theming across all pages
- **Dark Mode**: Comprehensive dark theme implementation in `materials-dark-mode.css`
- **Mobile Optimization**: `professor-calendar-mobile-fix.css` for responsive design
- **Cross-platform Consistency**: `professor-consistency.css` for unified styling patterns

### Security & Performance
- **Log File Management**: Proper gitignore configuration for sensitive log files
- **Static File Optimization**: Separated collected static files for production
- **Cache Management**: Enhanced Redis integration for session management
- **HTTPS Enforcement**: Production-grade SSL configuration with HSTS

## Deploy Test
- **Test Deploy**: Deploy automation test - 2025-08-04 ✅