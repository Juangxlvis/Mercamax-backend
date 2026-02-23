from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AjusteInventario

@receiver(post_save, sender=AjusteInventario)
def aplicar_ajuste_inventario(sender, instance, created, **kwargs):
    """
    Cuando se crea un registro de AjusteInventario, actualizamos
    automáticamente la cantidad en el StockItem correspondiente.
    """
    if created:
        stock_item = instance.stock_item
        # Actualizamos la cantidad física en el estante
        stock_item.cantidad = instance.cantidad_nueva
        stock_item.save()