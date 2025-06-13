from typing import Optional

from pydantic import BaseModel, Field


class UserUpdatableProperties(BaseModel):
    username: str = Field(..., description="Username of the user")
    company: Optional[str] = None
    onboarded: bool = Field(default=False, description="Whether the user has been onboarded")
    company_size: Optional[str] = None
    usage_purpose: Optional[str] = None


class CreateUserRequest(BaseModel):
    firstName: str = Field(..., description="First name of the user")
    lastName: str = Field(..., description="Last name of the user")
    email: str = Field(..., description="Email of the user")
    brains: list[str] = Field(default=[], description="List of brain IDs associated with the user")


class UpdateUserRequest(BaseModel):
    id: str = Field(..., description="User ID")
    firstName: str = Field(..., description="First name of the user")
    lastName: str = Field(..., description="Last name of the user")
    email: str = Field(..., description="Email of the user")
    brains: list[str] = Field(default=[], description="List of brain IDs associated with the user")


class ResetPasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Confirm new password")


class AdminResetPasswordRequest(BaseModel):
    user_id: str = Field(..., description="User ID to reset password for")
    new_password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Confirm new password")


class DeactivateUserRequest(BaseModel):
    user_id: str = Field(..., description="User ID to deactivate")
