from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from accounts.models import User
from catalogue.models import Categorie, Ouvrage, Exemplaire, Favorite
from loans.models import Emprunt, LoanRequest
from loans.services import refresh_overdue_loans
from reservations.models import Reservation
from sanctions.models import Sanction
from notifications.models import Notification


def landing_view(request):
    if request.user.is_authenticated:
        if request.user.is_administrateur():
            return redirect('dashboard:admin')
        if request.user.is_bibliothecaire():
            return redirect('dashboard:biblio')
        return redirect('dashboard:reader')
    return render(request, 'landing.html')


@login_required
def admin_dashboard(request):
    if not request.user.is_administrateur():
        return render(request, 'dashboard/forbidden.html')

    refresh_overdue_loans()
    now = timezone.now()
    today = timezone.localdate()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    active_loan_filter = {
        'statut__in': [Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
        'date_retour_effective__isnull': True,
    }

    active_loans_qs = Emprunt.objects.filter(**active_loan_filter).select_related('exemplaire__ouvrage', 'lecteur')
    late_loans = active_loans_qs.filter(date_retour_prevue__lt=now)
    returns_to_confirm_qs = active_loans_qs.filter(date_retour_prevue__date__lte=today)
    reservations_active_qs = Reservation.objects.filter(statut=Reservation.STATUS_ACTIVE).select_related('ouvrage', 'lecteur')
    pending_requests_qs = LoanRequest.objects.filter(statut=LoanRequest.STATUS_PENDING).select_related('ouvrage', 'lecteur')
    unavailable_copies_qs = Exemplaire.objects.exclude(status=Exemplaire.STATUS_DISP).select_related('ouvrage')
    maintenance_copies_qs = Exemplaire.objects.filter(status__in=[Exemplaire.STATUS_MAINT, Exemplaire.STATUS_LOST]).select_related('ouvrage')
    important_sanctions_qs = Sanction.objects.filter(statut='active').select_related('lecteur', 'emprunt')

    popular_books = Ouvrage.objects.annotate(
        total_loans=Count('exemplaires__emprunt', distinct=True)
    ).order_by('-total_loans', 'titre')[:3]
    favorite_books = Ouvrage.objects.annotate(
        favorites_count=Count('favorited_by', distinct=True)
    ).order_by('-favorites_count', 'titre')[:3]
    recommended_books = (
        Ouvrage.objects.annotate(
            total_loans=Count('exemplaires__emprunt', distinct=True),
            favorites_count=Count('favorited_by', distinct=True),
        )
        .annotate(recommendation_score=F('total_loans') + F('favorites_count'))
        .filter(recommendation_score__gt=0)
        .order_by('-recommendation_score', '-total_loans', '-favorites_count', 'titre')[:3]
    )
    trending_categories = Categorie.objects.annotate(
        total_loans=Count('ouvrage__exemplaires__emprunt', distinct=True)
    ).order_by('-total_loans', 'nom')[:3]

    unread_notifications_count = Notification.objects.filter(lu=False).count()
    active_sanctions_count = important_sanctions_qs.count()
    total_fines = important_sanctions_qs.aggregate(total=Sum('montant'))['total'] or 0
    overdue_readers_count = late_loans.values('lecteur').distinct().count()

    recent_loans = list(Emprunt.objects.select_related('exemplaire__ouvrage', 'lecteur').order_by('-date_emprunt')[:5])
    recent_reservations = list(Reservation.objects.select_related('ouvrage', 'lecteur').order_by('-date_reservation')[:5])
    recent_notifications = list(Notification.objects.order_by('-date_envoi')[:5])
    recent_system_activity = sorted(
        [
            {
                'type': 'Emprunt',
                'label': loan.exemplaire.ouvrage.titre,
                'detail': f"{loan.lecteur.username} - {loan.date_emprunt.strftime('%d/%m/%Y')}",
                'date': loan.date_emprunt,
            }
            for loan in recent_loans
        ]
        + [
            {
                'type': 'Réservation',
                'label': reservation.ouvrage.titre,
                'detail': f"{reservation.lecteur.username} - {reservation.date_reservation.strftime('%d/%m/%Y')}",
                'date': reservation.date_reservation,
            }
            for reservation in recent_reservations
        ]
        + [
            {
                'type': 'Notification',
                'label': notification.get_type_notification_display(),
                'detail': notification.message[:80],
                'date': notification.date_envoi,
            }
            for notification in recent_notifications
        ],
        key=lambda item: item['date'],
        reverse=True,
    )[:5]

    loan_months = list(
        Emprunt.objects.annotate(month=TruncMonth('date_emprunt'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('-month')[:6]
    )
    loan_months.reverse()
    max_month_loans = max([row['total'] for row in loan_months] or [1])
    loan_month_chart = [
        {
            'label': row['month'].strftime('%b %Y') if row['month'] else '-',
            'total': row['total'],
            'percent': int((row['total'] / max_month_loans) * 100) if max_month_loans else 0,
        }
        for row in loan_months
    ]

    copy_status_raw = list(Exemplaire.objects.values('status').annotate(total=Count('id')).order_by('-total'))
    max_copy_status = max([row['total'] for row in copy_status_raw] or [1])
    copy_status_chart = [
        {
            'label': dict(Exemplaire.STATUS_CHOICES).get(row['status'], row['status']),
            'total': row['total'],
            'percent': int((row['total'] / max_copy_status) * 100) if max_copy_status else 0,
        }
        for row in copy_status_raw
    ]

    role_raw = list(User.objects.values('role').annotate(total=Count('id')).order_by('role'))
    max_role = max([row['total'] for row in role_raw] or [1])
    role_chart = [
        {
            'label': dict(User.ROLE_CHOICES).get(row['role'], row['role']),
            'total': row['total'],
            'percent': int((row['total'] / max_role) * 100) if max_role else 0,
        }
        for row in role_raw
    ]

    monthly_stats = [
        {'label': 'Emprunts ce mois', 'value': Emprunt.objects.filter(date_emprunt__gte=month_start).count()},
        {'label': 'Retours ce mois', 'value': Emprunt.objects.filter(date_retour_effective__gte=month_start).count()},
        {'label': 'Réservations ce mois', 'value': Reservation.objects.filter(date_reservation__gte=month_start).count()},
        {'label': 'Notifications ce mois', 'value': Notification.objects.filter(date_envoi__gte=month_start).count()},
    ]
    admin_alerts = [
        {'label': 'Lecteurs en retard', 'count': overdue_readers_count, 'status': 'danger', 'url': 'loans:list'},
        {'label': 'Réservations en attente', 'count': reservations_active_qs.count(), 'status': 'warning', 'url': 'reservations:my_reservations'},
        {'label': 'Demandes emprunt', 'count': pending_requests_qs.count(), 'status': 'warning', 'url': 'loans:requests'},
        {'label': 'Retours à confirmer', 'count': returns_to_confirm_qs.count(), 'status': 'danger', 'url': 'loans:list'},
        {'label': 'Maintenance exemplaires', 'count': maintenance_copies_qs.count(), 'status': 'neutral', 'url': 'catalogue:list'},
        {'label': 'Sanctions importantes', 'count': active_sanctions_count, 'status': 'warning', 'url': 'sanctions:mine'},
    ]
    quick_actions = [
        {'label': 'Ajouter ouvrage', 'url': 'catalogue:ouvrage_add', 'variant': ''},
        {'label': 'Ajouter utilisateur', 'url': 'accounts:user_add', 'variant': 'secondary'},
        {'label': 'Créer emprunt', 'url': 'loans:create', 'variant': 'secondary'},
        {'label': 'Gérer catégories', 'url': 'catalogue:category_list', 'variant': 'secondary'},
    ]
    administration_links = [
        {'label': 'Utilisateurs', 'detail': 'Comptes et suspensions', 'url': 'accounts:user_list'},
        {'label': 'Rôles', 'detail': 'Lecteurs, bibliothécaires et admins', 'url': 'accounts:user_list'},
        {'label': 'Permissions', 'detail': 'Matrice des droits', 'url': 'dashboard:permissions'},
        {'label': 'Notifications', 'detail': 'Types et alertes', 'url': 'dashboard:notification_settings'},
        {'label': 'Sanctions', 'detail': 'Amendes et blocages', 'url': 'dashboard:sanction_settings'},
        {'label': 'Rapports', 'detail': 'Synthèse système', 'url': 'dashboard:system_reports'},
    ]

    context = {
        'users_count': User.objects.count(),
        'lecteurs_count': User.objects.filter(role=User.ROLE_LECTEUR).count(),
        'biblio_count': User.objects.filter(role=User.ROLE_BIBLIO).count(),
        'admins_count': User.objects.filter(role=User.ROLE_ADMIN).count(),
        'ouvrages_count': Ouvrage.objects.count(),
        'exemplaires_count': Exemplaire.objects.count(),
        'available_copies_count': Exemplaire.objects.filter(status=Exemplaire.STATUS_DISP).count(),
        'active_loans': active_loans_qs.count(),
        'reservations': reservations_active_qs.count(),
        'pending_requests_count': pending_requests_qs.count(),
        'active_sanctions_count': active_sanctions_count,
        'total_fines': total_fines,
        'notifications': Notification.objects.count(),
        'important_notifications_count': unread_notifications_count,
        'late_loans_count': late_loans.count(),
        'overdue_readers_count': overdue_readers_count,
        'maintenance_count': maintenance_copies_qs.count(),
        'unavailable_copies_count': unavailable_copies_qs.count(),
        'returns_to_confirm_count': returns_to_confirm_qs.count(),
        'loan_months': loan_month_chart,
        'monthly_stats': monthly_stats,
        'copy_status_chart': copy_status_chart,
        'role_chart': role_chart,
        'popular_books': popular_books,
        'favorite_books': favorite_books,
        'recommended_books': recommended_books,
        'trending_categories': trending_categories,
        'recommendation_signals': Emprunt.objects.count() + Favorite.objects.count(),
        'recent_system_activity': recent_system_activity,
        'late_loans': late_loans[:4],
        'pending_requests': pending_requests_qs[:4],
        'active_reservations': reservations_active_qs[:4],
        'unavailable_copies': unavailable_copies_qs[:4],
        'maintenance_copies': maintenance_copies_qs[:4],
        'returns_to_confirm': returns_to_confirm_qs[:4],
        'important_sanctions': important_sanctions_qs[:4],
        'admin_alerts': admin_alerts,
        'quick_actions': quick_actions,
        'administration_links': administration_links,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def notification_settings(request):
    if not request.user.is_administrateur():
        return render(request, 'dashboard/forbidden.html')
    type_stats = Notification.objects.values('type_notification').annotate(total=Count('id')).order_by('-total')
    context = {
        'title': 'Paramètres notifications',
        'description': 'Vue de contrôle des types de notifications utilisés par le système.',
        'type_stats': type_stats,
        'unread_count': Notification.objects.filter(lu=False).count(),
        'total_count': Notification.objects.count(),
    }
    return render(request, 'dashboard/notification_settings.html', context)


@login_required
def sanction_settings(request):
    if not request.user.is_administrateur():
        return render(request, 'dashboard/forbidden.html')
    type_stats = Sanction.objects.values('type_sanction').annotate(total=Count('id'), amount=Sum('montant')).order_by('-total')
    context = {
        'title': 'Paramètres sanctions',
        'description': 'Synthèse des sanctions et amendes appliquées aux lecteurs.',
        'type_stats': type_stats,
        'active_count': Sanction.objects.filter(statut='active').count(),
        'total_amount': Sanction.objects.aggregate(total=Sum('montant'))['total'] or 0,
    }
    return render(request, 'dashboard/sanction_settings.html', context)


@login_required
def system_reports(request):
    if not request.user.is_administrateur():
        return render(request, 'dashboard/forbidden.html')
    refresh_overdue_loans()
    context = {
        'title': 'Rapports système',
        'description': 'Indicateurs consolidés pour vérifier la santé opérationnelle.',
        'total_users': User.objects.count(),
        'total_books': Ouvrage.objects.count(),
        'total_copies': Exemplaire.objects.count(),
        'active_loans': Emprunt.objects.filter(statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD], date_retour_effective__isnull=True).count(),
        'returned_loans': Emprunt.objects.filter(statut=Emprunt.STAT_RET).count(),
        'active_reservations': Reservation.objects.filter(statut=Reservation.STATUS_ACTIVE).count(),
        'pending_requests': LoanRequest.objects.filter(statut=LoanRequest.STATUS_PENDING).count(),
        'active_sanctions': Sanction.objects.filter(statut='active').count(),
        'unread_notifications': Notification.objects.filter(lu=False).count(),
    }
    return render(request, 'dashboard/system_reports.html', context)


@login_required
def biblio_dashboard(request):
    if not request.user.is_bibliothecaire():
        return render(request, 'dashboard/forbidden.html')
    refresh_overdue_loans()
    late_loans = Emprunt.objects.filter(
        statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
        date_retour_effective__isnull=True,
        date_retour_prevue__lt=timezone.now(),
    ).select_related('exemplaire__ouvrage', 'lecteur')
    today = timezone.localdate()
    due_today_loans = Emprunt.objects.filter(
        statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
        date_retour_effective__isnull=True,
        date_retour_prevue__date=today,
    ).select_related('exemplaire__ouvrage', 'lecteur')
    pending_requests = LoanRequest.objects.filter(statut=LoanRequest.STATUS_PENDING).select_related('ouvrage', 'lecteur').order_by('-date_demande')[:5]
    recent_notifications = Notification.objects.select_related('lecteur').order_by('-date_envoi')[:5]
    reservation_actions = Reservation.objects.filter(statut=Reservation.STATUS_ACTIVE).select_related('ouvrage', 'lecteur').order_by('date_reservation')[:5]
    recent_loans = Emprunt.objects.select_related('exemplaire__ouvrage', 'lecteur').order_by('-date_emprunt')[:5]
    overdue_readers = []
    for loan in late_loans[:5]:
        sanction = Sanction.objects.filter(emprunt=loan).first()
        overdue_readers.append({
            'loan': loan,
            'sanction': sanction,
        })
    reservation_actions_data = []
    for reservation in reservation_actions:
        related_loan = Emprunt.objects.filter(
            statut=Emprunt.STAT_EN_COURS,
            exemplaire__ouvrage=reservation.ouvrage,
            lecteur=reservation.lecteur,
        ).select_related('exemplaire__ouvrage').first()
        reservation_actions_data.append({
            'reservation': reservation,
            'related_loan': related_loan,
        })
    context = {
        'ouvrages_count': Ouvrage.objects.count(),
        'exemplaires_count': Exemplaire.objects.count(),
        'available_copies': Exemplaire.objects.filter(status=Exemplaire.STATUS_DISP).count(),
        'total_loans': Emprunt.objects.count(),
        'active_loans': Emprunt.objects.filter(statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD], date_retour_effective__isnull=True).count(),
        'returned_loans': Emprunt.objects.filter(statut=Emprunt.STAT_RET).count(),
        'overdue_loans': Emprunt.objects.filter(
            statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
            date_retour_effective__isnull=True,
            date_retour_prevue__lt=timezone.now(),
        ).count(),
        'reservations': Reservation.objects.filter(statut=Reservation.STATUS_ACTIVE).count(),
        'late_loans_count': late_loans.count(),
        'readers_count': User.objects.filter(role=User.ROLE_LECTEUR).count(),
        'recent_loans': recent_loans,
        'recent_reservations': reservation_actions_data,
        'late_loans': late_loans[:5],
        'due_today_loans': due_today_loans,
        'pending_requests_count': LoanRequest.objects.filter(statut=LoanRequest.STATUS_PENDING).count(),
        'pending_requests': pending_requests,
        'recent_notifications': recent_notifications,
        'overdue_readers': overdue_readers,
        'important_notifications_count': Notification.objects.count(),
        'due_today_count': due_today_loans.count(),
        'open_statuses': [Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
    }
    return render(request, 'dashboard/biblio_dashboard.html', context)


@login_required
def reader_dashboard(request):
    if not request.user.is_lecteur():
        if request.user.is_administrateur():
            return redirect('dashboard:admin')
        if request.user.is_bibliothecaire():
            return redirect('dashboard:biblio')

    user = request.user
    refresh_overdue_loans()
    loans = Emprunt.objects.filter(lecteur=user).select_related('exemplaire__ouvrage').order_by('-date_emprunt')
    active_loans = loans.filter(statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD], date_retour_effective__isnull=True)
    favorite_ids = Favorite.objects.filter(lecteur=user).values_list('ouvrage_id', flat=True)
    history_book_ids = loans.values_list('exemplaire__ouvrage_id', flat=True)
    history_category_ids = loans.values_list('exemplaire__ouvrage__categorie_id', flat=True)
    recommendations = (
        Ouvrage.objects.filter(categorie_id__in=history_category_ids)
        .exclude(id__in=history_book_ids)
        .exclude(id__in=favorite_ids)
        .distinct()[:6]
    )
    if not recommendations:
        recommendations = Ouvrage.objects.annotate(total_loans=Count('exemplaires__emprunt')).order_by('-total_loans', 'titre')[:6]

    context = {
        'loans_count': loans.count(),
        'active_loans': active_loans,
        'active_loans_count': active_loans.count(),
        'reservations_count': Reservation.objects.filter(lecteur=user).count(),
        'favorites_count': Favorite.objects.filter(lecteur=user).count(),
        'overdue_count': active_loans.filter(date_retour_prevue__lt=timezone.now()).count(),
        'sanctions_count': Sanction.objects.filter(lecteur=user).count(),
        'recent_loans': loans[:5],
        'recent_reservations': Reservation.objects.filter(lecteur=user).select_related('ouvrage').order_by('-date_reservation')[:5],
        'favorites': Favorite.objects.filter(lecteur=user).select_related('ouvrage')[:5],
        'recommendations': recommendations,
        'notifications': Notification.objects.filter(lecteur=user).order_by('-date_envoi')[:5],
        'open_statuses': [Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
    }
    return render(request, 'dashboard/reader_dashboard.html', context)


@login_required
def system_permissions(request):
    if not request.user.is_administrateur():
        return render(request, 'dashboard/forbidden.html')
    permissions = [
        ('Gestion utilisateurs', True, False, False),
        ('Gestion rôles et suspension', True, False, False),
        ('CRUD ouvrages et catégories', True, True, False),
        ('CRUD exemplaires et disponibilité', True, True, False),
        ('Création emprunts et retours', True, True, False),
        ('Historique emprunts personnel', True, True, True),
        ('Réservations: voir toutes', True, True, False),
        ('Réservations: réserver / annuler ses demandes', True, False, True),
        ('Sanctions globales', True, True, False),
        ('Sanctions personnelles', True, False, True),
        ('Analytics système', True, False, False),
        ('Catalogue public et recommandations', True, True, True),
    ]
    return render(request, 'dashboard/permissions.html', {'permissions': permissions})
