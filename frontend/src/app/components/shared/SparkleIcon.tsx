export function SparkleIcon({ size = 14, color = "#0D0D0D" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M8 1L9.18 6.18L14 7L9.18 7.82L8 13L6.82 7.82L2 7L6.82 6.18L8 1Z" fill={color} />
    </svg>
  );
}
