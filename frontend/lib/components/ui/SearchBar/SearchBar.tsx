import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { LuSearch } from "react-icons/lu";

import { Editor } from "@/app/chat/[chatId]/components/ActionsBar/components/ChatInput/components/ChatEditor/Editor/Editor";
import { useChatInput } from "@/app/chat/[chatId]/components/ActionsBar/components/ChatInput/hooks/useChatInput";
import { useChat } from "@/app/chat/[chatId]/hooks/useChat";
import { useChatContext } from "@/lib/context";
import { useBrainContext } from "@/lib/context/BrainProvider/hooks/useBrainContext";
import { useUserSettingsContext } from "@/lib/context/UserSettingsProvider/hooks/useUserSettingsContext";

import styles from "./SearchBar.module.scss";

import { CurrentBrain } from "../../CurrentBrain/CurrentBrain";
import { LoaderIcon } from "../LoaderIcon/LoaderIcon";

export const SearchBar = ({
	onSearch,
	newBrain,
}: {
	onSearch?: () => void;
	newBrain?: boolean;
}): JSX.Element => {
	const { t } = useTranslation(["chat"]);

	const [searching, setSearching] = useState(false);
	const [isDisabled, setIsDisabled] = useState(true);
	const [placeholder, setPlaceholder] = useState(t("select_brain", { ns: "chat" }));
	const { message, setMessage } = useChatInput();
	const { setMessages } = useChatContext();
	const { addQuestion } = useChat();
	const { currentBrain, setCurrentBrainId } = useBrainContext();
	const { remainingCredits } = useUserSettingsContext();

	useEffect(() => {
		setCurrentBrainId(null);
	}, []);

	useEffect(() => {
		setIsDisabled(message === "");
	}, [message]);

	useEffect(() => {
		setPlaceholder(currentBrain ? t("ask_question", { ns: "chat" }) : t("select_brain", { ns: "chat" }));
	}, [currentBrain]);

	const submit = async (): Promise<void> => {
		if (!!remainingCredits && !!currentBrain && !searching) {
			setSearching(true);
			setMessages([]);
			try {
				if (onSearch) {
					onSearch();
				}
				await addQuestion(message);
			} catch (error) {
				console.error(error);
			} finally {
				setSearching(false);
			}
		}
	};

	return (
		<div
			className={`${styles.search_bar_wrapper} ${newBrain ? styles.new_brain : ""
				}`}
		>
			<CurrentBrain
				allowingRemoveBrain={true}
				remainingCredits={remainingCredits}
				isNewBrain={newBrain}
			/>
			<div
				className={`${styles.editor_wrapper} ${!remainingCredits ? styles.disabled : ""
					} ${currentBrain ? styles.current : ""}`}
			>
				<Editor
					message={message}
					setMessage={setMessage}
					onSubmit={() => void submit()}
					placeholder={placeholder}
				></Editor>
				{searching ? (
					<LoaderIcon size="big" color="accent" />
				) : (
					<LuSearch
						className={`
          ${styles.search_icon}
          ${isDisabled || !remainingCredits || !currentBrain
								? styles.disabled
								: ""
							}
          `}
						onClick={() => void submit()}
					/>
				)}
			</div>
		</div>
	);
};
