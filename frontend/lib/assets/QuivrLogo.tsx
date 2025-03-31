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
  const [src, setSrc] = useState<string>("/traphaco.jpg");

  useEffect(() => {
    if (color === "primary") {
      setSrc("/traphaco.jpg");
    } else if (color === "accent") {
      setSrc("/traphaco.jpg");
    } else if (color === "black") {
      setSrc("/traphaco.jpg");
    } else {
      setSrc("/traphaco.jpg");
    }
  }, [color]);

  return <Image src={src} alt='Traphaco.AI Logo' width={size} height={size} />;
};
