from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogue.models import Exemplaire, Ouvrage
from notifications.models import Notification
from reservations.models import Reservation

from . import services
from .models import Emprunt, LoanRequest


@login_required
def create_loan(request):
	if not services.is_library_staff(request.user):
		messages.error(request, 'Acces refuse')
		return redirect('catalogue:list')
	if request.method == 'POST':
		lecteur = get_object_or_404(request.user.__class__, pk=request.POST.get('lecteur'))
		exemplaire = get_object_or_404(Exemplaire, pk=request.POST.get('exemplaire'))
		try:
			services.create_loan_from_copy(
				exemplaire,
				lecteur,
				request.user,
				request.POST.get('date_debut'),
				request.POST.get('date_retour'),
			)
		except ValueError as exc:
			messages.error(request, str(exc))
			return redirect('loans:create')
		messages.success(request, 'Emprunt enregistre')
		return redirect('loans:list')
	exemplaires = Exemplaire.objects.filter(status=Exemplaire.STATUS_DISP).select_related('ouvrage')
	return render(request, 'loans/form.html', {'exemplaires': exemplaires})


@login_required
def list_loans(request):
	services.refresh_overdue_loans()
	active_statuses = [Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD]
	if services.is_library_staff(request.user):
		qs = Emprunt.objects.select_related('exemplaire__ouvrage', 'lecteur').all().order_by('-date_emprunt')
		return render(request, 'loans/list.html', {
			'emprunts': qs,
			'open_statuses': active_statuses,
			'active_status': Emprunt.STAT_EN_COURS,
			'can_manage_loans': True,
		})

	user_loans = Emprunt.objects.select_related('exemplaire__ouvrage').filter(lecteur=request.user).order_by('-date_emprunt')
	active_emprunts = user_loans.filter(statut__in=active_statuses, date_retour_effective__isnull=True)
	returned_emprunts = user_loans.exclude(statut__in=active_statuses, date_retour_effective__isnull=True)
	return render(request, 'loans/list.html', {
		'active_emprunts': active_emprunts,
		'returned_emprunts': returned_emprunts,
		'open_statuses': active_statuses,
		'active_status': Emprunt.STAT_EN_COURS,
		'can_manage_loans': False,
	})


@login_required
def list_requests(request):
	if services.is_library_staff(request.user):
		qs = LoanRequest.objects.select_related('ouvrage', 'lecteur').order_by('-date_demande')
	else:
		qs = LoanRequest.objects.filter(lecteur=request.user).select_related('ouvrage').order_by('-date_demande')
	return render(request, 'loans/requests.html', {'requests': qs})


@login_required
def request_loan(request, ouvrage_id):
	ouvrage = get_object_or_404(Ouvrage, pk=ouvrage_id)
	if not request.user.is_lecteur():
		messages.error(request, 'Seuls les lecteurs peuvent faire une demande d emprunt.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	if request.method == 'POST':
		try:
			desired_start = services.parse_date(request.POST.get('date_debut')) or date.today()
			desired_return = services.parse_date(request.POST.get('date_fin'))
		except ValueError:
			messages.error(request, 'Format de date invalide.')
			return render(request, 'loans/request_form.html', {'ouvrage': ouvrage})
		if desired_start < date.today():
			messages.error(request, 'La date souhaitee doit etre aujourd hui ou dans le futur.')
			return render(request, 'loans/request_form.html', {'ouvrage': ouvrage})
		if desired_return and desired_return < desired_start:
			messages.error(request, 'La date de retour souhaitee doit etre posterieure a la date de debut.')
			return render(request, 'loans/request_form.html', {'ouvrage': ouvrage})
		commentaire = request.POST.get('commentaire', '').strip()
		if (
			LoanRequest.objects.filter(lecteur=request.user, ouvrage=ouvrage, statut=LoanRequest.STATUS_PENDING).exists()
			or Emprunt.objects.filter(
				lecteur=request.user,
				exemplaire__ouvrage=ouvrage,
				statut__in=[Emprunt.STAT_EN_COURS, Emprunt.STAT_RETARD],
			).exists()
			or Reservation.objects.filter(lecteur=request.user, ouvrage=ouvrage, statut=Reservation.STATUS_ACTIVE).exists()
		):
			messages.info(request, 'Vous avez deja une demande, reservation ou un emprunt actif pour cet ouvrage.')
			return redirect('catalogue:detail', pk=ouvrage_id)
		LoanRequest.objects.create(
			ouvrage=ouvrage,
			lecteur=request.user,
			date_debut_souhaite=desired_start,
			date_fin_souhaite=desired_return,
			commentaire=commentaire,
		)
		Notification.objects.create(
			lecteur=request.user,
			ouvrage=ouvrage,
			type_notification=Notification.TYPE_RESERVATION,
			message=f"Votre demande de pret pour {ouvrage.titre} a bien ete recue.",
		)
		messages.success(request, 'Demande d emprunt enregistree.')
		return redirect('loans:requests')
	return render(request, 'loans/request_form.html', {'ouvrage': ouvrage})


@login_required
@require_POST
def approve_request(request, pk):
	if not services.is_library_staff(request.user):
		messages.error(request, 'Acces refuse')
		return redirect('loans:requests')
	loan_request = get_object_or_404(LoanRequest, pk=pk)
	try:
		services.approve_loan_request(
			loan_request,
			request.user,
			request.POST.get('date_debut'),
			request.POST.get('date_retour'),
		)
	except ValueError as exc:
		messages.error(request, str(exc))
		return redirect('loans:requests')
	messages.success(request, 'Demande approuvee et emprunt cree.')
	return redirect('loans:requests')


@login_required
@require_POST
def reject_request(request, pk):
	if not services.is_library_staff(request.user):
		messages.error(request, 'Acces refuse')
		return redirect('loans:requests')
	loan_request = get_object_or_404(LoanRequest, pk=pk)
	if loan_request.statut != LoanRequest.STATUS_PENDING:
		messages.info(request, 'Cette demande a deja ete traitee.')
		return redirect('loans:requests')
	services.reject_loan_request(loan_request)
	messages.success(request, 'Demande refusee.')
	return redirect('loans:requests')


@login_required
@require_POST
def cancel_request(request, pk):
	loan_request = get_object_or_404(LoanRequest, pk=pk)
	if loan_request.lecteur != request.user and not services.is_library_staff(request.user):
		messages.error(request, 'Acces refuse')
		return redirect('loans:requests')
	if loan_request.statut != LoanRequest.STATUS_PENDING:
		messages.info(request, 'Cette demande ne peut plus etre annulee.')
		return redirect('loans:requests')
	loan_request.statut = LoanRequest.STATUS_CANCELLED
	loan_request.save(update_fields=['statut'])
	if loan_request.lecteur != request.user:
		Notification.objects.create(
			lecteur=loan_request.lecteur,
			ouvrage=loan_request.ouvrage,
			type_notification=Notification.TYPE_REFUSAL,
			message=f"Votre demande de pret pour {loan_request.ouvrage.titre} a ete annulee par le personnel.",
		)
	messages.success(request, 'Demande annulee.')
	return redirect('loans:requests')


@login_required
@require_POST
def process_return(request, pk):
	emprunt = get_object_or_404(Emprunt, pk=pk)
	if not services.is_library_staff(request.user) and emprunt.lecteur != request.user:
		messages.error(request, 'Acces refuse')
		return redirect('loans:list')
	try:
		fine = services.process_return(emprunt, request.user if services.is_library_staff(request.user) else None)
	except ValueError as exc:
		messages.info(request, str(exc))
		return redirect('loans:list')
	if fine > 0:
		messages.success(request, f'Retour enregistre. Amende: {fine} MAD')
	else:
		messages.success(request, 'Retour enregistre avec succes.')
	return redirect('loans:list')
