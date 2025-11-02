from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Avg, F, ExpressionWrapper, FloatField
from purchase_inv.models import PurchaseItem
from sale_inv.models import SaleItem
from stock.models import Stock


# -------------------- PURCHASE ITEM --------------------
@receiver(post_save, sender=PurchaseItem)
def update_stock_on_purchase(sender, instance, created, **kwargs):
    stock, _ = Stock.objects.get_or_create(
        product=instance.product,
        company=instance.invoice.company
        )

    # Purchases and sales for this product
    purchase_data = PurchaseItem.objects.filter(product=instance.product, invoice__company=instance.invoice.company).aggregate(
        total_qty=Sum("quantity"),
        avg_price=Avg("unit_price"),
        total_val=Sum(ExpressionWrapper(F("quantity") * F("unit_price"), output_field=FloatField()))
    )
    total_purchased = purchase_data["total_qty"] or 0
    avg_price = purchase_data["avg_price"] or 0
    total_val = purchase_data["total_val"] or 0

    total_sold = SaleItem.objects.filter(
        product=instance.product,
        invoice__company=instance.invoice.company
        ).aggregate(total_qty=Sum("quantity"))["total_qty"] or 0

    stock.quantity = total_purchased - total_sold
    stock.average_price = avg_price
    stock.total_value = total_val
    stock.save()


@receiver(post_delete, sender=PurchaseItem)
def update_stock_on_purchase_delete(sender, instance, **kwargs):
    update_stock_on_purchase(sender, instance, created=False)


# -------------------- SALE ITEM --------------------
@receiver(post_save, sender=SaleItem)
def update_stock_on_sale(sender, instance, created, **kwargs):
    update_stock_on_purchase(sender, instance, created)


@receiver(post_delete, sender=SaleItem)
def update_stock_on_sale_delete(sender, instance, **kwargs):
    update_stock_on_purchase(sender, instance, created=False)
