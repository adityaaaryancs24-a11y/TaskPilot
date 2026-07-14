type PastelVariant = "pink" | "yellow" | "green" | "blue" | "purple" | "orange" | "default";

const PASTEL_MAP: Record<string, { bg: string; border: string }> = {
  pink: { bg: "#F7C5E6", border: "#F0A8D6" },
  yellow: { bg: "#F5D66E", border: "#E8C84A" },
  green: { bg: "#BFD78D", border: "#A8C870" },
  blue: { bg: "#C9D8FF", border: "#A8C0F0" },
  purple: { bg: "#DCC7F7", border: "#C8A8E8" },
  orange: { bg: "#FAD6B3", border: "#F0C090" },
  default: { bg: "#FFFFFF", border: "#E9E4D8" },
};

export function Card({
  children, style, className, variant = "default", shadow = false,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  variant?: PastelVariant;
  shadow?: boolean;
}) {
  const v = PASTEL_MAP[variant];
  return (
    <div
      className={className}
      style={{
        background: v.bg,
        border: `1px solid ${v.border}`,
        borderRadius: 18,
        padding: "20px 22px",
        boxShadow: shadow ? "0 4px 24px rgba(0,0,0,0.04)" : "none",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
