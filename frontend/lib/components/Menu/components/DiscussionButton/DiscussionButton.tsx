import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "@/lib/components/ui/Icon/Icon";
import { useSearchModalContext } from "@/lib/context/SearchModalProvider/hooks/useSearchModalContext";

import styles from "./DiscussionButton.module.scss";

export const DiscussionButton = (): JSX.Element => {
	const { t } = useTranslation(["translation"]);

	const [hovered, setHovered] = useState(false);
	const { setIsVisible } = useSearchModalContext();

	const handleClick = (event: React.MouseEvent<HTMLDivElement>) => {
		setIsVisible(true);
		event.nativeEvent.stopImmediatePropagation();
	};

	return (
		<div
			className={styles.button_wrapper}
			onMouseEnter={() => setHovered(true)}
			onMouseLeave={() => setHovered(false)}
			onClick={handleClick}
		>
			<div className={styles.left_wrapper}>
				<span>{t("new_thread", { ns: "translation" })}</span>
				<div className={styles.shortcuts_wrapper}>
					<div className={styles.shortcut}>⌘</div>
					<div className={styles.shortcut}>K</div>
				</div>
			</div>
			<Icon name="search" size="normal" color={hovered ? "primary" : "black"} />
		</div>
	);
};
