"""Excel input template and strict source-bound workbook reader."""
import io
import json
import math
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from html_blocks import json_text

VERSION = 1
HEADER_ROW = 6
FIRST_ROW = HEADER_ROW + 1
HEADERS = ['Block ID', 'Type', 'Context']
META_SHEET = '_EmailStudio'


def metadata(document, source_language, targets, update_lang):
    return dict(format_version=VERSION, source_sha256=document.sha256,
                inventory_sha256=document.inventory_sha256, source_language=source_language,
                target_languages=targets, update_html_lang=update_lang)


def text_cell(sheet, row, column, value):
    cell = sheet.cell(row, column, value)
    # Even strings beginning '=' are literal wording, never spreadsheet formulas.
    cell.data_type = 's'
    cell.number_format = '@'
    return cell


def build_workbook(document, config):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Translations'
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.tabColor = '174F37'
    targets = config['target_languages']
    headers = HEADERS + [f"Source ({config['source_language']})"] + targets
    text_cell(sheet, 2, 1, 'Email translations')
    sheet['A2'].font = Font(name='Arial', size=16, bold=True, color='174F37')
    summary = f'{len(document.blocks)} blocks x {len(targets)} languages = {len(document.blocks) * len(targets)} translations'
    text_cell(sheet, 3, 1, summary)
    text_cell(sheet, 4, 1, 'Fill every yellow cell. Keep IDs and source wording unchanged. Upload the completed .xlsx in the same conversation.')
    text_cell(sheet, 5, 1, 'Rows are individual text runs. Inline formatting and protected tokens stay in the HTML. Long text is available in the formula bar.')
    sheet.row_dimensions[2].height = 28
    sheet.row_dimensions[3].height = 22
    sheet.row_dimensions[4].height = 23
    sheet.row_dimensions[5].height = 23
    widths = [14, 23, 42, 52] + [52] * len(targets)
    for column, (title, width) in enumerate(zip(headers, widths), 1):
        cell = text_cell(sheet, HEADER_ROW, column, title)
        cell.fill = PatternFill('solid', fgColor='174F37')
        cell.font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(right=Side(style='thin', color='FFFFFF'))
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.row_dimensions[HEADER_ROW].height = 30
    for row, block in enumerate(document.blocks, FIRST_ROW):
        values = [block.id, block.kind, block.context, block.source] + [''] * len(targets)
        for column, value in enumerate(values, 1):
            cell = text_cell(sheet, row, column, value)
            cell.font = Font(name='Arial', size=11, color='171C19')
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            cell.fill = PatternFill('solid', fgColor='FFF2CC' if column > 4 else 'F2F5F3' if row % 2 else 'FFFFFF')
            cell.protection = Protection(locked=column <= 4)
        lines = max(math.ceil(len(block.source) / 47), math.ceil(len(block.context) / 37), 2)
        sheet.row_dimensions[row].height = min(409, 16 * lines + 12)
    last_row = FIRST_ROW + len(document.blocks) - 1
    last_column = get_column_letter(len(headers))
    table = Table(displayName='EmailTranslations', ref=f'A{HEADER_ROW}:{last_column}{last_row}')
    table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium4', showRowStripes=False, showColumnStripes=False)
    sheet.add_table(table)
    sheet.freeze_panes = f'E{FIRST_ROW}'
    sheet.print_title_rows = f'{HEADER_ROW}:{HEADER_ROW}'
    # Protection is an accidental-edit aid, not trust or security. Import revalidates everything.
    sheet.protection.sheet = True
    sheet.protection.autoFilter = False
    sheet.protection.selectLockedCells = False
    sheet.protection.selectUnlockedCells = False
    sheet.protection.set_password('email-studio')
    hidden = book.create_sheet(META_SHEET)
    for row, (key, value) in enumerate(sorted(config.items()), 1):
        text_cell(hidden, row, 1, key)
        text_cell(hidden, row, 2, json_text(value))
    hidden.sheet_state = 'veryHidden'
    output = io.BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


def issue(code, message, **details):
    return dict(code=code, message=message, **details)


def read_workbook(data, document, config):
    """Return all expected translations plus actionable errors; never infer missing values."""
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Upload an .xlsx workbook smaller than 10 MB.')
    with ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 300 or sum(e.file_size for e in entries) > 100 * 1024 * 1024:
            raise ValueError('The workbook exceeds supported expanded size or entry limits.')
        if any('vbaproject' in e.filename.lower() or 'externallinks/' in e.filename.lower() for e in entries):
            raise ValueError('Macros and external workbook links are not supported.')
    book = load_workbook(io.BytesIO(data), data_only=False, keep_links=False)
    try:
        if set(book.sheetnames) != {'Translations', META_SHEET}:
            return {}, [issue('sheets', 'Keep the Translations worksheet and its original workbook metadata. Remove extra worksheets.')]
        hidden = book[META_SHEET]
        if hidden.max_row != len(config) or hidden.max_column != 2:
            return {}, [issue('metadata', 'Workbook metadata is missing or changed. Use the original template.')]
        received = {}
        for key, value in hidden.iter_rows(values_only=True):
            if not isinstance(key, str) or key in received or not isinstance(value, str):
                return {}, [issue('metadata', 'Workbook metadata is invalid. Use the original template.')]
            try:
                received[key] = json.loads(value)
            except (ValueError, TypeError):
                return {}, [issue('metadata', 'Workbook metadata is invalid. Use the original template.')]
        if json_text(received) != json_text(config):
            return {}, [issue('source_mismatch', 'This workbook belongs to a different email or language selection, or its metadata was changed.')]
        sheet = book['Translations']
        headers = HEADERS + [f"Source ({config['source_language']})"] + config['target_languages']
        if sheet.max_column != len(headers) or [c.value for c in sheet[HEADER_ROW]] != headers:
            return {}, [issue('headers', 'Language columns or table headers changed. Restore the original columns.')]
        if sheet.max_row > len(document.blocks) + FIRST_ROW + 100:
            return {}, [issue('rows', 'The workbook contains too many extra rows. Use the original template.')]
        expected = {b.id: b for b in document.blocks}
        seen, errors = set(), []
        translations = {target: {} for target in config['target_languages']}
        for row in sheet.iter_rows(min_row=FIRST_ROW):
            if all(c.value is None for c in row):
                continue
            identity = row[0].value
            if not isinstance(identity, str) or identity not in expected:
                errors.append(issue('unknown_id', f'Row {row[0].row}: unknown or missing block ID.', row=row[0].row))
                continue
            if identity in seen:
                errors.append(issue('duplicate_id', f'{identity}: duplicate block ID.', block_id=identity, row=row[0].row))
                continue
            seen.add(identity)
            block = expected[identity]
            if [c.value for c in row[:4]] != [block.id, block.kind, block.context, block.source] or any(c.data_type == 'f' for c in row[:4]):
                errors.append(issue('source_changed', f'{identity}: original ID, type, context or source wording changed.', block_id=identity, row=row[0].row))
            for target, cell in zip(config['target_languages'], row[4:]):
                detail = dict(block_id=identity, language=target, cell=cell.coordinate, row=cell.row)
                if cell.data_type == 'f':
                    errors.append(issue('formula', f'{target}: {identity} contains a formula. Enter literal translation text.', **detail))
                elif not isinstance(cell.value, str) or not cell.value.strip():
                    errors.append(issue('missing_translation', f'{target}: {identity} needs translation text. Format numeric wording as Text.', **detail))
                elif len(cell.value) > 30000:
                    errors.append(issue('text_length', f'{target}: {identity} exceeds 30,000 characters.', **detail))
                else:
                    translations[target][identity] = cell.value
        for identity in sorted(set(expected) - seen):
            errors.append(issue('missing_id', f'{identity}: translation row is missing.', block_id=identity))
        # Render each completed language to exercise the exact patch/guard before any file is published.
        for target, values in translations.items():
            if set(values) == set(expected):
                try:
                    document.render(values, target, config['update_html_lang'])
                except ValueError as error:
                    errors.append(issue('invalid_translation', f'{target}: {error}', language=target))
        return translations, errors
    finally:
        book.close()
