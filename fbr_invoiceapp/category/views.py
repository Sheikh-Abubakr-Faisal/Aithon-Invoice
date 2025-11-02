from django.shortcuts import render
from .models import Category
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, get_object_or_404
from product.models import Product

@login_required(login_url='sign_in')
def category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        category_desc = request.POST.get('category_desc')

        try:
            category = Category.objects.create(
                company=request.user.company,
                name=category_name,
                description=category_desc,
            )
            if category:
                messages.warning(request, f'Category "{category.name}" created successfully.')
                return redirect('category')
        except IntegrityError:
            messages.error(request, f"Category '{category_name}' already exists!")
            return redirect('category')
        except Exception as e:
            messages.error(request, f"Something went wrong: {e}")
            return redirect('category')
            

    categories = Category.objects.filter(company=request.user.company)

    # search filter
    search = request.GET.get('search')
    if search:
        categories = categories.filter(name__icontains=search)

    context = {
        'categories': categories,
        'title': "Category Management"
    }

    return render(request, 'category.html', context)


@login_required(login_url='sign_in')
def del_category(request, id):
    category = get_object_or_404(Category, id=id, company=request.user.company)
    assigned_products = Product.objects.filter(category=category)
    if assigned_products.exists():
        messages.error(
            request,
            f'Category "{category.name}" is assigned to {assigned_products.count()} product(s). '
            'Please delete or reassign those products before deleting this category.'
        )
        return redirect('category')
    category.delete()
    messages.success(request, f'Category "{category.name}" deleted successfully.')
    return redirect('category')

@login_required(login_url='sign_in')
def update_category(request, id):
    category = get_object_or_404(Category, id=id, company=request.user.company)
    if request.method == 'POST':
        category.name = request.POST.get('category_name')
        category.description = request.POST.get('category_desc')
        category.save()

        messages.success(request, f'Category "{category.name}" updated successfully.')
        return redirect('category')
    
    return render(request, 'category.html', {'category': category, 'title': 'Update Category'})
