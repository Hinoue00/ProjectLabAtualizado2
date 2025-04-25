from django.core.management.base import BaseCommand
from laboratories.models import Laboratory

class Command(BaseCommand):
    help = 'Corrige os nomes dos departamentos no banco de dados'

    def handle(self, *args, **options):
        departamento_correcoes = {
            'Saude': 'Saúde',
            'Informatica': 'Informática',
            # Adicione outros departamentos se necessário
        }

        self.stdout.write("Departamentos antes da correção:")
        for dept in Laboratory.objects.values_list('department', flat=True).distinct():
            self.stdout.write(f"- {dept}")

        for nome_antigo, nome_novo in departamento_correcoes.items():
            count = Laboratory.objects.filter(department=nome_antigo).count()
            if count > 0:
                self.stdout.write(f"Atualizando {count} laboratório(s) de '{nome_antigo}' para '{nome_novo}'")
                Laboratory.objects.filter(department=nome_antigo).update(department=nome_novo)

        self.stdout.write(self.style.SUCCESS("\nCorreção concluída com sucesso!"))