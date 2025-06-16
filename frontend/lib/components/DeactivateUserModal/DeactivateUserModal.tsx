import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useUserApi } from "@/lib/api/user/useUserApi";
import { DeactivateUserRequest } from "@/lib/api/user/user";
import { Modal } from "@/lib/components/ui/Modal/Modal";
import { QuivrButton } from "@/lib/components/ui/QuivrButton/QuivrButton";
import { useToast } from "@/lib/hooks/useToast";

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
  const { publish } = useToast();

  const handleDeactivate = async (): Promise<void> => {
    try {
      setIsDeactivating(true);
      setError(null);

      const deactivateData: DeactivateUserRequest = {
        user_id: userId,
      };

      await deactivateUser(deactivateData);

      // Show success toast
      publish({
        variant: "success",
        text: t("deactivate_user_success_toast", {
          defaultValue: `User ${userName} (${userEmail}) has been deactivated successfully!`,
        }),
      });

      // Close modal and call success callback
      setOpen(false);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error("Error deactivating user:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to deactivate user";
      setError(errorMessage);

      // Show error toast
      publish({
        variant: "danger",
        text: t("deactivate_user_error_toast", {
          defaultValue: `Failed to deactivate user ${userName}: ${errorMessage}`,
        }),
      });
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
      title={t("deactivate_user", { defaultValue: "Deactivate User" })}
      isOpen={isOpen}
      setOpen={setOpen}
      size="auto"
      CloseTrigger={<div />}
    >
      <div className={styles.modal_wrapper}>
        <div className={styles.warning_message}>
          <h3>
            {t("confirm_deactivate", { defaultValue: "Confirm Deactivation" })}
          </h3>
          <div className={styles.user_info}>
            <p>
              <strong>{t("name", { defaultValue: "Name" })}:</strong> {userName}
            </p>
            <p>
              <strong>{t("email", { defaultValue: "Email" })}:</strong>{" "}
              {userEmail}
            </p>
          </div>
          <p className={styles.warning_text}>
            {t("deactivate_user_warning", {
              defaultValue:
                "This action cannot be undone. Are you sure you want to deactivate this user?",
            })}
          </p>
        </div>

        {error && <div className={styles.error_message}>{error}</div>}

        <div className={styles.buttons}>
          <QuivrButton
            onClick={handleCancel}
            color="primary"
            label={t("cancel", { defaultValue: "Cancel" })}
            iconName="close"
          />
          <QuivrButton
            onClick={handleDeactivate}
            isLoading={isDeactivating}
            color="dangerous"
            label={t("confirm_deactivate", {
              defaultValue: "Confirm Deactivation",
            })}
            iconName="delete"
          />
        </div>
      </div>
    </Modal>
  );
};
