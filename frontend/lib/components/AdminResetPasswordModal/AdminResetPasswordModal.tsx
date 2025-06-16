import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { useUserApi } from "@/lib/api/user/useUserApi";
import { AdminResetPasswordRequest } from "@/lib/api/user/user";
import { Modal } from "@/lib/components/ui/Modal/Modal";
import { TextInput } from "@/lib/components/ui/TextInput/TextInput";
import { useToast } from "@/lib/hooks/useToast";

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
  const { publish } = useToast();

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

      // Show success toast
      publish({
        variant: "success",
        text: t("reset_password_success_toast", {
          defaultValue: `Password for ${userEmail} has been reset successfully!`,
        }),
      });

      // Close modal after a delay
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        reset();
        if (onSuccess) {
          onSuccess();
        }
      }, 2000);
    } catch (err) {
      console.error("Error resetting password:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to reset password";
      setError(errorMessage);

      // Show error toast
      publish({
        variant: "danger",
        text: t("reset_password_error_toast", {
          defaultValue: `Failed to reset password for ${userEmail}: ${errorMessage}`,
        }),
      });
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
        title={t("reset_password", { defaultValue: "Reset Password" })}
        isOpen={isOpen}
        setOpen={setOpen}
        size="normal"
        CloseTrigger={
          <div className={styles.actions}>
            <Button type="button" variant="secondary" onClick={handleCancel}>
              {t("cancel", { defaultValue: "Cancel" })}
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              onClick={() => void handleSubmit(onSubmit)()}
              disabled={success}
            >
              {success
                ? t("success", { defaultValue: "Success" })
                : t("reset_password", { defaultValue: "Reset Password" })}
            </Button>
          </div>
        }
      >
        <div className={styles.reset_password_form}>
          {error && <div className={styles.error_message}>{error}</div>}
          {success && (
            <div className={styles.success_message}>
              {t("reset_password_success", {
                defaultValue: "Password reset successfully",
              })}
            </div>
          )}

          <div className={styles.user_info}>
            <p>
              <strong>
                {t("reset_password_for", {
                  defaultValue: "Reset password for",
                })}
                :
              </strong>{" "}
              {userEmail}
            </p>
          </div>

          <div className={styles.form_fields}>
            <div className={styles.form_field}>
              <label htmlFor="new_password">
                {t("new_password", { defaultValue: "New Password" })}
              </label>
              <TextInput
                label={t("new_password", { defaultValue: "New Password" })}
                inputValue={newPassword}
                setInputValue={(value) =>
                  methods.setValue("new_password", value)
                }
                crypted={true}
                {...register("new_password", {
                  required: t("new_pass_required", {
                    defaultValue: "New password is required",
                  }),
                  minLength: {
                    value: 6,
                    message: t("new_pass_least_6", {
                      defaultValue:
                        "New password must be at least 6 characters",
                    }),
                  },
                })}
              />
              {errors.new_password && (
                <span className={styles.error}>
                  {errors.new_password.message}
                </span>
              )}
            </div>

            <div className={styles.form_field}>
              <label htmlFor="confirm_password">
                {t("confirm_password", { defaultValue: "Confirm Password" })}
              </label>
              <TextInput
                label={t("confirm_password", {
                  defaultValue: "Confirm Password",
                })}
                inputValue={confirmPassword}
                setInputValue={(value) =>
                  methods.setValue("confirm_password", value)
                }
                crypted={true}
                {...register("confirm_password", {
                  required: t("confirm_password_required", {
                    defaultValue: "Confirm password is required",
                  }),
                  validate: (value) =>
                    value === newPassword ||
                    t("new_pass_confirmed", {
                      defaultValue: "Passwords do not match",
                    }),
                })}
              />
              {errors.confirm_password && (
                <span className={styles.error}>
                  {errors.confirm_password.message}
                </span>
              )}
            </div>
          </div>
        </div>
      </Modal>
    </FormProvider>
  );
};
