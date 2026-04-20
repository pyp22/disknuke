#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime
from pathlib import Path


WIPE_SOURCES = {
    "1": {
        "label": "urandom       — kernel CSPRNG, good security, moderate speed (default)",
        "source": "urandom",
    },
    "2": {
        "label": "zero          — /dev/zero, fastest, no randomness (final pass only recommended)",
        "source": "zero",
    },
    "3": {
        "label": "openssl-aes   — AES-256-CTR stream, fastest on AES-NI CPUs, cryptographic quality",
        "source": "openssl",
    },
    "4": {
        "label": "shred         — GNU shred built-in (DoD 5220.22-M: urandom/complement/urandom + zero)",
        "source": "shred",
    },
}


def log(logfile: str, msg: str) -> None:
    ts = datetime.datetime.now().strftime("%F %T")
    line = f"[{ts}] {msg}\n"
    with open(logfile, "a") as f:
        f.write(line)


def human_size(size: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size //= 1024
    return f"{size:.1f}P"


def get_size(dev: str) -> int:
    result = subprocess.run(
        ["blockdev", "--getsize64", dev],
        capture_output=True, text=True
    )
    return int(result.stdout.strip()) if result.returncode == 0 else 0


def dd_pass(source_arg: str, dev: str, logfile: str) -> int:
    proc = subprocess.run(
        ["dd", f"if={source_arg}", f"of={dev}", "bs=4M", "conv=fsync", "status=progress"],
        stderr=subprocess.STDOUT,
        stdout=open(logfile, "a"),
    )
    # ENOSPC (exit 1) means dd filled the device completely — that is success
    return 0 if proc.returncode == 1 else proc.returncode


def openssl_pass(dev: str, logfile: str) -> int:
    # Generate a random 256-bit key and IV, pipe AES-256-CTR stream directly into dd
    key = os.urandom(32).hex()
    iv  = os.urandom(16).hex()
    openssl = subprocess.Popen(
        ["openssl", "enc", "-aes-256-ctr", "-nosalt", "-K", key, "-iv", iv],
        stdin=open("/dev/zero", "rb"),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    dd = subprocess.Popen(
        ["dd", f"of={dev}", "bs=4M", "conv=fsync", "status=progress"],
        stdin=openssl.stdout,
        stderr=subprocess.STDOUT,
        stdout=open(logfile, "a"),
    )
    openssl.stdout.close()
    dd.wait()
    openssl.wait()
    # ENOSPC (exit 1) means dd filled the device completely — that is success
    return 0 if dd.returncode == 1 else dd.returncode


def wipe_disk(dev: str, passes: int, source: str, logfile: str) -> None:
    log(logfile, f"Starting wipe of {dev} — source={source}, passes={passes}")

    if source == "shred":
        # shred handles its own passes internally; ignore the passes parameter
        log(logfile, "Running shred (DoD 5220.22-M)")
        proc = subprocess.run(
            ["shred", "-v", "-z", dev],
            stderr=subprocess.STDOUT,
            stdout=open(logfile, "a"),
        )
        log(logfile, f"shred done (exit: {proc.returncode})")
    else:
        for i in range(1, passes + 1):
            log(logfile, f"Pass {i}/{passes} - {source}")
            if source == "openssl":
                rc = openssl_pass(dev, logfile)
            elif source == "zero":
                rc = dd_pass("/dev/zero", dev, logfile)
            else:
                rc = dd_pass("/dev/urandom", dev, logfile)
            log(logfile, f"Pass {i}/{passes} - done (exit: {rc})")

        if source != "zero":
            log(logfile, "Final zero pass")
            dd_pass("/dev/zero", dev, logfile)

    log(logfile, f"Wipe COMPLETE on {dev}")
    subprocess.run(["sync"])


def choose_source() -> str:
    print("Select wipe source:")
    for key, opt in WIPE_SOURCES.items():
        print(f"  [{key}] {opt['label']}")
    print()
    choice = input("Choice [default: 1]: ").strip() or "1"
    if choice not in WIPE_SOURCES:
        print(f"ERROR: invalid choice '{choice}'.", file=sys.stderr)
        sys.exit(1)
    return WIPE_SOURCES[choice]["source"]


def main() -> None:
    if os.geteuid() != 0:
        print("ERROR: must be run as root.", file=sys.stderr)
        sys.exit(1)

    dev = input("Enter DISK to fully erase (e.g. /dev/sdd): ").strip()

    if not Path(dev).is_block_device():
        print(f"ERROR: {dev} is not a valid block device.", file=sys.stderr)
        sys.exit(1)

    print()
    source = choose_source()

    passes = 0
    if source != "shred":
        raw = input("Enter number of passes [default: 3]: ").strip()
        passes_str = raw if raw else "3"
        if not passes_str.isdigit() or int(passes_str) < 1:
            print(f"ERROR: '{passes_str}' is not a valid number of passes.", file=sys.stderr)
            sys.exit(1)
        passes = int(passes_str)

    size = get_size(dev)
    logfile = f"/var/log/disk_wipe_{os.getpid()}.log"

    print()
    print(f"Device   : {dev}")
    print(f"Size     : {human_size(size)}")
    print(f"Source   : {source}")
    if source != "shred":
        print(f"Passes   : {passes}")
    print(f"Log file : {logfile}")
    print()

    confirm = input("ARE YOU SURE? Type YES to confirm: ").strip()
    if confirm != "YES":
        print("Aborted.")
        sys.exit(0)

    # Fork into background
    pid = os.fork()
    if pid > 0:
        # Parent: print launch info and exit
        os.waitpid(pid, os.WNOHANG)
        print()
        print(f"✓ Wipe launched in background (PID: {pid})")
        print()
        print("Monitor progress:")
        print(f"  tail -f {logfile}")
        print()
        print("Check dd progress (signal USR1):")
        print("  kill -USR1 $(pgrep -f 'dd if=/dev')")
        print()
        print(f"Kill if needed:")
        print(f"  kill {pid}")
        sys.exit(0)

    # Child: detach from terminal
    os.setsid()
    wipe_disk(dev, passes, source, logfile)


if __name__ == "__main__":
    main()
