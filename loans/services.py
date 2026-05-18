from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from catalogue.models import Exemplaire
from notifications.models import Notification
from reservations.models import Reservation
from sanctions.models import Sanction

from .models import Emprunt, LoanRequest


MAX_LOAN_DAYS = 14
REMINDER_WINDOW_DAYS = 3


def parse_date(value):
	if not value:
		return None
	if isinstance(value, date):
		return value
	return date.fromisoformat(value)


def date_to_aware(value_date, end_of_day=False):
	clock = time.max if end_of_day else time.min
	return timezone.make_aware(datetime.combine(value_date, clock))


def is_library_staff(user):
	return user.is_bibliothecaire() or user.is_administrateur()


def notify(lecteur, type_notification, message, ouvrage=None):
	return Notification.objects.get_or_create(
		lecteur=lecteur,
		type_notification=type_notification,
		ouvrage=ouvrage,
		message=message,
	)[0]


def create_loan_from_copy(exemplaire, lecteur, bibliothecaire=None, start_date=None, due_date=None):
	start = parse_date(start_date) or timezone.localdate()
	due = parse_date(due_date) or (start + timedelta(days=MAX_LOAN_DAYS))
	if due < start:
		raise ValueError('La date de retour prevue doit etre posterieure a la date emprunt.')
	with transaction.atomic():
		exemplaire = Exemplaire.objects.select_for_update().get(pk=exemplaire.pk)
		if exemplaire.status != Exemplaire.STATUS_DISP:
			raise ValueError('Exemplaire non disponible.')
		if Emprunt.objects.filter(
			exemplaire__ouvrage=exemplaire.ouvrage,
			lecteur=lecteur,
			statut=Emprunt.STAT_EN_COURS,
			date_retour_effective__isnull=True,
		).exists():
			raise ValueError('Ce lecteur a deja un emprunt actif pour cet ouvrage.')
		loan = Emprunt.objects.create(
			exemplaire=exemplaire,
			lecteur=lecteur,
			bibliothecaire=bibliothecaire,
			date_emprunt=date_to_aware(start),
			date_retour_prevue=date_to_aware(due, end_of_day=True),
			statut=Emprunt.STAT_EN_COURS,
		)
		exemplaire.status = Exemplaire.STATUS_EMPR
		exemplaire.save(update_fields=['status'])
		notify(
			lecteur,
			Notification.TYPE_EMPRUNT,
			f"Emprunt confirme pour {exemplaire.ouvrage.titre}. Retour prevu le {due.strftime('%d/%m/%Y')}.",
			exemplaire.ouvrage,
		)
		return loan


def approve_loan_request(loan_request, staff_user, start_date=None, due_date=None):
	start = parse_date(start_date) or loan_request.date_debut_souhaite or timezone.localdate()
	due = parse_date(due_date) or loan_request.date_fin_souhaite or (start + timedelta(days=MAX_LOAN_DAYS))
	with transaction.atomic():
		loan_request = LoanRequest.objects.select_for_update().get(pk=loan_request.pk)
		if loan_request.statut != LoanRequest.STATUS_PENDING:
			raise ValueError('Cette demande a deja ete traitee.')
		available = (
			Exemplaire.objects.select_for_update()
			.filter(ouvrage=loan_request.ouvrage, status=Exemplaire.STATUS_DISP)
			.first()
		)
		if not available:
			raise ValueError('Aucun exemplaire disponible pour cette demande.')
		loan = create_loan_from_copy(available, loan_request.lecteur, staff_user, start, due)
		loan_request.statut = LoanRequest.STATUS_APPROVED
		loan_request.save(update_fields=['statut'])
		notify(
			loan_request.lecteur,
			Notification.TYPE_EMPRUNT,
			f"Votre demande de pret pour {loan_request.ouvrage.titre} a ete acceptee.",
			loan_request.ouvrage,
		)
		return loan


def reject_loan_request(loan_request):
	loan_request.statut = LoanRequest.STATUS_REJECTED
	loan_request.save(update_fields=['statut'])
	notify(
		loan_request.lecteur,
		Notification.TYPE_REFUSAL,
		f"Votre demande de pret pour {loan_request.ouvrage.titre} a ete refusee.",
		loan_request.ouvrage,
	)


def refresh_overdue_loans():
	now = timezone.now()
	active_loans = Emprunt.objects.filter(
		statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
		date_retour_effective__isnull=True,
		date_retour_prevue__isnull=False,
	).select_related('exemplaire__ouvrage', 'lecteur')
	for loan in active_loans:
		if loan.date_retour_prevue < now:
			ex = loan.exemplaire
			if ex.status != Exemplaire.STATUS_RET:
				ex.status = Exemplaire.STATUS_RET
				ex.save(update_fields=['status'])
			days = max(1, (timezone.localdate() - loan.date_retour_prevue.date()).days)
			fine = days * Emprunt.FINE_PER_DAY
			Sanction.objects.update_or_create(
				lecteur=loan.lecteur,
				emprunt=loan,
				type_sanction=Sanction.TYPE_AMENDE,
				defaults={'montant': fine, 'statut': 'active'},
			)
			notify(
				loan.lecteur,
				Notification.TYPE_RETARD,
				f"Votre emprunt de {loan.exemplaire.ouvrage.titre} est en retard de {days} jour(s). Amende estimee : {fine} MAD.",
				loan.exemplaire.ouvrage,
			)
			continue
		if loan.statut == Emprunt.STAT_EN_COURS:
			remaining = (loan.date_retour_prevue.date() - timezone.localdate()).days
			if 0 <= remaining <= REMINDER_WINDOW_DAYS:
				notify(
					loan.lecteur,
					Notification.TYPE_RAPPEL,
					f"Rappel : votre emprunt de {loan.exemplaire.ouvrage.titre} arrive a echeance dans {remaining} jour(s).",
					loan.exemplaire.ouvrage,
				)


def process_return(loan, actor=None):
	with transaction.atomic():
		loan = Emprunt.objects.select_for_update().select_related('exemplaire__ouvrage', 'lecteur').get(pk=loan.pk)
		if not loan.can_be_returned:
			raise ValueError('Cet emprunt est deja cloture.')
		loan.date_retour_effective = timezone.now()
		fine = loan.calculate_fine()
		loan.statut = Emprunt.STAT_RET
		loan.save(update_fields=['date_retour_effective', 'statut'])
		if fine > 0:
			Sanction.objects.update_or_create(
				lecteur=loan.lecteur,
				emprunt=loan,
				type_sanction=Sanction.TYPE_AMENDE,
				defaults={'montant': fine, 'statut': 'active'},
			)
			notify(
				loan.lecteur,
				Notification.TYPE_RETARD,
				f"Votre emprunt de {loan.exemplaire.ouvrage.titre} a ete retourne en retard. Amende due : {fine} MAD.",
				loan.exemplaire.ouvrage,
			)
		notify(
			loan.lecteur,
			Notification.TYPE_RETOUR,
			f"Livre retourne avec succes : {loan.exemplaire.ouvrage.titre}.",
			loan.exemplaire.ouvrage,
		)
		ex = loan.exemplaire
		ex.status = Exemplaire.STATUS_DISP
		ex.save(update_fields=['status'])
		next_res = Reservation.objects.select_for_update().filter(
			ouvrage=ex.ouvrage,
			statut=Reservation.STATUS_ACTIVE,
		).order_by('position_file').first()
		if next_res:
			notify(
				next_res.lecteur,
				Notification.TYPE_DISPO,
				f"Ouvrage disponible : votre reservation pour {next_res.ouvrage.titre} peut etre traitee.",
				next_res.ouvrage,
			)
		return fine
