from django.urls import path

from apps.analytics.views import TicketSummaryView


urlpatterns = [
    path('tickets/summary/', TicketSummaryView.as_view(), name='ticket-summary'),
]
