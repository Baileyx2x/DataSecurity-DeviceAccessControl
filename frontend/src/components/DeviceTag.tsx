import { Tag } from "antd";
export default function DeviceTag({ category }: { category: string }) {
  const m = { white: "green", black: "red", unknown: "default" } as Record<string, string>;
  return <Tag color={m[category]}>{category}</Tag>;
}
