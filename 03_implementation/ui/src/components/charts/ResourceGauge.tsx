import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";
import { tokens } from "../../styles/tokens";

/**
 * Radial percent gauge per visual contract: thin ring, percent in the center,
 * tone derived from the value (green < 60 → amber 60-85 → red > 85).
 */
export function ResourceGauge({
  value,
  label,
}: {
  /** 0-100. */
  value: number;
  label: string;
}) {
  const tone = pickTone(value);
  return (
    <div className="flex flex-col items-center justify-center w-full h-full">
      <div className="relative w-24 h-24">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            barSize={6}
            data={[{ value, fill: tone }]}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar
              dataKey="value"
              background={{ fill: "#1f2a44" }}
              cornerRadius={3}
              isAnimationActive={false}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-fg">
          {Math.round(value)}%
        </div>
      </div>
      <div className="text-muted text-xs mt-1">{label}</div>
    </div>
  );
}

function pickTone(v: number): string {
  if (v >= 85) return tokens.chartColors.red;
  if (v >= 60) return tokens.chartColors.amber;
  return tokens.chartColors.green;
}
