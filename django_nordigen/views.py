from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from .api import get_api


def redirect(request):
    error = request.GET.get('error')
    if error:
        return HttpResponse(
            f'Nordigen requisition failed: {error}',
            content_type='text/plain',
        )
    reference_id = request.GET.get('ref')
    api = get_api()
    requisition = get_object_or_404(
        api.integration.requisition_set, reference_id=reference_id
    )
    api.accept_requisition(requisition)
    return HttpResponse('Nordigen requisition successful.')
