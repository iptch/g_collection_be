from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import HttpRequest
from genius_collection.core.serializers import UserSerializer, CardSerializer

from .models import Card, User, Ownership
from .jwt_validation import JWTAccessTokenAuthentication

from .helper.ownership_helper import OwnershipHelper


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CardViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cards to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request: HttpRequest):
        
        giver: User = User.objects.get(email=request.data["giver"])
        card: Card = Card.objects.get(id=request.data["id"])

        try:
            ownership: Ownership = Ownership.objects.get(user=giver, card=card)
        except Ownership.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=f"Oh Brate, Ownership does not exist!, {request.headers.items}")
        
        
        OwnershipHelper.transfer_ownership(request.user, ownership, card)
        
        return Response({"status": f"Card transfered successfully, Brate, now {ownership}"})

