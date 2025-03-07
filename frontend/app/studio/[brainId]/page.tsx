"use client";

import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader } from "@/lib/components/PageHeader/PageHeader";
import { UploadDocumentModal } from "@/lib/components/UploadDocumentModal/UploadDocumentModal";
import { useBrainContext } from "@/lib/context/BrainProvider/hooks/useBrainContext";
import { useKnowledgeToFeedContext } from "@/lib/context/KnowledgeToFeedProvider/hooks/useKnowledgeToFeedContext";
import { useSearchModalContext } from "@/lib/context/SearchModalProvider/hooks/useSearchModalContext";
import { ButtonType } from "@/lib/types/QuivrButton";

import { BrainManagementTabs } from "./BrainManagementTabs/BrainManagementTabs";
import { DeleteOrUnsubscribeConfirmationModal } from "./BrainManagementTabs/components/DeleteOrUnsubscribeModal/DeleteOrUnsubscribeConfirmationModal";
import { useBrainManagementTabs } from "./BrainManagementTabs/hooks/useBrainManagementTabs";
import { getBrainPermissions } from "./BrainManagementTabs/utils/getBrainPermissions";
import { useBrainManagement } from "./hooks/useBrainManagement";
import styles from "./page.module.scss";

const BrainsManagement = (): JSX.Element => {
	const { t } = useTranslation(["translation", "brain", "knowledge"]);

	const { brain } = useBrainManagement();
	const { setIsVisible } = useSearchModalContext();
	const {
		handleUnsubscribeOrDeleteBrain,
		isDeleteOrUnsubscribeModalOpened,
		setIsDeleteOrUnsubscribeModalOpened,
		isDeleteOrUnsubscribeRequestPending,
	} = useBrainManagementTabs(brain?.id);
	const { allBrains } = useBrainContext();
	const { isOwnedByCurrentUser } = getBrainPermissions({
		brainId: brain?.id,
		userAccessibleBrains: allBrains,
	});
	const { setShouldDisplayFeedCard } = useKnowledgeToFeedContext();
	const { setCurrentBrainId } = useBrainContext();

	const buttons: ButtonType[] = [
		{
			label: t("talkButton", { ns: "brain" }),
			color: "primary",
			onClick: () => {
				if (brain) {
					setIsVisible(true);
					setTimeout(() => setCurrentBrainId(brain.id));
				}
			},
			iconName: "chat",
		},
		{
			label: t("addKnowledgeTitle", { ns: "knowledge" }),
			color: "primary",
			onClick: () => {
				setShouldDisplayFeedCard(true);
			},
			iconName: "uploadFile",
			hidden: !isOwnedByCurrentUser || !brain?.max_files,
		},
		{
			label: isOwnedByCurrentUser ? t("deleteBrain", { ns: "brain" }) : t("unsubscribe_brain", { ns: "brain" }),
			color: "dangerous",
			onClick: () => {
				setIsDeleteOrUnsubscribeModalOpened(true);
			},
			iconName: "delete",
		},
	];

	useEffect(() => {
		if (brain) {
			setCurrentBrainId(brain.id);
		}
	}, [brain]);

	if (!brain) {
		return <></>;
	}

	return (
		<>
			<div className={styles.brain_management_wrapper}>
				<PageHeader
					iconName="brain"
					label={brain.name}
					buttons={buttons}
					snippetEmoji={brain.snippet_emoji}
					snippetColor={brain.snippet_color}
				/>
				<div className={styles.content_wrapper}>
					<BrainManagementTabs />
				</div>
			</div>
			<UploadDocumentModal />
			<DeleteOrUnsubscribeConfirmationModal
				isOpen={isDeleteOrUnsubscribeModalOpened}
				setOpen={setIsDeleteOrUnsubscribeModalOpened}
				onConfirm={() => void handleUnsubscribeOrDeleteBrain()}
				isOwnedByCurrentUser={isOwnedByCurrentUser}
				isDeleteOrUnsubscribeRequestPending={
					isDeleteOrUnsubscribeRequestPending
				}
			/>
		</>
	);
};

export default BrainsManagement;
