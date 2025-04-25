import Image from "next/image";
import { useEffect, useState } from "react";

interface QuivrLogoProps {
  size: number;
  color?: "white" | "black" | "primary" | "accent";
}

export const QuivrLogo = ({
  size,
  color = "white",
}: QuivrLogoProps): JSX.Element => {
  const [src, setSrc] = useState<string>("/medzavy.webp");

  useEffect(() => {
    if (color === "primary") {
      setSrc("/medzavy.webp");
    } else if (color === "accent") {
      setSrc("/medzavy.webp");
    } else if (color === "black") {
      setSrc("/medzavy.webp");
    } else {
      setSrc("/medzavy.webp");
    }
  }, [color]);

  return <Image src={src} alt="Dobbie Logo" width={size} height={size} />;
};
