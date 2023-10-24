from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Count, Q, QuerySet
from django.http import JsonResponse
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView
from movies.models import Filmwork


class MoviesApiMixin(BaseListView):
    model = Filmwork
    http_method_names = ['get']
    paginate_by = 50

    def get_queryset(self):
        """
        Return the list of items for this view.
        The return value must be an iterable and may be an instance of
        `QuerySet` in which case `QuerySet` specific behavior will be enabled.
        """
        if self.queryset is not None:
            queryset = self.queryset
            if isinstance(queryset, QuerySet):
                queryset = queryset.all()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {
                    'cls': self.__class__.__name__
                }
            )
        queryset = queryset.values()\
                .annotate(genres=ArrayAgg('genres__name'))\
                .annotate(actors=ArrayAgg('personfilmwork__person__full_name', filter=Q(personfilmwork__role='actor')))\
                .annotate(directors=ArrayAgg('personfilmwork__person__full_name', filter=Q(personfilmwork__role='director')))\
                .annotate(writers=ArrayAgg('personfilmwork__person__full_name', filter=Q(personfilmwork__role='writer')))
        return queryset

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)


class MoviesListApi(MoviesApiMixin):

    def get_context_data(self, *, object_list=None, **kwargs):

        queryset = self.get_queryset()

        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset,
            self.paginate_by
        )
        return {'count': paginator.count,
                "total_pages": int,
                "prev": int,
                "next": int,
                "results": list
    }

class MoviesDetailApi(MoviesApiMixin):

    def get_context_data(self, **kwargs):
        return

m = MoviesListApi()
m.render_to_response(m.get_context_data())