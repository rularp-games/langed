from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Постраничная выдача списков: параметры page и page_size,
    ответ вида {count, next, previous, results}.
    """
    page_size = 24
    page_size_query_param = 'page_size'
    max_page_size = 100
