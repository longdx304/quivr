"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { CreateUserModal } from "@/lib/components/CreateUserModal/CreateUserModal";
import { ListAllUsers } from "@/lib/components/ListAllUsers";
import { PageHeader } from "@/lib/components/PageHeader/PageHeader";
import { ButtonType } from "@/lib/types/QuivrButton";

import styles from "./page.module.scss";

const Administrator = (): JSX.Element => {
  const { t } = useTranslation(["user"]);
  const [isCreateUserModalOpen, setIsCreateUserModalOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const buttons: ButtonType[] = [
    {
      label: t("create_user", { ns: "user" }),
      color: "primary",
      onClick: () => {
        setIsCreateUserModalOpen(true);
      },
      iconName: "user",
    },
  ];

  const handleUserCreated = () => {
    // Increment refresh trigger to cause ListAllUsers to re-render and fetch data
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className={styles.page_wrapper}>
      <div className={styles.page_header}>
        <PageHeader
          iconName='user'
          label={t("user_administration", { ns: "user" })}
          buttons={buttons}
        />
      </div>
      <div className={styles.content_wrapper}>
        <ListAllUsers key={refreshTrigger} />
      </div>
      <CreateUserModal
        isOpen={isCreateUserModalOpen}
        setOpen={setIsCreateUserModalOpen}
        onSuccess={handleUserCreated}
      />
    </div>
  );
};

export default Administrator;
