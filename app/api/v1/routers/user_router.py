from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status

from app.api.dependencies import get_current_user_id, get_user_service
from app.api.v1.schemas.user_schema import UserResponse, UserUpdateRequest
from app.core.exceptions import InsufficientPermissionsError
from app.modules.users.use_cases.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List users",
    description="Return all users ordered by newest first.",
)
async def list_users(
    current_user_id=Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> list[UserResponse]:
    user = await service.get_user(current_user_id)
    return [UserResponse.model_validate(user)]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get one user",
    description="Fetch a user by UUIDv7 identifier.",
)
async def get_user(
    user_id: Annotated[
        UUID,
        Path(
            description="User UUIDv7 to retrieve.",
            examples=["019d92aa-a6f4-74d3-a353-83f65edbb83e"],
        ),
    ],
    current_user_id=Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    if user_id != current_user_id:
        raise InsufficientPermissionsError("You can only access your own user profile.")
    user = await service.get_user(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description="Partially update user name, email, or active status.",
)
async def update_user(
    user_id: Annotated[
        UUID,
        Path(
            description="User UUIDv7 to update.",
            examples=["019d92aa-a6f4-74d3-a353-83f65edbb83e"],
        ),
    ],
    body: Annotated[
        UserUpdateRequest,
        Body(description="Payload for partial user updates."),
    ],
    current_user_id=Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    if user_id != current_user_id:
        raise InsufficientPermissionsError("You can only update your own user profile.")
    updated = await service.update_user(
        user_id,
        name=body.name,
        email=body.email,
        is_active=body.is_active,
    )
    return UserResponse.model_validate(updated)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Delete a user by UUIDv7. Related sessions are cascade-deleted.",
)
async def delete_user(
    user_id: Annotated[
        UUID,
        Path(
            description="User UUIDv7 to delete.",
            examples=["019d92aa-a6f4-74d3-a353-83f65edbb83e"],
        ),
    ],
    current_user_id=Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> None:
    if user_id != current_user_id:
        raise InsufficientPermissionsError("You can only delete your own user profile.")
    await service.delete_user(user_id)
