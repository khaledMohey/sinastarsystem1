from django.apps import AppConfig

from django import template
register = template.Library()


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        import main.signals  # مش yourapp — خليه اسم التطبيق الحقيقي


@register.filter
def zip(value, arg):
    return zip(value, arg)
