from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogue.models import Exemplaire, Ouvrage
from loans import services as loan_services
from loans.models import Emprunt, LoanRequest
from notifications.models import Notification

from .models import Reservation


@login_required
@require_POST
def reserve_ouvrage(request, ouvrage_id):
	ouvrage = get_object_or_404(Ouvrage, pk=ouvrage_id)
	user = request.user
	if not user.is_lecteur():
		messages.error(request, 'Seuls les lecteurs peuvent reserver un ouvrage.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	if user.statut_compte != user.STATUT_ACTIF or user.is_suspended:
		messages.error(request, 'Votre compte est suspendu ou bloque.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	if Reservation.objects.filter(ouvrage=ouvrage, lecteur=user, statut=Reservation.STATUS_ACTIVE).exists():
		messages.info(request, 'Vous avez deja une reservation active pour cet ouvrage.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	if LoanRequest.objects.filter(ouvrage=ouvrage, lecteur=user, statut=LoanRequest.STATUS_PENDING).exists():
		messages.info(request, 'Vous avez deja une demande de pret en attente pour cet ouvrage.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	if Emprunt.objects.filter(
		lecteur=user,
		exemplaire__ouvrage=ouvrage,
		statut=Emprunt.STAT_EN_COURS,
		date_retour_effective__isnull=True,
	).exists():
		messages.info(request, 'Vous avez deja un emprunt actif pour cet ouvrage.')
		return redirect('catalogue:detail', pk=ouvrage_id)
	Reservation.objects.create(ouvrage=ouvrage, lecteur=user)
	Notification.objects.create(
		lecteur=user,
		ouvrage=ouvrage,
		type_notification=Notification.TYPE_RESERVATION,
		message=f"Reservation enregistree pour {ouvrage.titre}.",
	)
	messages.success(request, 'Reservation enregistree.')
	return redirect('catalogue:detail', pk=ouvrage_id)


@login_required
def my_reservations(request):
	if request.user.is_administrateur() or request.user.is_bibliothecaire():
		res = Reservation.objects.select_related('ouvrage', 'lecteur').order_by('-date_reservation')
	else:
		res = Reservation.objects.filter(lecteur=request.user).select_related('ouvrage').order_by('-date_reservation')
	return render(request, 'reservations/list.html', {'reservations': res})


@login_required
@require_POST
def cancel_reservation(request, pk):
	reservation = get_object_or_404(Reservation, pk=pk)
	if reservation.lecteur != request.user and not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
		messages.error(request, 'Acces refuse.')
		return redirect('reservations:my_reservations')
	if reservation.statut != Reservation.STATUS_ACTIVE:
		messages.info(request, 'Cette reservation ne peut plus etre annulee.')
		return redirect('reservations:my_reservations')
	reservation.statut = Reservation.STATUS_ANNULEE
	reservation.save(update_fields=['statut'])
	if reservation.lecteur != request.user:
		Notification.objects.create(
			lecteur=reservation.lecteur,
			ouvrage=reservation.ouvrage,
			type_notification=Notification.TYPE_REFUSAL,
			message=f"Votre reservation pour {reservation.ouvrage.titre} a ete annulee par le personnel.",
		)
	messages.success(request, 'Reservation annulee.')
	return redirect('reservations:my_reservations')


@login_required
@require_POST
def reject_reservation(request, pk):
	if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
		messages.error(request, 'Acces refuse.')
		return redirect('reservations:my_reservations')
	reservation = get_object_or_404(Reservation, pk=pk)
	if reservation.statut != Reservation.STATUS_ACTIVE:
		messages.info(request, 'Cette reservation est deja traitee.')
		return redirect('reservations:my_reservations')
	reservation.statut = Reservation.STATUS_REFUSEE
	reservation.save(update_fields=['statut'])
	Notification.objects.create(
		lecteur=reservation.lecteur,
		ouvrage=reservation.ouvrage,
		type_notification=Notification.TYPE_REFUSAL,
		message=f"Votre reservation pour {reservation.ouvrage.titre} a ete refusee.",
	)
	messages.success(request, 'Reservation refusee.')
	return redirect('reservations:my_reservations')


@login_required
@require_POST
def confirm_reservation(request, pk):
	if not (request.user.is_administrateur() or request.user.is_bibliothecaire()):
		messages.error(request, 'Acces refuse.')
		return redirect('reservations:my_reservations')
	reservation = get_object_or_404(Reservation, pk=pk)
	if reservation.statut != Reservation.STATUS_ACTIVE:
		messages.info(request, 'Cette reservation est deja traitee.')
		return redirect('reservations:my_reservations')
	available = Exemplaire.objects.filter(ouvrage=reservation.ouvrage, status=Exemplaire.STATUS_DISP).first()
	if not available:
		messages.error(request, 'Aucun exemplaire disponible pour creer l emprunt.')
		return redirect('reservations:my_reservations')
	reservation.statut = Reservation.STATUS_HONOREE
	try:
		loan_services.create_loan_from_copy(available, reservation.lecteur, request.user)
	except ValueError as exc:
		messages.error(request, str(exc))
		return redirect('reservations:my_reservations')
	reservation.save(update_fields=['statut'])
	Notification.objects.create(
		lecteur=reservation.lecteur,
		ouvrage=reservation.ouvrage,
		type_notification=Notification.TYPE_EMPRUNT,
		message=f"Votre reservation pour {reservation.ouvrage.titre} a ete confirmee et un emprunt a ete cree.",
	)
	messages.success(request, 'Reservation confirmee et emprunt cree.')
	return redirect('reservations:my_reservations')
