from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from users.models import CustomUser, Follow
from users.serializers import (
    UserProfileSerializer,
    UserSubscriptionSerializer,
    ShortUserSerializer,
)


class UserProfileViewSet(viewsets.ModelViewSet):

    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def change_avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'avatar': serializer.data['avatar']},
                status=status.HTTP_200_OK,
            )

        user.avatar.delete()
        return Response(
            {'message': 'Аватар удалён'},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def subscribe_and_unsubscribe(self, request, id=None):
        author = get_object_or_404(CustomUser, pk=id)
        if author == request.user:
            raise ValidationError(
                {'error': 'Нельзя подписаться на самого себя'}
            )

        if request.method == 'POST':
            subscription, created = Follow.objects.get_or_create(
                subscriber=request.user,
                author=author,
            )
            if not created:
                raise ValidationError({'error': 'Подписка уже оформлена'})
            return Response(
                {
                    'user': subscription.subscriber.username,
                    'author': subscription.author.username,
                },
                status=status.HTTP_201_CREATED,
            )

        subscription = get_object_or_404(
            Follow,
            subscriber=request.user,
            author=author,
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        user = request.user
        subscriptions = user.subscriptions.select_related('author')
        serializer = UserSubscriptionSerializer(
            subscriptions,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):

    queryset = CustomUser.objects.all()
    serializer_class = ShortUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'], url_path='me')
    def get_me(self, request):
        return Response(self.get_serializer(request.user).data)
