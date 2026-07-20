from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import ActiveUserDep, AuthServiceDep
from app.api.schemas.auth import TokenResponse, UserCreate, UserResponse
from app.application.auth.service import DuplicateUserError

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, auth_service: AuthServiceDep) -> UserResponse:
    try:
        user = await auth_service.register(payload.email, payload.password)
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "Email is already registered"},
        ) from exc
    return UserResponse.model_validate(user)


@router.post("/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], auth_service: AuthServiceDep
) -> TokenResponse:
    token = await auth_service.authenticate(form_data.username, form_data.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: ActiveUserDep) -> UserResponse:
    return UserResponse.model_validate(current_user)
