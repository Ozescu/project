from django.shortcuts import get_object_or_404, redirect, render
from .models import Sanction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST


@login_required
def my_sanctions(request):
    if request.user.is_administrateur() or request.user.is_bibliothecaire():
        qs = Sanction.objects.select_related('lecteur', 'emprunt').all()
    else:
        qs = Sanction.objects.filter(lecteur=request.user)
    return render(request, 'sanctions/list.html', {'sanctions': qs})


def _can_manage_sanctions(user):
    return user.is_administrateur() or user.is_bibliothecaire()


@login_required
@require_POST
def resolve_sanction(request, pk):
    if not _can_manage_sanctions(request.user):
        messages.error(request, 'Accès refusé.')
        return redirect('sanctions:mine')
    sanction = get_object_or_404(Sanction, pk=pk)
    if sanction.statut != 'active':
        messages.info(request, 'Cette sanction est déjà clôturée.')
        return redirect('sanctions:mine')
    sanction.statut = 'resolue'
    sanction.date_fin = timezone.now()
    sanction.save(update_fields=['statut', 'date_fin'])
    messages.success(request, 'Sanction résolue.')
    return redirect('sanctions:mine')


@login_required
@require_POST
def cancel_sanction(request, pk):
    if not request.user.is_administrateur():
        messages.error(request, 'Action réservée à l administrateur.')
        return redirect('sanctions:mine')
    sanction = get_object_or_404(Sanction, pk=pk)
    if sanction.statut != 'active':
        messages.info(request, 'Cette sanction est déjà clôturée.')
        return redirect('sanctions:mine')
    sanction.statut = 'annulee'
    sanction.date_fin = timezone.now()
    sanction.save(update_fields=['statut', 'date_fin'])
    messages.success(request, 'Sanction annulée.')
    return redirect('sanctions:mine')
