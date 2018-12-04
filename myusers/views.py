#from django.shortcuts import render
from rest_framework import generics, views
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, TokenHasScope
from .models import MyUser
from .permissions import CheckOperationPerm, IsOwnerOrReadOnly
from .serializers import MyUserListSerializer, MyUserDetailSerializer, ChangePasswordSerializer
from .serializers import CreateUserSerializer, UserLoginSerializers


from oauth2_provider.models import AccessToken
from django.contrib.auth.models import Permission


class UserView(generics.CreateAPIView):
    """
    post - 创建用户
    """
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.AllowAny]


class UserLoginView(generics.GenericAPIView):
    """
    post - 用户登录
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializers

    def post(self, request):
        request_dict = request.data

        # 查询登录用户的权限
        token_obj = AccessToken.objects.get(token=request_dict.get("token"))
        # print(token_obj.user.email)

        # 根据token查询对应的scope
        scope_list = token_obj.scope.split(" ")

        index = ""

        for i, value in enumerate(scope_list):
            if value == "users":
                index = i
                break

        if type(index) == int:
            scope_list[index] = "user"

        user = token_obj.user

        for value in scope_list:
            permissions_list = Permission.objects.filter(codename__contains=value)

            # print(permissions_list)

            user.user_permissions.add(*[p_id for p_id in permissions_list])

        serializer = UserLoginSerializers(data=request_dict)

        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class UserLogoutView(views.APIView):
    """
    当前用户退出登录
    """

    permission_classes = [TokenHasScope, IsOwnerOrReadOnly]
    required_scopes = ['users']

    def get(self, request):
        # data_dict = request.data
        return Response({
            "msg": "退出成功",
            "code": status.HTTP_200_OK,
        })


class MyUserList(generics.ListAPIView):
    """
        get:
        获取所有 用户 列表
    """

    permission_classes = [TokenHasScope, IsOwnerOrReadOnly]
    required_scopes = ['users']
    queryset = MyUser.objects.all()
    serializer_class = MyUserListSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('$user_name', '$phone')

    # myuser = MyUser.objects.filter(id__in=range(1, 20))
    # # print(myuser)
    #
    # for user in myuser:
    #
    #     print(user.get_all_permissions())


class MyUserDetail(generics.RetrieveUpdateAPIView):
    """
        get:
        获取该 用户 的详情

        put:
        整体更新该 用户.

        patch:
        部分更新该 用户.
    """
    permission_classes = [TokenHasScope, CheckOperationPerm]
    required_scopes = ["users"]
    queryset = MyUser.objects.all()
    serializer_class = MyUserDetailSerializer


class UpdatePassword(generics.GenericAPIView):
    """
        put:
        更新密码，需要提供旧密码
    """
    permission_classes = [TokenHasScope, CheckOperationPerm]
    required_scopes = ['users']

    def get_object(self, queryset=None):
        return self.request.user

    def get_queryset(self):
        user = self.request.user
        return user.accounts.all()

    def get_serializer_class(self):
        return ChangePasswordSerializer

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            old_password = serializer.data.get("old_password")
            if not self.object.check_password(old_password):
                return Response({"old_password": ["Wrong password."]},
                                status=status.HTTP_400_BAD_REQUEST)
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            return Response({"status": "success"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)