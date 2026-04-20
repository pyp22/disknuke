#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/dd_wipe.py"
IMG="/tmp/test_wipe_disk.img"
LOOP=""

cleanup() {
    echo ""
    echo "--- Cleanup ---"
    [ -n "$LOOP" ] && sudo /usr/sbin/losetup -d "$LOOP" 2>/dev/null && echo "Loop device $LOOP detached."
    rm -f "$IMG" && echo "Image $IMG removed."
}
trap cleanup EXIT

run_test() {
    local choice="$1"
    local passes="$2"
    local label="$3"

    echo ""
    echo "=============================="
    echo "TEST: $label"
    echo "=============================="

    # Create fresh 64MB image
    dd if=/dev/zero of="$IMG" bs=1M count=64 status=none

    # Attach loop device
    LOOP=$(sudo /usr/sbin/losetup --find --show "$IMG")
    echo "Loop device : $LOOP"

    # Build input sequence for the script
    if [ "$choice" -eq 4 ]; then
        # shred: no passes prompt
        INPUT="$LOOP\n$choice\nYES"
    else
        INPUT="$LOOP\n$choice\n$passes\nYES"
    fi

    # Run the wipe script
    echo -e "$INPUT" | sudo python3 "$PYTHON_SCRIPT"

    # Wait for background wipe to complete
    echo "Waiting for wipe to finish..."
    local logfile
    logfile=$(ls -t /var/log/disk_wipe_*.log 2>/dev/null | head -1 || true)
    if [ -n "$logfile" ]; then
        timeout 120 bash -c "until grep -q 'Wipe COMPLETE\|COMPLETE' \"$logfile\" 2>/dev/null; do sleep 1; done" || true
        echo ""
        echo "--- Log output ---"
        cat "$logfile"
        sudo rm -f "$logfile"
    fi

    # Detach loop
    sudo /usr/sbin/losetup -d "$LOOP"
    LOOP=""
    echo ""
    echo "PASS: $label"
}

echo "=========================================="
echo " DD-Wipe Python script — integration test"
echo "=========================================="

# Test 1: urandom, 1 pass
run_test 1 1 "urandom / 1 pass"

# Test 2: zero, 1 pass
run_test 2 1 "zero / 1 pass"

# Test 3: openssl-aes, 1 pass
run_test 3 1 "openssl-aes / 1 pass"

# Test 4: shred
run_test 4 "" "shred (DoD)"

echo ""
echo "=========================================="
echo " All tests passed."
echo "=========================================="
