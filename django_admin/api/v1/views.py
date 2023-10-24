from django.http import JsonResponse
from django.views.generic.list import BaseListView, ListView
from movies.models import Movie
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .serializers import MovieSerializer


class MoviesListView(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovieSerializer
    permission_classes = (AllowAny,)
    queryset = Movie.objects.prefetch_related('genres', 'actors', 'directors', 'writers').all()


class MoviesListApi(BaseListView):
    model = Movie
    http_method_names = ['get']  # Список методов, которые реализует обработчик
    paginate_by = 10

    def get_queryset(self):
        return self.model.objects.values('id').all()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = {
            'results': list(self.get_queryset()),
        }
        return context

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)