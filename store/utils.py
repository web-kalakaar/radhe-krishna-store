from django.core.paginator import Paginator


def paginate(request, queryset, per_page=8):
    """Return (page_obj, querystring) for the page requested in the URL.

    `querystring` holds every URL parameter except `page`, so pagination links
    can keep the customer's filters, sorting and search words.
    """
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    return page_obj, params.urlencode()