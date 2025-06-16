import { UserIdentity } from "@/lib/api/user/user";
import { AdminResetPasswordModal } from "@/lib/components/AdminResetPasswordModal/AdminResetPasswordModal";
import { CreateUserModal } from "@/lib/components/CreateUserModal/CreateUserModal";
import { DeactivateUserModal } from "@/lib/components/DeactivateUserModal/DeactivateUserModal";

type UserModalsProps = {
  selectedUser: UserIdentity;
  isEditModalOpen: boolean;
  setIsEditModalOpen: (isOpen: boolean) => void;
  isResetPasswordModalOpen: boolean;
  setIsResetPasswordModalOpen: (isOpen: boolean) => void;
  isDeactivateModalOpen: boolean;
  setIsDeactivateModalOpen: (isOpen: boolean) => void;
  onSuccess: () => void;
};

export const UserModals = ({
  selectedUser,
  isEditModalOpen,
  setIsEditModalOpen,
  isResetPasswordModalOpen,
  setIsResetPasswordModalOpen,
  isDeactivateModalOpen,
  setIsDeactivateModalOpen,
  onSuccess,
}: UserModalsProps): JSX.Element => (
  <>
    <CreateUserModal
      isOpen={isEditModalOpen}
      setOpen={setIsEditModalOpen}
      isEditMode={true}
      userData={selectedUser}
      onSuccess={onSuccess}
    />
    <AdminResetPasswordModal
      isOpen={isResetPasswordModalOpen}
      setOpen={setIsResetPasswordModalOpen}
      userId={selectedUser.id}
      userEmail={selectedUser.email ?? "N/A"}
      onSuccess={onSuccess}
    />
    <DeactivateUserModal
      isOpen={isDeactivateModalOpen}
      setOpen={setIsDeactivateModalOpen}
      userId={selectedUser.id}
      userEmail={selectedUser.email ?? "N/A"}
      userName={selectedUser.username}
      onSuccess={onSuccess}
    />
  </>
);
