import type { MascotPose } from "../components/Mascot";

/** 根据决策评级返回最合适的 Dromy 情绪动作。
 *
 *  buy / 买入          → profitable（满眼收益）
 *  overweight / 增持   → confident（充满信心）
 *  sell / 卖出         → thinking（谨慎思考）
 *  underweight / 减持  → thinking
 *  hold / neutral / 持有 / 中性 → thinking（持观望）
 */
export function decisionPose(rating?: string | null): MascotPose {
  const r = rating?.trim().toLowerCase() ?? "";
  if (r.includes("buy") || r.includes("买入")) return "profitable";
  if (r.includes("overweight") || r.includes("增持")) return "confident";
  if (r.includes("sell") || r.includes("卖出")) return "thinking";
  if (r.includes("underweight") || r.includes("减持")) return "thinking";
  return "thinking"; // hold / neutral / 持有 / 中性
}
