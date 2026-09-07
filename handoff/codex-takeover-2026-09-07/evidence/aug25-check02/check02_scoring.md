# Check 02 scoring rule (pre-registered 2026-09-03 23:58, before any rating)

- Engines: dialect (local), speechmatics (ar_en), eleven_auto, eleven_ara. The two ElevenLabs runs are ONE family.
- Row score: each picked letter's engine gets 1 (multi-pick allowed; picked engines tie with each other on that row). "All same" = every engine 0.5. "All wrong" = every engine 0.
- Silence rows: an engine showing "(nothing)" scores 1, an engine showing words scores 0, regardless of the pick.
- Verdict = pairwise: ElevenLabs family vs Speechmatics vs dialect, counting rows where the two differ.
  ElevenLabs is the default; it loses only if another engine beats it on >= 60% of the differing rows (min 20 rows rated).
- Partial ratings count (hard rows are first). Ties go to the cheaper engine with the best independent benchmark (ElevenLabs).
- Separate question NOT measured here: which engine keeps Medi's mistakes instead of auto-correcting them (LearnerVoice). That needs a no-LM CTC run later.
