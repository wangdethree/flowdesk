from django.urls import path

from apps.ai.views import TicketAssistantSuggestionView, TicketDraftSuggestionView


urlpatterns = [
    path('ticket-draft/', TicketDraftSuggestionView.as_view(), name='ai-ticket-draft'),
    path('tickets/<int:pk>/suggestion/', TicketAssistantSuggestionView.as_view(), name='ai-ticket-suggestion'),
]
