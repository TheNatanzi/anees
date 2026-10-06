// check-homework (Medi 2026-10-05, grill Q1): the AI's FIRST check of one typed homework answer from the Student tab -
// right / close / wrong + one reason, at once - written to homework_replies.ai with the service key. Amal confirms or
// overrules on her Tutor page (homework_verdicts); only her word counts, and her overrules are fed back here as examples
// (S6: a correction becomes a rule the checker meets next time). Same guards as `grade`: the reply must exist and be
// unchecked, today's OpenAI spend (api_spend) stays under DAILY_CAP_USD, the model sees only the task, his answer, the
// target words (her spelling) and her latest overrules. POST {reply_id} -> {ai}
import { createClient } from "npm:@supabase/supabase-js@2";
import { PAIRS } from "./pairs.ts";   // her real WhatsApp corrections (same file as `grade`)

const MODEL = "gpt-5.5";
const DAILY_CAP_USD = 0.5;
const ORIGINS = ["https://thenatanzi.github.io", "http://localhost", "http://127.0.0.1"];
const KIND = { translate: "translate a sentence", create: "make a sentence with the given words", question: "answer a question" } as Record<string, string>;

function cors(origin: string | null) {
  const ok = origin && ORIGINS.some((o) => origin === o || origin.startsWith(o + ":"));
  return { "Access-Control-Allow-Origin": ok ? origin! : ORIGINS[0], "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
           "Access-Control-Allow-Methods": "POST, OPTIONS", "Content-Type": "application/json" };
}
const cost = (u: { prompt_tokens?: number; completion_tokens?: number }) =>
  Math.round(((u.prompt_tokens || 0) * 5 / 1e6 + (u.completion_tokens || 0) * 20 / 1e6) * 1e4) / 1e4;
const json = (H: Record<string, string>, body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: H });

Deno.serve(async (req) => {
  const H = cors(req.headers.get("origin"));
  if (req.method === "OPTIONS") return new Response("ok", { headers: H });
  if (req.method !== "POST") return json(H, { error: "POST only" }, 405);
  let body: { reply_id?: string } = {};
  try { body = await req.json(); } catch { /* empty */ }
  if (!body.reply_id) return json(H, { error: "reply_id missing" }, 400);

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: r } = await sb.from("homework_replies").select("*").eq("id", body.reply_id).maybeSingle();
  if (!r) return json(H, { error: "no such reply" }, 404);
  if (r.ai) return json(H, { ai: r.ai, cached: true });
  const { data: t } = await sb.from("homework_tasks").select("*").eq("id", r.task_id).maybeSingle();
  if (!t || !(t.kind in KIND)) return json(H, { error: "no such task" }, 404);
  // claim first: two taps on the same answer must not both pay
  const { data: claimed } = await sb.from("homework_replies").update({ ai_at: new Date().toISOString() }).eq("id", r.id).is("ai_at", null).select("id");
  if (!claimed || !claimed.length) return json(H, { error: "already checking" }, 409);
  const unchecked = async (reason: string) => {
    const ai = { verdict: "ungraded", reason, fixed: "", model: null, cost_usd: 0 };
    await sb.from("homework_replies").update({ ai, ai_at: new Date().toISOString() }).eq("id", r.id);
    return json(H, { ai });
  };

  const since = new Date(); since.setUTCHours(0, 0, 0, 0);
  const { data: spent } = await sb.from("api_spend").select("usd").gte("ts", since.toISOString());
  if ((spent || []).reduce((s: number, x: { usd: number }) => s + (x.usd || 0), 0) >= DAILY_CAP_USD) return unchecked("Today's checking budget is used up. Amal will still see your answer.");

  // her words for the task (create: the words he must use; translate: words of the sentence that are on her Doc)
  const want = (t.kind === "create" ? (t.words || []) : String(t.prompt || "").split(/[^\p{L}\p{N}'’]+/u)).map((w: string) => String(w).trim()).filter(Boolean).slice(0, 40);
  const { data: words } = want.length
    ? await sb.from("words").select("key,arabizi,arabic,english,house_spelling").or(want.map((w: string) => `arabizi.ilike.${w.replace(/[%,()]/g, "")},english.ilike.${w.replace(/[%,()]/g, "")}`).join(",")).limit(40)
    : { data: [] };
  const targets = (words || []).map((w) => `${w.house_spelling || w.arabizi} | ${w.arabic} | ${w.english}`).join("\n");
  // S6: her overrules of earlier checks are the bar (the latest 12, with her note / fix)
  const { data: overs } = await sb.from("homework_verdicts").select("reply_id,verdict,note,fix,created_at").eq("kind", "verdict").eq("agrees", false).order("created_at", { ascending: false }).limit(12);
  const ids = (overs || []).map((o) => o.reply_id);
  const { data: oreps } = ids.length ? await sb.from("homework_replies").select("id,task_id,answer,ai").in("id", ids) : { data: [] };
  const { data: otasks } = oreps && oreps.length ? await sb.from("homework_tasks").select("id,kind,prompt,direction,words").in("id", oreps.map((x) => x.task_id)) : { data: [] };
  const bar = PAIRS.map((p: { english: string; answer: string; amal: string; note: string }) => `Prompt: ${p.english}\nMedi: ${p.answer}\nAmal: ${p.amal}${p.note ? `  (${p.note})` : ""}`).join("\n\n");
  const examples = (overs || []).map((o) => {
    const rep = (oreps || []).find((x) => x.id === o.reply_id), tk = rep && (otasks || []).find((x) => x.id === rep.task_id);
    if (!rep || !tk) return "";
    return `Task: ${KIND[tk.kind]}${tk.direction ? ` (${tk.direction === "en_ar" ? "English to Arabic" : "Arabic to English"})` : ""}: ${tk.prompt}${tk.words ? ` [words: ${(tk.words || []).join(", ")}]` : ""}\nMedi: ${rep.answer}\nAI said: ${rep.ai?.verdict || "?"}. Amal says: ${o.verdict}${o.fix ? ` - say "${o.fix}"` : ""}${o.note ? ` (${o.note})` : ""}`;
  }).filter(Boolean).join("\n\n");

  const dir = t.direction === "ar_en" ? "He translates spoken Palestinian Arabic INTO English." : t.direction === "en_ar" ? "He translates the English sentence INTO spoken Palestinian Arabic." : "";
  const prompt = `You are Amal, a Palestinian Arabic tutor, giving the FIRST check of one typed homework answer from your adult student Medi.
He writes spoken Palestinian Arabic in Arabizi (6=ط 7=ح 3=ع 2=ء/ق 5=خ 9=ص 8=غ) or in Arabic letters; either is fine. You are terse,
only what needs fixing, never a lecture. Spelling variants of the same sound are NOT errors (kteer/ktir, ma3/ma3a, e/i, o/u);
MSA where he could have said the dialect word is a small note, not wrong. Amal's real verdict comes after yours; her past
overrules below set the bar - follow them.

Task kind: ${KIND[t.kind]}. ${dir}
${t.kind === "create" ? `Words he must use (Amal's spelling): ${(t.words || []).join(", ")}` : ""}
${t.kind === "question" && t.context ? `Context Amal gave: ${t.context}` : ""}
Amal's words that may belong here (her spelling | Arabic | English):
${targets || "(none matched)"}

Your real corrections from the chat (the bar you set):
${bar}
${examples ? `\nAmal's earlier overrules of this checker (learn from them):\n${examples}\n` : ""}
Prompt: ${t.prompt}
Medi: ${r.answer}

Return ONLY JSON: {"verdict": "right" | "close" | "wrong", "reason": "<= 20 words, Amal's voice, say what to fix", "fixed": "<how to say it, in Medi's script (Arabizi or Arabic letters), or the same text when right>"}
"right" = you would reply Yes / Tmm. "close" = one small fix (a word, an ending, a preposition). "wrong" = the meaning, the main verb or a required word is off.`;

  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST", headers: { Authorization: `Bearer ${Deno.env.get("OPENAI_API_KEY")}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, messages: [{ role: "user", content: prompt }], response_format: { type: "json_object" } }),
  });
  if (!resp.ok) {
    const txt = await resp.text();
    await sb.from("homework_replies").update({ ai_at: null }).eq("id", r.id);      // release the claim; the page may retry
    return json(H, { error: `OpenAI ${resp.status}: ${txt.slice(0, 200)}` }, 502);
  }
  const j = await resp.json(), usage = j.usage || {};
  let ai: Record<string, unknown>;
  try { ai = JSON.parse(j.choices[0].message.content); } catch { ai = { verdict: "ungraded", reason: "The checker answered in a shape I could not read.", fixed: "" }; }
  if (!["right", "close", "wrong"].includes(ai.verdict as string)) ai.verdict = "ungraded";
  ai.reason = String(ai.reason || "").slice(0, 300); ai.fixed = String(ai.fixed || "").slice(0, 500);
  ai.model = MODEL; ai.cost_usd = cost(usage); ai.examples = (overs || []).length;
  await sb.from("api_spend").insert({ service: "openai", usd: ai.cost_usd, note: `check-homework ${r.id} (${usage.total_tokens || 0} tokens)` });
  await sb.from("homework_replies").update({ ai, ai_at: new Date().toISOString() }).eq("id", r.id);
  return json(H, { ai });
});
