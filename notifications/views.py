from django.shortcuts import get_object_or_404, redirect, render
from .models import Notification
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST


@login_required
def my_notifications(request):
    if request.user.is_administrateur() or request.user.is_bibliothecaire():
        qs = Notification.objects.select_related('lecteur', 'ouvrage').all()
    else:
        qs = Notification.objects.filter(lecteur=request.user).select_related('ouvrage')
    return render(request, 'notifications/list.html', {'notifications': qs})


@login_required
@require_POST
def mark_read(request, pk):
    qs = Notification.objects.all()
    if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
        qs = qs.filter(lecteur=request.user)
    notification = get_object_or_404(qs, pk=pk)
    notification.lu = True
    notification.save(update_fields=['lu'])
    messages.success(request, 'Notification marquée comme lue.')
    return redirect('notifications:mine')


@login_required
@require_POST
def mark_all_read(request):
    qs = Notification.objects.all()
    if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
        qs = qs.filter(lecteur=request.user)
    updated = qs.filter(lu=False).update(lu=True)
    messages.success(request, f'{updated} notification(s) marquée(s) comme lues.')
    return redirect('notifications:mine')
