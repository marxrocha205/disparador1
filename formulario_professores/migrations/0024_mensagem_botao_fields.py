# Generated migration for button fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formulario_professores', '0023_midia_mimetype'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensagem',
            name='incluir_botao',
            field=models.BooleanField(default=False, verbose_name='Incluir Botão com Link'),
        ),
        migrations.AddField(
            model_name='mensagem',
            name='botao_texto',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Texto do Botão'),
        ),
        migrations.AddField(
            model_name='mensagem',
            name='botao_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='URL do Botão'),
        ),
    ]
