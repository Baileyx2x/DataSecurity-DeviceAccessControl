export const RISK_COLORS = ["blue", "gold", "orange", "red"] as const;
export const RISK_NAMES = ["低", "中", "高", "严重"] as const;

export const CATEGORY_COLOR: Record<string, string> = {
  white: "green",
  black: "red",
  unknown: "default",
};
export const CATEGORY_NAME: Record<string, string> = {
  white: "白名单",
  black: "黑名单",
  unknown: "未知",
};

export const STATUS_COLOR: Record<string, string> = {
  online: "green",
  offline: "default",
  blocked: "red",
};
