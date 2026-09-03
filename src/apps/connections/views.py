"""
Connections endpoints — port of `src/connections/connections.controller.ts`.

Controller uses JwtAuthGuard ONLY (no RolesGuard); authorization is
relationship-based inside the service.
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import JwtAuthenticated
from . import services
from .serializers import CreateConnectionSerializer


class ConnectionRequestView(APIView):
    permission_classes = [JwtAuthenticated]

    def post(self, request):
        s = CreateConnectionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.create_request(dict(s.validated_data), request.user), status=201)


class ConnectionPendingView(APIView):
    permission_classes = [JwtAuthenticated]

    def get(self, request):
        return Response(services.get_pending_requests(request.user))


class ConnectionApproveView(APIView):
    permission_classes = [JwtAuthenticated]

    def patch(self, request, id):
        return Response(services.process_request(id, "approve", request.user))


class ConnectionRejectView(APIView):
    permission_classes = [JwtAuthenticated]

    def patch(self, request, id):
        return Response(services.process_request(id, "reject", request.user))


class MyChildrenView(APIView):
    permission_classes = [JwtAuthenticated]

    def get(self, request):
        return Response(services.get_my_children(request.user))


class MyParentsView(APIView):
    permission_classes = [JwtAuthenticated]

    def get(self, request):
        return Response(services.get_my_parents(request.user))
