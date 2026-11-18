#!/usr/bin/env python3
"""Small local round trip, plus optional verification of a host-uploaded workbook."""
import argparse
import json
from pathlib import Path
import tempfile

from openpyxl import load_workbook
from translation_workbook import complete, prepare

SOURCE = '<!doctype html><html lang="en-GB"><head><title>Runtime check</title></head><body><p>Hello &amp; welcome</p></body></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('runtime-check-output'))
    parser.add_argument('--uploaded', type=Path, help='Verify the returned runtime-probe.xlsx from the actual host attachment.')
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            original = folder / 'input.html'
            original.write_bytes(SOURCE.encode('utf-8'))
            job = folder / 'job'
            prepare(original, 'en-GB', ['de-DE'], job)
            workbook = load_workbook(job / 'translations.xlsx')
            workbook['Translations']['E7'] = 'Hallo & willkommen'
            probe = folder / 'runtime-probe.xlsx'
            workbook.save(probe)
            workbook.close()
            result = complete(job, args.uploaded or probe, folder / 'completed')
            if not result['ok']:
                print(json.dumps(result, indent=2))
                return 1
            output = (folder / 'completed/email-de-DE.html').read_bytes()
            expected = SOURCE.replace('lang="en-GB"', 'lang="de-DE"').replace('Hello &amp; welcome', 'Hallo &amp; willkommen').encode('utf-8')
            if output != expected:
                raise ValueError('Runtime round trip did not produce the exact expected HTML.')
            args.output_dir.mkdir(parents=True, exist_ok=False)
            (args.output_dir / 'runtime-probe.xlsx').write_bytes(probe.read_bytes())
            (args.output_dir / 'runtime-probe.html').write_bytes(output)
            print(json.dumps(dict(ok=True, uploaded_workbook_checked=bool(args.uploaded),
                                  output_directory=str(args.output_dir),
                                  host_downloads_verified=False), indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps(dict(ok=False, error=str(error))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
