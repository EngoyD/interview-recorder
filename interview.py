#!/usr/bin/env python3
"""Record a call on your Mac and write a two-speaker transcript. Nothing leaves your computer.

  interview <name>      record in this window (press q to stop), then transcribe
  interview toggle      start recording in the background, or stop the running one (for a keyboard shortcut)
  interview <folder>    re-transcribe an existing recording folder
"""
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")  # Shortcuts runs with a bare PATH
ROOT = Path.home() / "interviews"
MODEL = ROOT / "models" / "ggml-large-v3-turbo.bin"
VAD = ROOT / "models" / "ggml-silero-v6.2.0.bin"
PIDFILE = ROOT / ".recording.pid"
# Each side is recorded from its own device into its own file. To pick the mic yourself, put its name in
# ~/interviews/mic.txt (list names: ffmpeg -f avfoundation -list_devices true -i "").
MIC_FILE = ROOT / "mic.txt"
CALL = "BlackHole 2ch"
SIDES = {  # speaker: (raw file, filter applied before transcription)
    "Me": ("mic.wav", "dynaudnorm"),
    "Interviewer": ("call.wav", "anull"),
}
HINT = {"Me": "that Terminal, Shortcuts and ffmpeg have microphone access",
        "Interviewer": "that your call app's speaker is set to your Multi-Output device"}


def notify(msg):
    subprocess.run(["osascript", "-e", "on run argv", "-e",
                    'display notification (item 1 of argv) with title "Interview"', "-e", "end run", msg])


def new_folder(name):
    out = ROOT / f"{datetime.now():%Y-%m-%d_%H%M%S}_{name}"
    out.mkdir(parents=True)
    return out


def pick_mic():
    if MIC_FILE.exists() and MIC_FILE.read_text().strip():
        return MIC_FILE.read_text().strip()
    # Prefer the Mac's own mic: opening a Bluetooth headset's mic drops the headphones into scratchy call-quality audio.
    listing = subprocess.run(["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                             capture_output=True, text=True).stderr
    builtin = re.search(r"\] \[\d+\] ((?:MacBook|iMac)[^\n]*Microphone)\s*$", listing, re.M)
    return builtin.group(1) if builtin else "default"


def record(out, background=False):
    mic = pick_mic()
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin" if background else "-stats"]
    for device in (mic, CALL):
        cmd += ["-thread_queue_size", "1024", "-f", "avfoundation", "-i", f":{device}"]
    for i, (raw, _) in enumerate(SIDES.values()):
        cmd += ["-map", f"{i}:a", "-ac", "1", str(out / raw)]
    print(f"Mic: {mic}")
    proc = subprocess.Popen(cmd)
    if background:
        PIDFILE.write_text(str(proc.pid))
    else:
        print(f"Recording to {out}\nPress q to stop.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.wait()  # ffmpeg got the same Ctrl+C and is finalizing the files
    finally:
        if background:
            PIDFILE.unlink(missing_ok=True)
    for raw, _ in SIDES.values():
        f = out / raw
        if not f.exists() or f.stat().st_size < 100_000:
            sys.exit(f"Recording failed or too short: {f}")
    if proc.returncode not in (0, 255):  # 0 = stopped with q, 255 = stopped with Ctrl+C or the shortcut
        msg = "Recording stopped on its own. Transcribing what was captured."
        print("WARNING: " + msg)
        if background:
            notify(msg)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def transcribe(out):
    segments, warnings = [], []
    lengths = {who: duration(out / raw) for who, (raw, _) in SIDES.items()}
    for who, (raw, af) in SIDES.items():
        shift = round((max(lengths.values()) - lengths[who]) * 1000)  # both stop together; the shorter one started late
        if shift > 3000:  # too big for a late start: this side dropped out mid-call, so its start time is right as is
            print(f"WARNING: the {who} track is {shift / 1000:.0f}s shorter than the other; it may have cut out.")
            shift = 0
        wav = out / f"{who}.16k.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-i", str(out / raw), "-af", af, "-ar", "16000", "-ac", "1", str(wav)], check=True)
        subprocess.run(["whisper-cli", "-m", str(MODEL), "--vad", "-vm", str(VAD), "-l", "en",
                        "-np", "-oj", "-of", str(out / who), "-f", str(wav)], check=True)
        data = json.loads((out / f"{who}.json").read_bytes().decode("utf-8", "replace"), strict=False)
        found = [(s["offsets"]["from"] + shift, who, s["text"].strip())
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
    segments, warnings = transcribe(out)
    write_transcript(segments, out / "transcript.md")
    print(f"Done: {out / 'transcript.md'}")
    return warnings


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
            os.kill(pid, signal.SIGINT)  # ffmpeg finalizes the files; the background process then transcribes
            notify("Stopped. Transcribing...")
            return
        out = new_folder("call")
        with open(out / "log.txt", "w") as log:
            subprocess.Popen([sys.executable, __file__, "--bg", str(out)], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        for _ in range(100):  # hold the lock until ffmpeg is up and the pid file is written
            if running_pid():
                break
            time.sleep(0.1)


def background(out):
    try:
        notify("Recording. Press the shortcut again to stop.")
        record(out, background=True)
        warnings = finish(out)
        notify(f"Transcript ready, but: {warnings[0]}" if warnings else f"Transcript ready: {out.name}")
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
    raw = SIDES["Me"][0]
    out = next((p for p in (Path(arg).expanduser(), ROOT / arg) if (p / raw).exists()), None)
    if out is None:
        out = new_folder(arg)
        record(out)
    finish(out)


if __name__ == "__main__":
    main()
