import { Tag } from "antd";
const COLORS = ["blue", "gold", "orange", "red"];
const LABELS = ["低", "中", "高", "严重"];
export default function RiskBadge({ level }: { level: number }) {
  return <Tag color={COLORS[level]}>{LABELS[level]}</Tag>;
}
