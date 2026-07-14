export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size,
      borderRadius: 10, background: "#0D0D0D",
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0,
    }}>
      <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 16 16" fill="none">
        <path d="M8 1L9.18 6.18L14 7L9.18 7.82L8 13L6.82 7.82L2 7L6.82 6.18L8 1Z" fill="#FFFFFF" />
      </svg>
    </div>
  );
}
