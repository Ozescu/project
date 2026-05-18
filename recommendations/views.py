from django.db import models
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from catalogue.models import Favorite, Ouvrage, Exemplaire
from loans.models import Emprunt


def _popular_available_books(limit=6):
    return (
        Ouvrage.objects
        .filter(exemplaires__status=Exemplaire.STATUS_DISP)
        .annotate(total_loans=models.Count('exemplaires__emprunt', distinct=True))
        .order_by('-total_loans', 'titre')
        .distinct()[:limit]
    )


@login_required
def recommendations_view(request):
    user = request.user
    favorite_categories = Favorite.objects.filter(lecteur=user).values_list('ouvrage__categorie_id', flat=True)
    history_categories = Emprunt.objects.filter(lecteur=user).values_list('exemplaire__ouvrage__categorie_id', flat=True)
    borrowed_ids = Emprunt.objects.filter(lecteur=user).values_list('exemplaire__ouvrage_id', flat=True)

    ouvrages = (
        Ouvrage.objects
        .filter(models.Q(categorie_id__in=favorite_categories) | models.Q(categorie_id__in=history_categories))
        .filter(exemplaires__status=Exemplaire.STATUS_DISP)
        .exclude(id__in=borrowed_ids)
        .annotate(total_loans=models.Count('exemplaires__emprunt', distinct=True))
        .order_by('-total_loans', 'titre')
        .distinct()[:6]
    )
    if not ouvrages:
        ouvrages = _popular_available_books(limit=6)

    return render(request, 'recommendations/list.html', {'ouvrages': ouvrages})
