"""Run safety tests and both Qt stress scenarios with timeouts and saved logs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk-count', type=int, default=0, help='Opt-in disk IO test; 0 disables it')
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--full-grid-count', type=int, default=1000)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    if min(args.count, args.full_grid_count, args.timeout) <= 0:
        parser.error('Counts and timeout must be positive')
    root = Path(__file__).resolve().parents[1]
    output = root / 'tests/artifacts' / ('suite_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True)
    common = ['--output', str(output), '--max-load-seconds', '120',
              '--max-render-seconds', '600', '--max-rss-mb', '2048']
    cases = [
        ('safety', ['-m', 'unittest', 'discover', '-s', 'tests', '-v']),
        ('virtual_grid', ['-m', 'tests.ate', '--count', str(args.count), '--mode', 'virtual-grid'] + common),
        ('small_batches', ['-m', 'tests.ate', '--count', str(args.full_grid_count), '--mode', 'batch'] + common),
    ]
    if args.disk_count < 0:
        parser.error('--disk-count must be nonnegative')
    if args.disk_count:
        cases.append(('disk_io', ['-m', 'tests.ate', '--storage', 'disk',
                                  '--count', str(args.disk_count)] + common))
    results = []
    for name, command in cases:
        print(f'Running {name}; log: {output / (name + ".log")}', flush=True)
        tick = time.perf_counter()
        with (output / (name + '.log')).open('w') as log:
            try:
                completed = subprocess.run([sys.executable] + command, cwd=root,
                                           stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = 124
                log.write('\nATE timeout exceeded\n')
        results.append(dict(case=name, exit_code=code, passed=code == 0,
                            seconds=time.perf_counter() - tick))
        (output / 'suite.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    print(f'Results: {output}')
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
