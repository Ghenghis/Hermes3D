import { Line, LineChart, ResponsiveContainer } from "recharts";
import { tokens } from "../../styles/tokens";

/**
 * Tiny line chart for KPI cards. Accepts a flat number array (no labels —
 * sparklines are visual cues, not detailed charts).
 */
export function Sparkline({
  data,
  color = tokens.chartColors.cyan,
}: {
  data: number[];
  color?: string;
}) {
  const series = data.map((y, i) => ({ x: i, y }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={series} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
        <Line
          type="monotone"
          dataKey="y"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
