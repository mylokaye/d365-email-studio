#!/usr/bin/env python3
"""Prepare an Excel translation job, validate a returned workbook, and export HTML."""
import argparse
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile
from xml.etree.ElementTree import ParseError
from openpyxl.utils.exceptions import InvalidFileException, IllegalCharacterError

from html_blocks import EmailDocument, fingerprint, json_text, language_selection
from workbook_io import build_workbook, metadata, read_workbook


@contextmanager
def new_directory(destination):
    """Publish a complete result directory or nothing. Never overwrite an earlier job."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError(f'Output already exists: {destination}. Choose a new directory.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.email-studio-', dir=destination.parent))
    try:
        yield temporary
        if destination.exists():
            raise ValueError(f'Output already exists: {destination}. Choose a new directory.')
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def prepare(original, source_language, targets, output, update_lang=True):
    source_language, targets = language_selection(source_language, targets)
    raw = Path(original).read_bytes()
    document = EmailDocument(raw.decode('utf-8'))
    config = metadata(document, source_language, targets, update_lang)
    workbook = build_workbook(document, config)
    with new_directory(output) as folder:
        (folder / 'original.html').write_bytes(raw)
        (folder / 'job.json').write_text(json_text(config) + '\n', encoding='utf-8')
        (folder / 'translations.xlsx').write_bytes(workbook)
    counts = {}
    for block in document.blocks:
        counts[block.kind] = counts.get(block.kind, 0) + 1
    return dict(ok=True, blocks=len(document.blocks), block_types=counts,
                languages=len(targets), source_language=source_language, targets=targets,
                translations_required=len(document.blocks) * len(targets), notices=document.notices,
                workbook=str(Path(output) / 'translations.xlsx'), original=str(Path(output) / 'original.html'),
                job=str(Path(output) / 'job.json'))


def load_job(folder):
    folder = Path(folder)
    raw = (folder / 'original.html').read_bytes()
    document = EmailDocument(raw.decode('utf-8'))
    config = json.loads((folder / 'job.json').read_text(encoding='utf-8'))
    if not isinstance(config, dict) or not isinstance(config.get('target_languages'), list):
        raise ValueError('Invalid saved job. Restore the original job or prepare a fresh workbook.')
    source, targets = language_selection(config.get('source_language'), config['target_languages'])
    if type(config.get('update_html_lang')) is not bool or json_text(config) != json_text(metadata(document, source, targets, config['update_html_lang'])):
        raise ValueError('Saved job does not match the original HTML or supported format.')
    return document, config


def complete(job, workbook, output=None):
    if Path(workbook).suffix.lower() != '.xlsx':
        raise ValueError('Upload the completed .xlsx workbook.')
    document, config = load_job(job)
    translations, errors = read_workbook(Path(workbook).read_bytes(), document, config)
    if errors:
        return dict(ok=False, errors=errors)
    files = {f'email-{target}.html': document.render(values, target, config['update_html_lang']).encode('utf-8')
             for target, values in translations.items()}
    if any(len(data) > 10 * 1024 * 1024 for data in files.values()):
        raise ValueError('A translated HTML file exceeds the 10 MB host download limit. Reduce the input email size.')
    report = dict(ok=True, blocks=len(document.blocks), languages=len(translations),
                  translations_verified=len(document.blocks) * len(translations),
                  source_sha256=document.sha256,
                  checks=['Workbook identity and source inventory', 'Complete translation cells and stable block IDs',
                          'Exact replacement plan', 'Protected source and recognised Outlook counterparts'],
                  not_verified=['Translation meaning and language accuracy', 'Dynamics acceptance', 'Outlook rendering'],
                  notices=list(document.notices),
                  files={name: dict(bytes=len(data), sha256=fingerprint(data.decode('utf-8'))) for name, data in files.items()})
    if output is not None:
        bundle = io.BytesIO()
        with ZipFile(bundle, 'w', compression=ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        bundle_supported = len(bundle.getvalue()) <= 10 * 1024 * 1024
        report['bundle'] = 'translated-emails.zip' if bundle_supported else None
        if not bundle_supported:
            report['notices'].append('The combined ZIP exceeds the 10 MB host download limit. Use the individual HTML files.')
        with new_directory(output) as folder:
            for name, data in files.items():
                (folder / name).write_bytes(data)
            if bundle_supported:
                (folder / 'translated-emails.zip').write_bytes(bundle.getvalue())
            (folder / 'validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report['output_directory'] = str(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('prepare', help='Extract blocks and create a blank translation workbook.')
    export.add_argument('original', type=Path)
    export.add_argument('--source-language', required=True)
    export.add_argument('--targets', required=True, nargs='+')
    export.add_argument('--output-dir', required=True, type=Path)
    export.add_argument('--keep-html-lang', action='store_true', help='Leave existing root language metadata unchanged.')
    for name in ['validate', 'complete']:
        command = commands.add_parser(name)
        command.add_argument('--job', required=True, type=Path)
        command.add_argument('--workbook', required=True, type=Path)
        if name == 'complete':
            command.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            report = prepare(args.original, args.source_language, args.targets, args.output_dir, not args.keep_html_lang)
        else:
            report = complete(args.job, args.workbook, getattr(args, 'output_dir', None))
    except (ValueError, OSError, BadZipFile, KeyError, TypeError, ParseError, InvalidFileException, IllegalCharacterError, RuntimeError) as error:
        report = dict(ok=False, errors=[dict(code='input_error', message=str(error))])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
