import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useUserApi } from "@/lib/api/user/useUserApi";
import { DeactivateUserRequest } from "@/lib/api/user/user";
import { Modal } from "@/lib/components/ui/Modal/Modal";
import { QuivrButton } from "@/lib/components/ui/QuivrButton/QuivrButton";

import styles from "./DeactivateUserModal.module.scss";

type DeactivateUserModalProps = {
  isOpen: boolean;
  setOpen: (isOpen: boolean) => void;
  userId: string;
  userEmail: string;
  userName: string;
  onSuccess?: () => void;
};

export const DeactivateUserModal = ({
  isOpen,
  setOpen,
  userId,
  userEmail,
  userName,
  onSuccess,
}: DeactivateUserModalProps): JSX.Element => {
  const { t } = useTranslation(["user"]);
  const [isDeactivating, setIsDeactivating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { deactivateUser } = useUserApi();

  const handleDeactivate = async (): Promise<void> => {
    try {
      setIsDeactivating(true);
      setError(null);

      const deactivateData: DeactivateUserRequest = {
        user_id: userId,
      };

      await deactivateUser(deactivateData);

      // Close modal and call success callback
      setOpen(false);
      if (onSuccess) {
        onSuccess();
      }

    } catch (error) {
      console.error("Error deactivating user:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to deactivate user"
      );
    } finally {
      setIsDeactivating(false);
    }
  };

  const handleCancel = (): void => {
    setError(null);
    setOpen(false);
  };

  return (
    <Modal
      title={t("deactivate_user", { ns: "user" })}
      isOpen={isOpen}
      setOpen={setOpen}
      size="auto"
      CloseTrigger={<div />}
    >
      <div className={styles.modal_wrapper}>
        <div className={styles.warning_message}>
          <h3>{t("confirm_deactivate", { ns: "user" })}</h3>
          <div className={styles.user_info}>
            <p><strong>{t("name", { ns: "user" })}:</strong> {userName}</p>
            <p><strong>{t("email", { ns: "user" })}:</strong> {userEmail}</p>
          </div>
          <p className={styles.warning_text}>
            {t("deactivate_user_warning", { ns: "user" })}
          </p>
        </div>

        {error && <div className={styles.error_message}>{error}</div>}

        <div className={styles.buttons}>
          <QuivrButton
            onClick={handleCancel}
            color="primary"
            label={t("cancel", { ns: "user" })}
            iconName="close"
          />
          <QuivrButton
            onClick={handleDeactivate}
            isLoading={isDeactivating}
            color="dangerous"
            label={t("confirm_deactivate", { ns: "user" })}
            iconName="delete"
          />
        </div>
      </div>
    </Modal>
  );
}; 