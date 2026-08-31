from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CurrentUserSerializer


class MeView(APIView):
    """
    GET /api/accounts/me/  -> returns the logged-in user's profile + role.
    This is the first endpoint to test once you log into /admin/ and then
    hit this URL in the same browser session — confirms auth + serializer
    + role field are all wired correctly before building anything on top.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)
