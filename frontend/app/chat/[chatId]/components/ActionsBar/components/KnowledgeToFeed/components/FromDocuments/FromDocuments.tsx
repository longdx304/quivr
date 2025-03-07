import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "@/lib/components/ui/Icon/Icon";
import { useKnowledgeToFeedContext } from "@/lib/context/KnowledgeToFeedProvider/hooks/useKnowledgeToFeedContext";
import { useCustomDropzone } from "@/lib/hooks/useDropzone";

import styles from "./FromDocuments.module.scss";

export const FromDocuments = (): JSX.Element => {
	const { t } = useTranslation(["knowledge"]);

	const [dragging, setDragging] = useState<boolean>(false);
	const { getRootProps, getInputProps, open } = useCustomDropzone();
	const { knowledgeToFeed } = useKnowledgeToFeedContext();

	useEffect(() => {
		setDragging(false);
	}, [knowledgeToFeed]);

	return (
		<div
			className={`
      ${styles.from_document_wrapper}
      ${dragging ? styles.dragging : ""}
      `}
			{...getRootProps()}
			onDragOver={() => setDragging(true)}
			onDragLeave={() => setDragging(false)}
			onMouseLeave={() => setDragging(false)}
			onClick={open}
		>
			<div className={styles.box_content}>
				<Icon name="upload" size="big" color={dragging ? "accent" : "black"} />
				<div className={styles.input}>
					<div className={styles.clickable}>
						<span>{t("knowledge:choose_document")}</span>
						<input {...getInputProps()} />
					</div>
					<span>{t("knowledge:or_drag_it_here")}</span>
				</div>
			</div>
		</div>
	);
};
