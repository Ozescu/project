from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import Ouvrage, Categorie, Exemplaire, Favorite
from .forms import CategorieForm, OuvrageForm, ExemplaireForm
from loans.models import Emprunt, LoanRequest
from reservations.models import Reservation


def has_catalogue_permission(user):
    return user.is_authenticated and (user.is_administrateur() or user.is_bibliothecaire())


def list_view(request):
    qs = Ouvrage.objects.select_related('categorie').annotate(
        total=Count('exemplaires', distinct=True),
        available_count=Count('exemplaires', filter=Q(exemplaires__status=Exemplaire.STATUS_DISP), distinct=True),
    ).order_by('titre')
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(auteur__icontains=q) | Q(isbn__icontains=q) | Q(sujet__icontains=q) | Q(categorie__nom__icontains=q))
    cat = request.GET.get('categorie')
    if cat:
        qs = qs.filter(categorie__id=cat)
    dispo = request.GET.get('disponible')
    if dispo == '1':
        qs = qs.filter(exemplaires__status=Exemplaire.STATUS_DISP)
    status = request.GET.get('status')
    if status:
        qs = qs.filter(exemplaires__status=status)
    qs = qs.distinct()
    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    ouvrages = paginator.get_page(page)
    categories = Categorie.objects.all()
    fav_ids = []
    reservation_ids = []
    request_ids = []
    loan_ids = []
    if request.user.is_authenticated:
        fav_ids = list(Favorite.objects.filter(lecteur=request.user).values_list('ouvrage_id', flat=True))
        reservation_ids = list(Reservation.objects.filter(lecteur=request.user, statut=Reservation.STATUS_ACTIVE).values_list('ouvrage_id', flat=True))
        request_ids = list(LoanRequest.objects.filter(lecteur=request.user, statut=LoanRequest.STATUS_PENDING).values_list('ouvrage_id', flat=True))
        loan_ids = list(Emprunt.objects.filter(
            lecteur=request.user,
            statut=Emprunt.STAT_EN_COURS,
            date_retour_effective__isnull=True,
        ).values_list('exemplaire__ouvrage_id', flat=True))
    return render(request, 'catalogue/list.html', {
        'ouvrages': ouvrages,
        'page_obj': ouvrages,
        'is_paginated': ouvrages.has_other_pages(),
        'categories': categories,
        'status_choices': Exemplaire.STATUS_CHOICES,
        'can_manage': has_catalogue_permission(request.user),
        'fav_ids': fav_ids,
        'reservation_ids': reservation_ids,
        'request_ids': request_ids,
        'loan_ids': loan_ids,
    })


def detail_view(request, pk):
    ouvrage = get_object_or_404(Ouvrage, pk=pk)
    exemplaires = ouvrage.exemplaires.all()
    total = exemplaires.count()
    disponibles = exemplaires.filter(status=Exemplaire.STATUS_DISP).count()
    can_manage = has_catalogue_permission(request.user)
    is_fav = False
    if request.user.is_authenticated:
        is_fav = Favorite.objects.filter(lecteur=request.user, ouvrage=ouvrage).exists()
    has_active_reservation = request.user.is_authenticated and Reservation.objects.filter(
        lecteur=request.user,
        ouvrage=ouvrage,
        statut=Reservation.STATUS_ACTIVE,
    ).exists()
    has_active_request = request.user.is_authenticated and LoanRequest.objects.filter(
        lecteur=request.user,
        ouvrage=ouvrage,
        statut=LoanRequest.STATUS_PENDING,
    ).exists()
    has_active_loan = request.user.is_authenticated and Emprunt.objects.filter(
        lecteur=request.user,
        exemplaire__ouvrage=ouvrage,
        statut=Emprunt.STAT_EN_COURS,
        date_retour_effective__isnull=True,
    ).exists()
    similar_books = Ouvrage.objects.filter(
        Q(categorie=ouvrage.categorie) | Q(auteur__iexact=ouvrage.auteur)
    ).exclude(pk=ouvrage.pk).distinct()[:4]
    recommended_books = similar_books
    if request.user.is_authenticated:
        fav_categories = Favorite.objects.filter(lecteur=request.user).values_list('ouvrage__categorie_id', flat=True)
        history_categories = Emprunt.objects.filter(lecteur=request.user).values_list('exemplaire__ouvrage__categorie_id', flat=True)
        recommended_books = Ouvrage.objects.filter(
            Q(categorie_id__in=fav_categories) | Q(categorie_id__in=history_categories)
        ).exclude(pk=ouvrage.pk).distinct()[:4] or similar_books
    return render(request, 'catalogue/detail.html', {
        'ouvrage': ouvrage,
        'exemplaires': exemplaires,
        'total': total,
        'disponibles': disponibles,
        'can_manage': can_manage,
        'is_fav': is_fav,
        'has_active_reservation': has_active_reservation,
        'has_active_request': has_active_request,
        'has_active_loan': has_active_loan,
        'similar_books': similar_books,
        'recommended_books': recommended_books,
    })


@login_required
def favorite_toggle(request, pk):
    ouvrage = get_object_or_404(Ouvrage, pk=pk)
    user = request.user
    if not user.is_lecteur():
        messages.error(request, 'Action réservée aux lecteurs.')
        return redirect('catalogue:detail', pk=pk)
    if user.statut_compte != user.STATUT_ACTIF or user.is_suspended:
        messages.error(request, 'Votre compte est suspendu ou bloque.')
        return redirect('catalogue:detail', pk=pk)
    if request.method != 'POST':
        return redirect('catalogue:detail', pk=pk)

    fav = Favorite.objects.filter(lecteur=user, ouvrage=ouvrage).first()
    if fav:
        fav.delete()
        messages.success(request, 'Retiré des favoris.')
    else:
        Favorite.objects.get_or_create(lecteur=user, ouvrage=ouvrage)
        messages.success(request, 'Ajouté aux favoris.')
    return redirect(request.META.get('HTTP_REFERER', 'catalogue:detail'))


@login_required
def favorites_list(request):
    if not request.user.is_lecteur():
        messages.error(request, 'Les favoris sont réservés aux lecteurs.')
        return redirect('catalogue:list')
    qs = Favorite.objects.filter(lecteur=request.user).select_related('ouvrage')
    ouvrages = [f.ouvrage for f in qs]
    return render(request, 'catalogue/favorites.html', {'ouvrages': ouvrages})


@login_required
def category_list(request):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    categories = Categorie.objects.annotate(books_count=Count('ouvrage')).order_by('nom')
    return render(request, 'catalogue/category_list.html', {'categories': categories})


@login_required
def category_form(request, pk=None):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    category = get_object_or_404(Categorie, pk=pk) if pk else None
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Catégorie enregistrée.')
            return redirect('catalogue:category_list')
    else:
        form = CategorieForm(instance=category)
    return render(request, 'catalogue/category_form.html', {'form': form, 'category': category})


@login_required
def category_delete(request, pk):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    category = get_object_or_404(Categorie, pk=pk)
    if Ouvrage.objects.filter(categorie=category).exists():
        messages.error(request, 'Impossible de supprimer une catégorie encore utilisée par des ouvrages.')
        return redirect('catalogue:category_list')
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Catégorie supprimée.')
        return redirect('catalogue:category_list')
    return render(request, 'generic/confirm_delete.html', {'title': 'Supprimer catégorie', 'message': 'Voulez-vous vraiment supprimer cette catégorie ?', 'cancel_url': request.META.get('HTTP_REFERER', '/catalogue/categories/')})


@login_required
def ouvrage_form(request, pk=None):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    ouvrage = get_object_or_404(Ouvrage, pk=pk) if pk else None
    if request.method == 'POST':
        form = OuvrageForm(request.POST, request.FILES, instance=ouvrage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ouvrage enregistré.')
            return redirect('catalogue:list')
    else:
        form = OuvrageForm(instance=ouvrage)
    return render(request, 'catalogue/ouvrage_form.html', {'form': form, 'ouvrage': ouvrage})


@login_required
def ouvrage_delete(request, pk):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    ouvrage = get_object_or_404(Ouvrage, pk=pk)
    if Emprunt.objects.filter(exemplaire__ouvrage=ouvrage, statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD], date_retour_effective__isnull=True).exists():
        messages.error(request, 'Impossible de supprimer un ouvrage avec des emprunts actifs.')
        return redirect('catalogue:detail', pk=pk)
    if request.method == 'POST':
        ouvrage.delete()
        messages.success(request, 'Ouvrage supprimé.')
        return redirect('catalogue:list')
    return render(request, 'generic/confirm_delete.html', {'title': 'Supprimer ouvrage', 'message': 'Voulez-vous vraiment supprimer cet ouvrage ?', 'cancel_url': request.META.get('HTTP_REFERER', '/catalogue/')})


@login_required
def exemplaire_form(request, pk=None, ouvrage_pk=None):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    exemplaire = get_object_or_404(Exemplaire, pk=pk) if pk else None
    if request.method == 'POST':
        form = ExemplaireForm(request.POST, instance=exemplaire)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exemplaire enregistré.')
            return redirect('catalogue:detail', pk=form.instance.ouvrage.pk)
    else:
        form = ExemplaireForm(instance=exemplaire)
        if ouvrage_pk:
            form.fields['ouvrage'].initial = get_object_or_404(Ouvrage, pk=ouvrage_pk)
    return render(request, 'catalogue/exemplaire_form.html', {'form': form, 'exemplaire': exemplaire})


@login_required
def exemplaire_delete(request, pk):
    if not has_catalogue_permission(request.user):
        messages.error(request, 'Accès refusé')
        return redirect('catalogue:list')
    exemplaire = get_object_or_404(Exemplaire, pk=pk)
    if Emprunt.objects.filter(exemplaire=exemplaire, statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD], date_retour_effective__isnull=True).exists():
        messages.error(request, 'Impossible de supprimer un exemplaire en prêt actif.')
        return redirect('catalogue:detail', pk=exemplaire.ouvrage.pk)
    if request.method == 'POST':
        ouvrage_pk = exemplaire.ouvrage.pk
        exemplaire.delete()
        messages.success(request, 'Exemplaire supprimé.')
        return redirect('catalogue:detail', pk=ouvrage_pk)
    return render(request, 'generic/confirm_delete.html', {'title': 'Supprimer exemplaire', 'message': 'Voulez-vous vraiment supprimer cet exemplaire ?', 'cancel_url': request.META.get('HTTP_REFERER', f'/catalogue/{exemplaire.ouvrage.pk}/')})
