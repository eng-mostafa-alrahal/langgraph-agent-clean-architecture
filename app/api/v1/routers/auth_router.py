from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.api.dependencies import get_current_user_id, get_user_service
from app.api.v1.schemas.token_schema import RefreshTokenRequest, TokenResponse
from app.api.v1.schemas.user_schema import UserLoginRequest, UserRegisterRequest, UserResponse
from app.modules.users.use_cases.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create an account using name, email, and password.",
)
async def register(
    body: Annotated[
        UserRegisterRequest,
        Body(description="Registration payload containing name, email, and password."),
    ],
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.register(name=body.name, email=body.email, password=body.password)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get tokens",
    description=(
        "Authenticate with email and password. "
        "Use the returned `access_token` as `Bearer <token>` in Swagger Authorize."
    ),
)
async def login(
    body: Annotated[
        UserLoginRequest,
        Body(description="Login payload containing email and password."),
    ],
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    tokens = await service.authenticate(email=body.email, password=body.password)
    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access/refresh token pair.",
)
async def refresh_token(
    body: Annotated[
        RefreshTokenRequest,
        Body(description="Payload containing the refresh token to rotate."),
    ],
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    tokens = await service.refresh_tokens(body.refresh_token)
    return TokenResponse(**tokens)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Return profile data for the authenticated user linked to the bearer token.",
)
async def get_me(
    user_id=Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_profile(user_id)
    return UserResponse.model_validate(user)
