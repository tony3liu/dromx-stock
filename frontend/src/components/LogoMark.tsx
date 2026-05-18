type LogoMarkProps = {
  className?: string;
  size?: number;
};

function LogoMark({ className, size = 32 }: LogoMarkProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height={size}
      viewBox="0 0 64 64"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="2"
        y="2"
        width="60"
        height="60"
        rx="16"
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.38"
      />
      <path
        d="M18 18V46"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5.5"
      />
      <path
        d="M18 18H30C36.627 18 42 23.373 42 30C42 36.627 36.627 42 30 42H18"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5.5"
      />
      <path
        d="M36 18L48 46"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5.5"
      />
      <path
        d="M48 18L36 46"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5.5"
      />
    </svg>
  );
}

export default LogoMark;
