import type { ReactNode } from "react";
import { cn } from "../lib/format";
import working from "../assets/mascot/poses/mascot-working.png";
import celebrating from "../assets/mascot/poses/mascot-celebrating.png";
import confident from "../assets/mascot/poses/mascot-confident.png";
import thinking from "../assets/mascot/poses/mascot-thinking.png";
import profitable from "../assets/mascot/poses/mascot-profitable.png";

export type MascotPose =
  | "working"
  | "celebrating"
  | "confident"
  | "thinking"
  | "profitable";

export type MascotAnimation =
  | "float"
  | "bob"
  | "pop"
  | "breathe"
  | "none";

const POSE_META: Record<
  MascotPose,
  { src: string; alt: string }
> = {
  working: {
    src: working,
    alt: "Dromy 正在电脑前分析行情",
  },
  celebrating: {
    src: celebrating,
    alt: "Dromy 在庆祝分析完成",
  },
  confident: {
    src: confident,
    alt: "Dromy 充满信心",
  },
  thinking: {
    src: thinking,
    alt: "Dromy 正在思考",
  },
  profitable: {
    src: profitable,
    alt: "Dromy 眼中满是上涨的利润",
  },
};

const animationClass: Record<MascotAnimation, string> = {
  float: "animate-float",
  bob: "animate-bob",
  pop: "animate-pop",
  breathe: "breathe",
  none: "",
};

interface MascotProps {
  pose: MascotPose;
  animation?: MascotAnimation;
  size?: number;
  className?: string;
  alt?: string;
}

/** Dromy — DromX 品牌 IP 形象。
 *
 *  pose        动作（working / celebrating / confident / thinking / profitable）
 *  animation   预设动画：float 漂浮、bob 雀跃、pop 入场、breathe 呼吸、none 无动画
 *  size        显示宽度（px），高度按比例自适应
 */
export function Mascot({
  pose,
  animation = "float",
  size = 160,
  className,
  alt,
}: MascotProps) {
  const meta = POSE_META[pose];
  return (
    <img
      src={meta.src}
      alt={alt ?? meta.alt}
      width={size}
      className={cn(
        "h-auto object-contain drop-shadow-[0_20px_48px_rgba(1,4,9,0.55)]",
        animationClass[animation],
        className,
      )}
      style={{ width: size }}
    />
  );
}

/** 带标题文案的 mascot 场景，用于空状态 / loading / 结果反馈。 */
export function MascotScene({
  pose,
  animation = "float",
  size = 160,
  title,
  body,
  className,
  children,
}: {
  pose: MascotPose;
  animation?: MascotAnimation;
  size?: number;
  title?: React.ReactNode;
  body?: React.ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        className,
      )}
    >
      <Mascot pose={pose} animation={animation} size={size} />
      {title && (
        <div className="mt-5 font-display text-lg font-semibold text-[var(--color-ink)]">
          {title}
        </div>
      )}
      {body && (
        <p className="mt-1 max-w-[40ch] text-sm leading-relaxed text-[var(--color-ink-soft)]">
          {body}
        </p>
      )}
      {children}
    </div>
  );
}
