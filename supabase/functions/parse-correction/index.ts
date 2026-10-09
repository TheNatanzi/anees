// parse-correction (PG-37; Medi 2026-10-08 "Can we turn this into just 1 box and we can write the correction"): when
// the rule layer in docs/js/correction-parse.js is not sure what his typed fix means, the Lessons page asks this for
// ONE cheap Claude Haiku read and shows the answer as chips he confirms before Send. Nothing is written to the
// corrections table here (the page saves the row, raw text included). Every paid call is one api_spend row
// (service anthropic, note "parse-correction ..."); scripts/correction_parse.py mirrors those rows into data/budget.json
// and the run log so the AI-paid-logged check sees them. Today's spend stays under DAILY_CAP_USD. No key set ->
// {status: "no-key"} and the page saves his words as a note; the hourly job reads it later with the same prompt.
// The prompt text is scripts/correction_parse_prompt.md, shipped here as prompt.ts (scripts/correction_parse.py build).
// POST {text, line, who, t} -> {status, items, model, cost_usd}
import { createClient } from "npm:@supabase/supabase-js@2";
import { PROMPT } from "./prompt.ts";

const MODEL = "claude-haiku-5-5";
const DAILY_CAP_USD = 0.5;
const IN_PER_M = 0.10, OUT_PER_M = 0.50;          // Claude Haiku 5.5 list price (prompts under 100K tokens)
const ORIGINS = ["https://thenatanzi.github.io", "http://localhost", "http://127.0.0.1"];

function cors(origin: string | null) {
  const ok = origin && ORIGINS.some((o) => origin === o || origin.startsWith(o + ":"));
  return { "Access-Control-Allow-Origin": ok ? origin! : ORIGINS[0], "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
           "Access-Control-Allow-Methods": "POST, OPTIONS", "Content-Type": "application/json" };
}
const json = (H: Record<string, string>, body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: H });
const mmss = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

Deno.serve(async (req) => {
  const H = cors(req.headers.get("origin"));
  if (req.method === "OPTIONS") return new Response("ok", { headers: H });
  if (req.method !== "POST") return json(H, { error: "POST only" }, 405);
  let body: { text?: string; line?: string; who?: string; t?: number } = {};
  try { body = await req.json(); } catch { /* empty */ }
  const text = String(body.text || "").trim().slice(0, 600), line = String(body.line || "").slice(0, 600);
  const who = body.who === "Amal" ? "Amal" : "Medi", t = Number(body.t) || 0;
  if (!text) return json(H, { error: "text missing" }, 400);
  const key = Deno.env.get("ANTHROPIC_API_KEY");
  if (!key) return json(H, { status: "no-key", items: [] });

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const since = new Date(); since.setUTCHours(0, 0, 0, 0);
  const { data: spent } = await sb.from("api_spend").select("usd").eq("service", "anthropic").gte("ts", since.toISOString());
  if ((spent || []).reduce((s: number, x: { usd: number }) => s + (x.usd || 0), 0) >= DAILY_CAP_USD) return json(H, { status: "cap", items: [] });

  const prompt = PROMPT.replace("{who}", who).replace("{mmss}", mmss(t)).replace("{line}", line || "(empty)").replace("{text}", text);
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, max_tokens: 400, output_config: { effort: "low" }, messages: [{ role: "user", content: prompt }] }),
  });
  if (!r.ok) return json(H, { status: "error", why: `anthropic ${r.status}`, items: [] });
  const d = await r.json();
  const u = d.usage || {};
  const cost = Math.round(((u.input_tokens || 0) * IN_PER_M / 1e6 + (u.output_tokens || 0) * OUT_PER_M / 1e6) * 1e6) / 1e6;
  await sb.from("api_spend").insert({ service: "anthropic", usd: cost, note: `parse-correction ${who} ${mmss(t)} (${(u.input_tokens || 0) + (u.output_tokens || 0)} tokens, ${d.model || MODEL})` });
  const out = (d.content || []).filter((c: { type: string }) => c.type === "text").map((c: { text: string }) => c.text).join("");
  let items: unknown[] = [];
  try { const m = out.match(/\{[\s\S]*\}/); items = m ? (JSON.parse(m[0]).items || []) : []; } catch { items = []; }
  return json(H, { status: "ok", items, model: d.model || MODEL, cost_usd: cost });
});
