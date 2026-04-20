# disknuke

Multi-pass disk wipe utility for Linux. Overwrites block devices using your choice of wipe source, logs everything, and runs fully in the background.

## Features

- Multiple wipe sources: `/dev/urandom`, `/dev/zero`, OpenSSL AES-256-CTR, GNU `shred` (DoD 5220.22-M)
- Configurable number of passes
- Runs in background — terminal can be closed safely
- Full logging to `/var/log/disk_wipe_<PID>.log`
- Auto-sudo launcher with dependency check

## Requirements

- Python 3.6+
- `dd`, `blockdev`, `sync` (coreutils / util-linux)
- `openssl` (optional, for AES source)
- `shred` (optional, GNU coreutils)

## Usage

```bash
sudo ./run_wipe.sh
```

Or directly:

```bash
sudo python3 dd_wipe.py
```

```
Enter DISK to fully erase (e.g. /dev/sdd): /dev/sdd

Select wipe source:
  [1] urandom       — kernel CSPRNG, good security, moderate speed (default)
  [2] zero          — /dev/zero, fastest, no randomness (final pass only recommended)
  [3] openssl-aes   — AES-256-CTR stream, fastest on AES-NI CPUs, cryptographic quality
  [4] shred         — GNU shred built-in (DoD 5220.22-M: urandom/complement/urandom + zero)

Choice [default: 1]: 1
Enter number of passes [default: 3]: 3

Device   : /dev/sdd
Size     : 931.5G
Source   : urandom
Passes   : 3
Log file : /var/log/disk_wipe_1234.log

ARE YOU SURE? Type YES to confirm: YES

✓ Wipe launched in background (PID: 1236)
```

## Monitor progress

```bash
tail -f /var/log/disk_wipe_<PID>.log
```

```bash
# Trigger dd progress output
kill -USR1 $(pgrep -f 'dd if=/dev')
```

## Notes

- **SSD/NVMe**: wear-leveling makes software wipe unreliable. Use `hdparm --security-erase` or `nvme format --ses=1` instead.
- `ENOSPC` errors in the log are normal — they confirm the device was fully overwritten.

## License

MIT
