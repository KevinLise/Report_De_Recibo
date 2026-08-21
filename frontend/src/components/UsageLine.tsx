import type { Usage } from "../api/types";

export function UsageLine({ usage }: { usage: Usage }) {
  if (usage.cache_hit) {
    return <p className="usage">cache</p>;
  }
  return (
    <p className="usage">
      {usage.tokens_in} in · {usage.tokens_out} out
    </p>
  );
}
