---
name: interview-debrief
description: Debrief a job interview recorded with the interview recorder. Grades each answer, flags what was missing, rewrites weak answers, and saves debrief.md. Use on 'debrief', 'how did my interview go', or a transcript.md.
---

# Interview debrief

Turns a transcript from the `interview` recorder into coaching the user can act on before their next call.

## Find the transcript
- If a transcript.md is attached, use it.
- Otherwise, if you can reach ~/interviews on the user's Mac, pick the folder they name ("acme" matches `*_acme`), or the newest folder if they don't name one. If you can't reach it, ask them to attach transcript.md from that folder.
- Lines look like `**[MM:SS] Me:** ...` and `**[MM:SS] Interviewer:** ...`. Whisper drops most "um" and "uh", so don't score filler words.
- If one side is missing or nearly empty, say so first. The recording setup failed and a debrief would be one-sided.
- If the user shares the job description or their resume, use them. Don't hold the debrief waiting for either.

## Debrief
Terse. Lead with the verdict.

1. **Overall**: two sentences on how it went and the single biggest fix.
2. **Numbers**: the user's share of total words, their longest answer (duration and rough word count), and how many questions they asked the interviewer.
3. **Each question the interviewer asked**, in order:
   - The question, shortened.
   - Verdict: strong / fine / weak.
   - What was missing: a concrete example, a number, the outcome, their own role, or a direct answer to what was actually asked.
   - For fine or weak answers, a tighter version they could say next time: 3 to 5 spoken sentences in their voice, built only from facts in the transcript, their resume, or what they've told you. Never invent metrics.
4. **Missed openings**: moments where they could have brought up a strength that fits the role and didn't. Use the job description and resume if you have them, otherwise strengths they mentioned elsewhere in the call.
5. **Their questions**: which ones landed, plus one or two better ones for the next round with this company.
6. **Next time**: the habits to change, phrased as things to do.

## Save
If you can write to the transcript's folder, save the debrief there as debrief.md. Otherwise give it to the user as a debrief.md file.

If earlier debriefs exist (debrief.md in other ~/interviews folders, or ones the user attaches), read their "Next time" sections and add one line on whether each habit improved, held, or slipped.
