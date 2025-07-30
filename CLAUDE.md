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