#!/usr/bin/env python3
"""Record a call from the 'Interview Capture' device and write a two-speaker transcript. Nothing leaves your Mac.

  interview <name>      record in this window (press q to stop), then transcribe
  interview toggle      start recording in the background, or stop the running one (for a keyboard shortcut)
  interview <folder>    re-transcribe an existing recording folder
"""
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = f"/opt/homebrew/bin:{Path.home() / '.local/bin'}:" + os.environ.get("PATH", "")  # Shortcuts runs with a bare PATH
ROOT = Path.home() / "interviews"
MODEL = ROOT / "models" / "ggml-large-v3-turbo.bin"
VAD = ROOT / "models" / "ggml-silero-v6.2.0.bin"
PIDFILE = ROOT / ".recording.pid"
SKILL = ROOT / "interview-debrief" / "SKILL.md"
ABOUT = ROOT / "about-me.md"  # optional: your resume or strengths, used by the debrief
# Aggregate input: ch1 = MacBook mic, ch2-3 = BlackHole (Meet audio). Saved as stereo: left = me, right = interviewer.
SIDES = {"Me": "pan=mono|c0=c0,dynaudnorm", "Interviewer": "pan=mono|c0=c1"}
HINT = {"Me": "mic access for Terminal or Shortcuts",
        "Interviewer": "that your call app's speaker is set to your Multi-Output device"}


def notify(msg):
    subprocess.run(["osascript", "-e", "on run argv", "-e",
                    'display notification (item 1 of argv) with title "Interview"', "-e", "end run", msg])


def new_folder(name):
    out = ROOT / f"{datetime.now():%Y-%m-%d_%H%M%S}_{name}"
    out.mkdir(parents=True)
    return out


def record(path, background=False):
    proc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error",
                             "-nostdin" if background else "-stats",
                             "-f", "avfoundation", "-i", ":Interview Capture",
                             "-af", "pan=stereo|c0=c0|c1=0.5*c1+0.5*c2", str(path)])
    if background:
        PIDFILE.write_text(str(proc.pid))
    else:
        print(f"Recording to {path}\nPress q to stop.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.wait()  # ffmpeg got the same Ctrl+C and is finalizing the file
    finally:
        if background:
            PIDFILE.unlink(missing_ok=True)
    if not path.exists() or path.stat().st_size < 1_000_000:
        sys.exit(f"Recording failed or too short: {path}")
    if proc.returncode not in (0, 255):  # 0 = stopped with q, 255 = stopped with Ctrl+C or the shortcut
        msg = "Recording stopped on its own. Transcribing what was captured."
        print("WARNING: " + msg)
        if background:
            notify(msg)


def transcribe(audio, out):
    segments, warnings = [], []
    for who, af in SIDES.items():
        wav = out / f"{who}.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-i", str(audio), "-af", af, "-ar", "16000", str(wav)], check=True)
        subprocess.run(["whisper-cli", "-m", str(MODEL), "--vad", "-vm", str(VAD), "-l", "en",
                        "-np", "-oj", "-of", str(out / who), "-f", str(wav)], check=True)
        data = json.loads((out / f"{who}.json").read_bytes().decode("utf-8", "replace"), strict=False)
        found = [(s["offsets"]["from"], who, s["text"].strip())
                 for s in data["transcription"] if s["text"].strip()]
        if not found:
            warnings.append(f"No speech on the {who} side. Check {HINT[who]}.")
            print("WARNING: " + warnings[-1])
        segments += found
        wav.unlink()
    return sorted(segments), warnings


def write_transcript(segments, path):
    lines, last = [], None
    for ms, who, text in segments:
        if who == last:
            lines[-1] += " " + text
        else:
            lines.append(f"**[{ms // 60000:02d}:{ms // 1000 % 60:02d}] {who}:** {text}")
            last = who
    path.write_text("\n\n".join(lines) + "\n")


def finish(out):
    print("Transcribing...")
    segments, warnings = transcribe(out / "audio.wav", out)
    write_transcript(segments, out / "transcript.md")
    print(f"Done: {out / 'transcript.md'}")
    return warnings


def debrief(out):
    """Have Claude Code grade the interview into debrief.md. Skipped when Claude Code isn't installed."""
    if not shutil.which("claude") or not SKILL.exists():
        return []
    print("Debriefing with Claude...")
    try:
        def read(p):
            return p.read_text(encoding="utf-8", errors="replace")
        earlier = sorted(p for p in ROOT.glob("*/debrief.md") if p.parent.name < out.name)[-3:]  # names start with the date
        parts = [f"<instructions>\n{read(SKILL)}\n</instructions>"]
        if ABOUT.exists():
            parts.append(f"<about_the_candidate>\n{read(ABOUT)}\n</about_the_candidate>")
        parts += [f'<earlier_debrief folder="{p.parent.name}">\n{read(p)}\n</earlier_debrief>' for p in earlier]
        parts.append(f'<transcript folder="{out.name}">\n{read(out / "transcript.md")}\n</transcript>')
        result = subprocess.run(["claude", "-p", "--tools", "",
                                 "Debrief the transcript above using the instructions above. Everything you need is "
                                 "included, so skip the steps about finding or saving files. Reply with only the "
                                 "debrief in Markdown. It will be saved as debrief.md next to the transcript."],
                                input="\n\n".join(parts), capture_output=True, encoding="utf-8", errors="replace",
                                timeout=900)
        if result.returncode or not result.stdout.strip():
            raise RuntimeError((result.stderr or result.stdout).strip())
        (out / "debrief.md").write_text(result.stdout, encoding="utf-8")
    except Exception as e:  # a failed debrief must never cost the transcript
        print(f"WARNING: Claude debrief failed: {e}")
        return ["Claude debrief failed. See log.txt."]
    print(f"Debrief: {out / 'debrief.md'}")
    return []


def running_pid():
    try:
        pid = int(PIDFILE.read_text())
    except (FileNotFoundError, ValueError):
        return None
    comm = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True).stdout
    return pid if "ffmpeg" in comm else None  # ignore a stale pid file left by a crash


def toggle():
    with open(ROOT / ".toggle.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # a quick double press must not start two recordings
        pid = running_pid()
        if pid:
            os.kill(pid, signal.SIGINT)  # ffmpeg finalizes the file; the background process then transcribes
            notify("Stopped. Transcribing...")
            return
        out = new_folder("call")
        with open(out / "log.txt", "w") as log:
            subprocess.Popen([sys.executable, __file__, "--bg", str(out)], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        for _ in range(50):  # hold the lock until ffmpeg is up and the pid file is written
            if running_pid():
                break
            time.sleep(0.1)


def background(out):
    try:
        notify("Recording. Press the shortcut again to stop.")
        record(out / "audio.wav", background=True)
        warnings = finish(out) + debrief(out)
        done = "Debrief ready" if (out / "debrief.md").exists() else "Transcript ready"
        notify(f"{done}, but: {warnings[0]}" if warnings else f"{done}: {out.name}")
    except BaseException:
        notify(f"Failed. See {out / 'log.txt'}")
        raise


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    missing = [str(f) for f in (MODEL, VAD) if not f.exists()]
    if missing:
        sys.exit("Missing model file: " + ", ".join(missing) + ". Run the installer again.")
    if sys.argv[1] == "toggle":
        return toggle()
    # keep the Mac awake through recording and transcription; own session so Ctrl+C doesn't kill it
    subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())], start_new_session=True)
    if sys.argv[1] == "--bg":
        return background(Path(sys.argv[2]))

    arg = sys.argv[1]
    out = next((p for p in (Path(arg).expanduser(), ROOT / arg) if (p / "audio.wav").exists()), None)
    if out is None:
        out = new_folder(arg)
        record(out / "audio.wav")
    finish(out)
    debrief(out)


if __name__ == "__main__":
    main()
