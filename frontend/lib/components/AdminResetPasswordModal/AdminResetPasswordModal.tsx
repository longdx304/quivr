import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { useUserApi } from "@/lib/api/user/useUserApi";
import { AdminResetPasswordRequest } from "@/lib/api/user/user";
import { Modal } from "@/lib/components/ui/Modal/Modal";
import { TextInput } from "@/lib/components/ui/TextInput/TextInput";

import styles from "./AdminResetPasswordModal.module.scss";

import Button from "../ui/Button";

type ResetPasswordFormProps = {
  new_password: string;
  confirm_password: string;
};

type AdminResetPasswordModalProps = {
  isOpen: boolean;
  setOpen: (isOpen: boolean) => void;
  userId: string;
  userEmail: string;
  onSuccess?: () => void;
};

export const AdminResetPasswordModal = ({
  isOpen,
  setOpen,
  userId,
  userEmail,
  onSuccess,
}: AdminResetPasswordModalProps): JSX.Element => {
  const { t } = useTranslation(["user"]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const { adminResetPassword } = useUserApi();

  const methods = useForm<ResetPasswordFormProps>({
    defaultValues: {
      new_password: "",
      confirm_password: "",
    },
    mode: "onChange",
  });

  const { register, handleSubmit, formState, watch, reset } = methods;
  const { errors } = formState;

  const newPassword = watch("new_password");
  const confirmPassword = watch("confirm_password");

  const onSubmit = async (data: ResetPasswordFormProps): Promise<void> => {
    try {
      setIsSubmitting(true);
      setError(null);

      const passwordData: AdminResetPasswordRequest = {
        user_id: userId,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      };

      await adminResetPassword(passwordData);
      setSuccess(true);

      // Close modal after a delay
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        reset();
        if (onSuccess) {
          onSuccess();
        }
      }, 2000);

    } catch (error) {
      console.error("Error resetting password:", error);
      setError(
        error instanceof Error
          ? error.message
          : "Failed to reset password"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = (): void => {
    reset();
    setError(null);
    setSuccess(false);
    setOpen(false);
  };

  return (
    <FormProvider {...methods}>
      <Modal
        title={t("admin_reset_password", { ns: "user" })}
        isOpen={isOpen}
        setOpen={setOpen}
        size="normal"
        CloseTrigger={
          <div className={styles.actions}>
            <Button type="button" variant="secondary" onClick={handleCancel}>
              {t("cancel", { ns: "user" })}
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              onClick={handleSubmit(onSubmit)}
              disabled={success}
            >
              {success ? t("success", { ns: "user" }) : t("reset_password", { ns: "user" })}
            </Button>
          </div>
        }
      >
        <div className={styles.reset_password_form}>
          {error && <div className={styles.error_message}>{error}</div>}
          {success && (
            <div className={styles.success_message}>
              {t("password_reset_success", { ns: "user" })}
            </div>
          )}
          
          <div className={styles.user_info}>
            <p><strong>{t("reset_password_for", { ns: "user" })}:</strong> {userEmail}</p>
          </div>

          <div className={styles.form_fields}>
            <div className={styles.form_field}>
              <label htmlFor="new_password">
                {t("new_password", { ns: "user" })}
              </label>
              <TextInput
                label={t("new_password", { ns: "user" })}
                inputValue={newPassword}
                setInputValue={(value) => methods.setValue("new_password", value)}
                type="password"
                {...register("new_password", {
                  required: t("new_pass_required", { ns: "user" }),
                  minLength: {
                    value: 6,
                    message: t("new_pass_least_6", { ns: "user" })
                  }
                })}
              />
              {errors.new_password && (
                <span className={styles.error}>{errors.new_password.message}</span>
              )}
            </div>

            <div className={styles.form_field}>
              <label htmlFor="confirm_password">
                {t("confirm_password", { ns: "user" })}
              </label>
              <TextInput
                label={t("confirm_password", { ns: "user" })}
                inputValue={confirmPassword}
                setInputValue={(value) => methods.setValue("confirm_password", value)}
                type="password"
                {...register("confirm_password", {
                  required: t("confirm_password_required", { ns: "user" }),
                  validate: (value) =>
                    value === newPassword || t("new_pass_confirmed", { ns: "user" })
                })}
              />
              {errors.confirm_password && (
                <span className={styles.error}>{errors.confirm_password.message}</span>
              )}
            </div>
          </div>
        </div>
      </Modal>
    </FormProvider>
  );
}; 