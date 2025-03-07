import { useTranslation } from "react-i18next";

import { Icon } from "@/lib/components/ui/Icon/Icon";

import { ApiKeyConfig } from "./ApiKeyConfig";
import { InfoSection } from "./InfoSection/InfoSection";
import styles from "./Settings.module.scss";

import { StripePricingOrManageButton } from "../StripePricingOrManageButton";

const showTokensSettings = process.env.NEXT_PUBLIC_SHOW_TOKENS === "true";

type InfoDisplayerProps = {
	email: string;
	username: string;
	remainingCredits: number;
};

export const Settings = ({
	email,
	username,
	remainingCredits,
}: InfoDisplayerProps): JSX.Element => {
	const { t } = useTranslation(["translation"]);

	return (
		<div className={styles.settings_wrapper}>
			<span className={styles.title}>
				{t("general_settings_and_information", { ns: "translation" })}
			</span>
			<div className={styles.infos_wrapper}>
				<InfoSection iconName="email" title="Email">
					<span className={styles.bold}>{email}</span>
				</InfoSection>
				<InfoSection iconName="user" title="Username">
					<span className={styles.bold}>{username}</span>
				</InfoSection>
				{!!showTokensSettings && (
					<InfoSection iconName="coin" title="Remaining credits">
						<div className={styles.remaining_credits}>
							<span className={styles.credits}>{remainingCredits}</span>
							<Icon name="coin" color="gold" size="normal" />
						</div>
					</InfoSection>
				)}
				<InfoSection iconName="key" title="Dobbie API Key">
					<div className={styles.text_and_button}>
						<span className={styles.text}>
							{t("api_key_is_unique_identifier", { ns: "translation" })}
							<a
								href="https://api.quivr.app/docs"
								target="_blank"
								rel="noopener noreferrer"
								className={styles.link}
							>
								Dobbie&apos;s API.
							</a>
						</span>
						<div className={styles.button}>
							<ApiKeyConfig />
						</div>
					</div>
				</InfoSection>
				{!!showTokensSettings && (
					<InfoSection iconName="star" title="My plan" last={true}>
						<div className={styles.text_and_button}>
							<span className={styles.text}>
								Customize your subscription to best suit your needs. By
								upgrading to a premium plan, you gain access to a host of
								additional benefits, including significantly more chat credits
								and the ability to create more Brains.
							</span>
							<div className={styles.button}>
								<StripePricingOrManageButton small={true} />
							</div>
						</div>
					</InfoSection>
				)}
			</div>
		</div>
	);
};
