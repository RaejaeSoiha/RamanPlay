import type { Team } from "../types";
import { teamColors } from "../lib/helpers";
export function Badge({
  children,
  kind = "",
}: {
  children: React.ReactNode;
  kind?: string;
}) {
  return <span className={"badge " + kind}>{children}</span>;
}
export function Crest({
  team,
  small = false,
}: {
  team: Team;
  small?: boolean;
}) {
  const hasLogo = team.logo_url && team.logo_url.trim() !== "";
  return (
    <span className={"crest " + (small ? "small" : "")}>
      {hasLogo ? (
        <img
          src={team.logo_url}
          alt={team.name}
          className="crest-logo"
          onError={(e) => {
            e.currentTarget.style.display = "none";
            e.currentTarget.nextElementSibling?.classList.remove("hidden");
          }}
        />
      ) : null}
      <span
        className={"crest-fallback " + (hasLogo ? "hidden" : "")}
        style={{
          "--team": teamColors[team.abbreviation] || "#9eabc1",
        } as React.CSSProperties}
      >
        {team.abbreviation}
      </span>
    </span>
  );
}