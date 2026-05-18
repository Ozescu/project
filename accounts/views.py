from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from .forms import ProfileForm, RegisterForm, UserForm
from catalogue.models import Favorite
from loans.models import Emprunt
from reservations.models import Reservation
from sanctions.models import Sanction

User = get_user_model()


def add_auth_no_store_headers(response):
    response['Cache-Control'] = 'no-store, no-cache, max-age=0, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response.headers.setdefault('Vary', 'Cookie')
    return response


@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AppLoginView(LoginView):
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return add_auth_no_store_headers(response)

    def form_valid(self, form):
        user = form.get_user()
        if user.statut_compte != User.STATUT_ACTIF or user.is_suspended:
            messages.error(self.request, 'Votre compte est suspendu ou bloque.')
            return redirect('accounts:login')
        response = super().form_valid(form)
        if self.get_redirect_url():
            return response
        if user.is_administrateur():
            return redirect('dashboard:admin')
        if user.is_bibliothecaire():
            return redirect('dashboard:biblio')
        return redirect('dashboard:reader')


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AppLogoutView(LogoutView):
    next_page = '/'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return add_auth_no_store_headers(response)


@ensure_csrf_cookie
@csrf_protect
@never_cache
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte cree avec succes.')
            return redirect('dashboard:reader')
    else:
        form = RegisterForm()
    response = render(request, 'accounts/register.html', {'form': form})
    return add_auth_no_store_headers(response)


@login_required
def profile(request):
    context = {}
    if request.user.is_lecteur():
        context = {
            'active_loans_count': Emprunt.objects.filter(
                lecteur=request.user,
                statut=Emprunt.STAT_EN_COURS,
                date_retour_effective__isnull=True,
            ).count(),
            'reservations_count': Reservation.objects.filter(lecteur=request.user).count(),
            'favorites_count': Favorite.objects.filter(lecteur=request.user).count(),
            'active_sanctions_count': Sanction.objects.filter(lecteur=request.user, statut='active').count(),
        }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil modifie avec succes.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile_form.html', {'form': form})


@login_required
def user_list(request):
    if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
        messages.error(request, 'Acces refuse')
        return redirect('dashboard:reader')

    users = User.objects.all().order_by('username')
    if request.user.is_bibliothecaire():
        users = users.filter(role=User.ROLE_LECTEUR)

    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    role = request.GET.get('role')
    if role and request.user.is_administrateur():
        users = users.filter(role=role)
    statut = request.GET.get('statut')
    if statut:
        users = users.filter(statut_compte=statut)

    return render(request, 'accounts/user_list.html', {
        'users': users,
        'can_manage_users': request.user.is_administrateur(),
        'reader_only_mode': request.user.is_bibliothecaire(),
    })


@login_required
def user_detail(request, pk):
    if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
        messages.error(request, 'Acces refuse')
        return redirect('dashboard:reader')
    user_obj = get_object_or_404(User, pk=pk)
    if request.user.is_bibliothecaire() and not user_obj.is_lecteur():
        messages.error(request, 'Acces refuse')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_detail.html', {'user_obj': user_obj})


@login_required
def user_form(request, pk=None):
    if not request.user.is_administrateur():
        messages.error(request, 'Acces reserve a l administrateur.')
        return redirect('accounts:user_list')

    user_obj = get_object_or_404(User, pk=pk) if pk else None
    requested_role = request.GET.get('role')
    role_values = [choice[0] for choice in User.ROLE_CHOICES]
    initial = {}
    if not user_obj and requested_role in role_values:
        initial['role'] = requested_role

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            if user_obj == request.user and (
                form.cleaned_data.get('role') != User.ROLE_ADMIN
                or form.cleaned_data.get('statut_compte') != User.STATUT_ACTIF
                or form.cleaned_data.get('is_suspended')
            ):
                form.add_error(None, 'Vous ne pouvez pas retirer votre propre acces administrateur ni suspendre votre compte.')
            else:
                saved_user = form.save()
                messages.success(request, 'Utilisateur enregistre avec succes.')
                if saved_user.role == User.ROLE_BIBLIO:
                    return redirect(f"{reverse('accounts:user_list')}?role={User.ROLE_BIBLIO}")
                return redirect('accounts:user_list')
    else:
        form = UserForm(instance=user_obj, initial=initial)
    return render(request, 'accounts/user_form.html', {'form': form, 'user_obj': user_obj})


@login_required
def user_delete(request, pk):
    if not request.user.is_administrateur():
        messages.error(request, 'Acces reserve a l administrateur.')
        return redirect('accounts:user_list')

    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte administrateur.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'Utilisateur supprime.')
        return redirect('accounts:user_list')
    return render(request, 'generic/confirm_delete.html', {
        'title': 'Supprimer utilisateur',
        'message': 'Voulez-vous vraiment supprimer cet utilisateur ?',
        'cancel_url': request.META.get('HTTP_REFERER', '/accounts/users/'),
    })


@login_required
def user_toggle_status(request, pk):
    if not request.user.is_administrateur():
        messages.error(request, 'Acces reserve a l administrateur.')
        return redirect('accounts:user_list')

    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, 'Vous ne pouvez pas suspendre ou désactiver votre propre compte.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        if user_obj.statut_compte == User.STATUT_ACTIF:
            user_obj.statut_compte = User.STATUT_SUSPENDU
            user_obj.is_suspended = True
            messages.success(request, 'Compte suspendu.')
        else:
            user_obj.statut_compte = User.STATUT_ACTIF
            user_obj.is_suspended = False
            messages.success(request, 'Compte reactive.')
        user_obj.save()
        return redirect('accounts:user_list')
    return render(request, 'generic/confirm_delete.html', {
        'title': 'Modifier statut',
        'message': 'Confirmez-vous le changement de statut de ce compte ?',
        'cancel_url': request.META.get('HTTP_REFERER', '/accounts/users/'),
    })
