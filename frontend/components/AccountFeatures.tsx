"use client";

import { useEffect, useState } from "react";
import type { ProviderAccount } from "../types";

type Account = { csrf_token: string; role: string };
type Household = { name: string; role: string; members: Array<{ id: number; display_name: string; role: string }> };

export default function AccountFeatures() {
  const [account, setAccount] = useState<Account | null>(null);
  const [providers, setProviders] = useState<ProviderAccount[]>([]);
  const [household, setHousehold] = useState<Household | null>(null);
  const [invite, setInvite] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [displayName, setDisplayName] = useState("");

  async function load() {
    const me = await fetch("/api/account/me").then((r) => r.json());
    setAccount(me);
    const [accounts, home] = await Promise.all([
      fetch("/api/provider-accounts").then((r) => r.json()),
      fetch("/api/household").then((r) => r.json()),
    ]);
    setProviders(accounts);
    setHousehold(home);
  }
  useEffect(() => { void load(); }, []);

  async function connect(provider: string) {
    if (!account) return;
    const response = await fetch(`/api/provider-accounts/${provider}/connect`, {
      method: "POST",
      headers: { "X-CSRF-Token": account.csrf_token },
    });
    const result = await response.json();
    if (result.url) window.location.assign(result.url);
  }
  async function createInvite() {
    if (!account) return;
    const response = await fetch("/api/household/invites", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": account.csrf_token },
      body: JSON.stringify({}),
    });
    if (response.ok) setInvite((await response.json()).code);
  }
  async function joinHousehold() {
    if (!account || !inviteCode.trim() || !displayName.trim()) return;
    const response = await fetch("/api/household/join", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": account.csrf_token },
      body: JSON.stringify({ code: inviteCode, display_name: displayName }),
    });
    if (response.ok) await load();
  }

  return (
    <>
      <section className="settings-panel provider-accounts">
        <h2>Provider Accounts</h2>
        <p>Connect only through official provider pages. RamanPlay never asks for or stores provider passwords.</p>
        <div className="subscriptions-grid">
          {providers.map((provider) => (
            <div className="subscription-row" key={provider.provider}>
              <div className="sub-info"><strong>{provider.name}</strong><small>{provider.status === "CONNECTED" ? "Connected" : "Not connected"}</small></div>
              <button className="secondary-button" onClick={() => connect(provider.provider)}>{provider.status === "CONNECTED" ? "Open provider" : "Connect"}</button>
            </div>
          ))}
        </div>
      </section>
      <section className="settings-panel household-panel">
        <h2>Family / Household</h2>
        <p>{household?.name || "Loading household…"}</p>
        <div className="subscriptions-grid">
          {household?.members.map((member) => <div className="subscription-row" key={member.id}><strong>{member.display_name}</strong><small>{member.role === "OWNER" ? "Owner" : "Family Member"}</small></div>)}
        </div>
        {household?.role === "OWNER" && <button className="secondary-button" onClick={createInvite}>Invite Family</button>}
        {invite && <p className="household-invite">One-time invite code: <strong>{invite}</strong></p>}
        <div className="household-join">
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Your name" />
          <input value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} placeholder="Household invite code" />
          <button className="secondary-button" onClick={joinHousehold}>Join Household</button>
        </div>
      </section>
    </>
  );
}
