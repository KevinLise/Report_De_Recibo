type Props = { text: string };

export function Report({ text }: Props) {
  if (!text) return null;
  return <p className="report">{text}</p>;
}
