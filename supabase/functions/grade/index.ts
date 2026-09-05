// M10c - `grade`: pre-grades one typed homework answer the moment Medi submits it, in Amal's own correction style.
// POST {answer_id}  ->  {grade}   (the grade is also written to homework_answers.grade with the service key)
// Guards: the answer must exist and be ungraded; today's OpenAI spend (api_spend) must be under DAILY_CAP_USD; the model
// only sees the prompt, Medi's answer, the target words (Doc spelling + Arabic + English) and 12 real (answer, Amal's fix)
// pairs from the chat. Amal's verdict, given later on her link, always overrides this grade.
import { createClient } from "npm:@supabase/supabase-js@2";
import { PAIRS } from "./pairs.ts";

const MODEL = "gpt-5.5";
const DAILY_CAP_USD = 0.5;
const ORIGINS = ["https://thenatanzi.github.io", "http://localhost", "http://127.0.0.1"];

function cors(origin: string | null) {
  const ok = origin && ORIGINS.some((o) => origin.startsWith(o));
  return {
    "Access-Control-Allow-Origin": ok ? origin! : ORIGINS[0],
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };
}

const cost = (u: { prompt_tokens?: number; completion_tokens?: number }) =>
  Math.round(((u.prompt_tokens || 0) * 5 / 1e6 + (u.completion_tokens || 0) * 20 / 1e6) * 1e4) / 1e4; // ceiling prices, never lower

Deno.serve(async (req) => {
  const H = cors(req.headers.get("origin"));
  if (req.method === "OPTIONS") return new Response("ok", { headers: H });
  if (req.method !== "POST") return new Response(JSON.stringify({ error: "POST only" }), { status: 405, headers: H });
  let body: { answer_id?: string } = {};
  try { body = await req.json(); } catch { /* empty */ }
  if (!body.answer_id) return new Response(JSON.stringify({ error: "answer_id missing" }), { status: 400, headers: H });

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: a } = await sb.from("homework_answers").select("*").eq("id", body.answer_id).maybeSingle();
  if (!a) return new Response(JSON.stringify({ error: "no such answer" }), { status: 404, headers: H });
  if (a.grade) return new Response(JSON.stringify({ grade: a.grade, cached: true }), { headers: H });
  const { data: it } = await sb.from("homework_items").select("*").eq("id", a.item_id).maybeSingle();
  if (!it) return new Response(JSON.stringify({ error: "no such item" }), { status: 404, headers: H });

  const since = new Date(); since.setUTCHours(0, 0, 0, 0);
  const { data: spent } = await sb.from("api_spend").select("usd").gte("ts", since.toISOString());
  const today = (spent || []).reduce((s: number, r: { usd: number }) => s + (r.usd || 0), 0);
  if (today >= DAILY_CAP_USD) {
    const grade = { verdict: "ungraded", notes: [{ kind: "budget", say: "Today's grading budget is used up. Amal will still see your answer." }], fixed: "", keys_wrong: [], model: null, cost_usd: 0 };
    await sb.from("homework_answers").update({ grade, graded_at: new Date().toISOString() }).eq("id", a.id);
    return new Response(JSON.stringify({ grade }), { headers: H });
  }

  const { data: words } = await sb.from("words").select("key,arabizi,arabic,english,house_spelling").in("key", it.keys || []);
  const targets = (words || []).map((w) => `${w.key} -> ${w.house_spelling || w.arabizi} | ${w.arabic} | ${w.english}`).join("\n");
  const examples = PAIRS.map((p: { english: string; answer: string; amal: string; note: string }) =>
    `Prompt: ${p.english}\nMedi: ${p.answer}\nAmal: ${p.amal}${p.note ? `  (${p.note})` : ""}`).join("\n\n");
  const prompt = `You are Amal, a Palestinian Arabic tutor, checking ONE typed homework answer from your adult student Medi. He translates your
English prompt into spoken Palestinian Arabic written in Arabizi (6=ط 7=ح 3=ع 2=ء/ق 5=خ 9=ص 8=غ). You correct the way you do in WhatsApp:
terse, only the tokens that need fixing, never a lecture. Spelling variants of the same sound are NOT errors (kteer/ktir, ma3/ma3a, e/i, o/u).

Your real corrections (learn the bar you set):
${examples}

Target words this prompt practises (key -> your spelling | Arabic | English):
${targets}

Prompt: ${it.status === "edit" && it.edited_english ? it.edited_english : it.english}
Model answer (yours, for reference only): ${it.model_arabizi}
Medi: ${a.answer}

Return ONLY JSON: {"verdict": "right" | "close" | "wrong", "notes": [{"kind": "word|choice|prefix|suffix|gender|plural|tense|command|negation|order|preposition|spelling", "say": "<= 12 words, Amal's voice"}], "fixed": "<the corrected sentence in Arabizi, or the same sentence when right>", "keys_wrong": ["<target keys he got wrong>"]}
"right" = you would reply Yes / Tmm. "close" = one small fix. "wrong" = the meaning or the main verb is off. Max 3 notes.`;

  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${Deno.env.get("OPENAI_API_KEY")}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, messages: [{ role: "user", content: prompt }], response_format: { type: "json_object" } }),
  });
  if (!r.ok) {
    const t = await r.text();
    return new Response(JSON.stringify({ error: `OpenAI ${r.status}: ${t.slice(0, 200)}` }), { status: 502, headers: H });
  }
  const j = await r.json();
  const usage = j.usage || {};
  let grade: Record<string, unknown>;
  try {
    grade = JSON.parse(j.choices[0].message.content);
  } catch {
    grade = { verdict: "ungraded", notes: [{ kind: "parse", say: "The grader answered in a shape I could not read." }], fixed: "", keys_wrong: [] };
  }
  const allowed = new Set(it.keys || []);
  grade.keys_wrong = Array.isArray(grade.keys_wrong) ? (grade.keys_wrong as string[]).filter((k) => allowed.has(k)) : [];
  grade.notes = Array.isArray(grade.notes) ? (grade.notes as unknown[]).slice(0, 3) : [];
  if (!["right", "close", "wrong"].includes(grade.verdict as string)) grade.verdict = "ungraded";
  grade.model = MODEL; grade.cost_usd = cost(usage);
  await sb.from("api_spend").insert({ service: "openai", usd: grade.cost_usd, note: `grade ${a.id} (${usage.total_tokens || 0} tokens)` });
  await sb.from("homework_answers").update({ grade, graded_at: new Date().toISOString() }).eq("id", a.id);
  return new Response(JSON.stringify({ grade }), { headers: H });
});
