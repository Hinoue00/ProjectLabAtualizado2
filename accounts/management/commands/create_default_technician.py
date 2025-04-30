from django.core.management.base import BaseCommand
from accounts.models import User
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password

class Command(BaseCommand):
    help = 'Creates a default technician user with administrative privileges and Django superuser access'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admin@kroton.com.br',
                            help='Email for the default technician (default: admin@kroton.com.br)')
        parser.add_argument('--password', type=str, default='labconnect2025',
                            help='Password for the default technician (default: labconnect2025)')
        parser.add_argument('--department', type=str, default='computer',
                            choices=['computer', 'engineering', 'health'],
                            help='Department for the technician (default: computer)')
        parser.add_argument('--bypass-validation', action='store_true',
                            help='Bypass password validation when creating the user')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        department = options['department']
        bypass_validation = options['bypass_validation']
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User with email {email} already exists.'))
            user = User.objects.get(email=email)
            # Update user to ensure correct privileges
            user.is_approved = True
            user.user_type = 'technician'
            user.lab_department = department
            user.is_staff = True        # Allow access to Django admin
            user.is_superuser = True    # Grant all permissions
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated existing user {email} with technician privileges and Django admin access.'))
            return
        
        # Create new technician user
        try:
            with transaction.atomic():
                # If bypass_validation is True, create user directly with hashed password
                if bypass_validation:
                    user = User(
                        email=email,
                        password=make_password(password),  # Hash the password directly
                        first_name='Admin',
                        last_name='Technician',
                        user_type='technician',
                        phone_number='99999999999',
                        is_approved=True,
                        is_active=True,
                        is_staff=True,        # Allow access to Django admin
                        is_superuser=True,    # Grant all permissions
                        registration_date=timezone.now(),
                        lab_department=department
                    )
                    user.save()
                else:
                    # Try with normal create_user method first
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name='Admin',
                        last_name='Technician',
                        user_type='technician',
                        phone_number='99999999999',
                        is_approved=True,
                        is_staff=True,        # Allow access to Django admin
                        is_superuser=True,    # Grant all permissions
                        registration_date=timezone.now(),
                        lab_department=department
                    )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created default technician user: {email}'))
            self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
            self.stdout.write(self.style.SUCCESS(f'Department: {department}'))
            self.stdout.write(self.style.SUCCESS('This user has been granted:'))
            self.stdout.write(self.style.SUCCESS('- Lab technician privileges (can approve users)'))
            self.stdout.write(self.style.SUCCESS('- Django admin access (is_staff=True)'))
            self.stdout.write(self.style.SUCCESS('- Full superuser permissions (is_superuser=True)'))
            self.stdout.write(self.style.SUCCESS(f'Access the admin interface at: /admin/'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating user: {str(e)}'))
            self.stdout.write(self.style.WARNING('Try running the command with --bypass-validation to skip password validation.'))