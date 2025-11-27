# Em formulario_professores/management/commands/create_default_superuser.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Cria um superusuário padrão de forma não-interativa.'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'supersecret123')

        if not User.objects.filter(username=username).exists():
            self.stdout.write(f"Criando superusuário '{username}'...")
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superusuário '{username}' criado com sucesso!"))
        else:
            self.stdout.write(self.style.WARNING(f"Superusuário '{username}' já existe."))