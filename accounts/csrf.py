from django.contrib import messages
from django.middleware.csrf import get_token
from django.shortcuts import redirect


def csrf_failure(request, reason=''):
    get_token(request)
    if request.path.startswith('/accounts/login/'):
        messages.error(request, 'Session de connexion expiree. Rechargez le formulaire puis reconnectez-vous.')
        return redirect('accounts:login')
    if request.path.startswith('/accounts/register/'):
        messages.error(request, 'Session d inscription expiree. Rechargez le formulaire puis reessayez.')
        return redirect('accounts:register')
    messages.error(request, 'Session expiree. Rechargez la page puis reessayez.')
    return redirect('landing')
