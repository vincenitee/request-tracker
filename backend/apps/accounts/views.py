from rest_framework.generics import RetrieveAPIView

from .serializers import MeSerializer


class MeView(RetrieveAPIView):
    """The logged-in user. Uses the default IsAuthenticated permission."""

    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
