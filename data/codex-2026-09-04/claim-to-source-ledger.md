# Anees claim-to-source ledger

Prepared 2026-09-04. “Local” means directly measured from the frozen 2026-09-04 inputs and stored artifacts. “Verified” means the linked primary/official source explicitly supports the claim. “Inference” means the conclusion combines sources or measurements and is labeled as such in the report.

| Claim | Status | Evidence/source | Qualification |
|---|---|---|---|
| Recording is 3,876.083333 s and contains one AAC stereo stream | Local, verified | `manifest.json`; `ffprobe` output used by `run_test.py` | Stereo is treated as mixed; channel independence was not proven |
| All O1/O2 and exploratory ElevenLabs calls returned 200/nonempty | Local, verified | five result JSON files | Provider success is not transcript correctness |
| ES has 725 tokens, 22 fillers, 25 cutoff markers; O1/O2 have 590/593 and zero fillers | Local, reproducible | `comparison.json`; `analyze_results.py` | Mechanical proxy counts, not WER |
| O1/O2 recover 14/13 families; ElevenLabs arms recover 16 | Local, manually audited | `comparison.json` manual surface labels | Chat-family visibility, not audio truth |
| Short segmentation accounts for diarization cluster recovery | Local inference | E-long vs ES/EKG/EKL in `comparison.json`; Meet named captions | No-keyterm ES is the control; cluster count does not establish identity |
| Global keyterms inserted `Mabsoo6` for “Awesome” | Local, verified by output comparison | clip 1 in ES/EKG/EKL result JSONs and audio | Human listening is still invited in Claude review |
| Existing 15/20 blind vote excluded OpenAI | Local code/data verified | `C:\dev\anees\scripts\build_engine_report.py`; `data\aug25\check02_scoring.md` | It compared ElevenLabs, Speechmatics, local dialect system |
| Current pipeline can miscount tutor Arabic as Medi Arabic when split fails | Local code inference | `lesson_pipeline.py` lines 91–128 | Code path should be covered by a regression test |
| `gpt-transcribe` costs $0.0045/min and supports context/keyword/multiple-language hints | Verified | https://developers.openai.com/api/docs/models/gpt-transcribe | Prices/features can change |
| OpenAI diarization supports known names and 2–10 s references, up to 4 speakers | Verified | https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create | Must be benchmarked before use |
| ElevenLabs Scribe v2 is $0.22/h; keyterms $0.05/h/20%; realtime $0.39/h | Verified | https://elevenlabs.io/pricing/api and request docs | Billing/rounding can differ from arithmetic estimates |
| ElevenLabs supports `no_verbatim`, keyterms, and multichannel up to 5 channels | Verified | https://elevenlabs.io/docs/api-reference/speech-to-text/convert and https://elevenlabs.io/docs/overview/capabilities/speech-to-text | Raw learner layer should not use keyterms |
| Zencastr Free advertises unlimited separate recording/download | Verified on current pricing page | https://zencastr.com/pricing | Plan terms can change |
| Amal need not manually upload; local recording progressively uploads | Verified | https://support.zencastr.com/en/articles/5452702-how-zencastr-records | Both keep page open until completion |
| Zencastr WAV entitlement is inconsistent across official pages | Mixed official evidence | Pricing page says 48 kHz WAV; https://support.zencastr.com/en/articles/9745874-getting-started-with-recording says WAV paid | Rely on separate MP3 until account UI confirms |
| Zencastr native transcripts are not a Palestinian-Arabic solution | Verified from help article | https://support.zencastr.com/en/articles/9746991-getting-transcripts-for-zencastr-recordings | Current pricing says 10 languages but does not name them; older help names five, none Arabic |
| Meet can save captions/chat but does not solve separate-track capture here | Verified plus local | https://support.google.com/meet/answer/9308681?hl=en; recording manifest | Actual file had one audio stream |
| Maknuune has >36K Palestinian entries, 17K lemmas, 3.7K roots, phonological transcription | Verified academic primary source | https://aclanthology.org/2022.wanlp-1.13/ | Use as seed; Amal’s local variety remains authoritative for this project |
| Forced alignment needs transcript and pronunciation dictionary | Verified documentation | https://montreal-forced-aligner.readthedocs.io/en/v3.4.1/user_guide/index.html | Appropriate when target is known |
| GOP is phone-posterior based; classifier features can outperform raw threshold | Verified code/reference | https://github.com/kaldi-asr/kaldi/blob/master/src/bin/compute-gop.cc | Requires Palestinian/Medi calibration |
| Available Arabic MDD examples are domain-mismatched | Verified | https://arxiv.org/abs/2111.01136 and https://aclanthology.org/2025.arabicnlp-sharedtasks.61/ | Egyptian children and Qur’anic/MSA reading are not adult Palestinian conversation |
| Azure and Google list `ar-PS` ASR/adaptation | Verified | Microsoft language support and Google STT supported languages pages | Worth future benchmark; not evidence of learner-error accuracy |
| Nearly perfect transcript has not been demonstrated | Verified limitation | no human verbatim gold in project/test | Requires labeled WER/CER plus learner-form and speaker metrics |

