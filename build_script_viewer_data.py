#!/usr/bin/env python
"""Build viewer data from TOS files for the Different Realm script viewer.

Usage:
    python build_script_viewer_data.py
    python build_script_viewer_data.py --no-excel   # skip Excel translation loading

Outputs script_viewer/viewer-data.js with all decoded TOS blocks.
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tos import decode_tos


def is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF)


def bytes_to_unicode_tagged(content):
    """Convert a block's byte content (SJIS text + ASCII tags) to a Unicode
    string with bracket-tags preserved."""
    parts = []
    pos = 0
    while pos < len(content):
        b = content[pos]
        if is_sjis_lead(b) and pos + 1 < len(content):
            sjis_pair = bytes([content[pos], content[pos + 1]])
            try:
                char = sjis_pair.decode('shift_jis')
            except Exception:
                char = f'\\x{content[pos]:02x}\\x{content[pos + 1]:02x}'
            parts.append(char)
            pos += 2
        elif b == 0x5B:  # '['
            end = pos + 1
            while end < len(content) and content[end] != 0x5D:
                end += 1
            if end < len(content):
                try:
                    tag = content[pos:end + 1].decode('ascii')
                except UnicodeDecodeError:
                    tag = '[?]'
                parts.append(tag)
                pos = end + 1
            else:
                parts.append('[')
                pos += 1
        elif 0x20 <= b <= 0x7E:
            parts.append(chr(b))
            pos += 1
        elif b in (0x0D, 0x0A):
            pos += 1
        else:
            parts.append(f'\\x{b:02x}')
            pos += 1
    return ''.join(parts)


def strip_tags_for_display(text):
    """Strip control-code tags for display, keeping LN as newlines and
    Spaces as fullwidth spaces."""
    text = text.replace('[LN]', '\n')
    text = re.sub(r'\[Spaces(\d+)\]', lambda m: '\u3000' * int(m.group(1)), text)
    text = text.replace('[PlayerName]', 'ストックマン')
    text = re.sub(r'\[MapNameEnd\]', '', text)
    # MapName tag — just remove the tag, keep the name text that follows
    text = re.sub(r'\[MapName\]', '', text)
    text = re.sub(r'\[[^\]]+\]', '', text)
    return text


def extract_tags(raw):
    """Return a list of all tag names found in the raw text."""
    return re.findall(r'\[([^\]]+)\]', raw)


def extract_metadata(tags):
    """Extract portrait, window position, and active colors from tag list."""
    portrait = None
    window = None
    colors = set()

    for t in tags:
        if t.startswith('PortraitUp'):
            portrait = t
        elif t.startswith('PortraitDown'):
            portrait = t
        elif t.startswith('WindowUp'):
            window = 'upper'
        elif t.startswith('WindowDown'):
            window = 'lower'
        elif t.startswith('Color'):
            colors.add(t)

    return portrait, window, sorted(colors)


def load_translations(xlsx_path):
    """Load English translations from the workbook.  Returns a dict
    keyed by (sheet_title, block_num) → list of English strings."""
    translations = {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            sheet = ws.title
            for row in ws.iter_rows(min_row=2, values_only=True):
                if len(row) < 7:
                    continue
                block_val = row[1]    # col B — block number
                jp_val = row[4]       # col E — Japanese
                en_val = row[6]       # col G — English
                if block_val is not None and en_val and jp_val and str(en_val).strip() != str(jp_val).strip():
                    key = (sheet, int(block_val))
                    if key not in translations:
                        translations[key] = []
                    translations[key].append(str(en_val))
        wb.close()
        print(f"  Loaded translations from {xlsx_path}: "
              f"{sum(len(v) for v in translations.values())} translated strings "
              f"across {len(translations)} blocks")
    except ImportError:
        print("  Warning: openpyxl not installed — skipping Excel translation loading")
    except FileNotFoundError:
        print(f"  Warning: {xlsx_path} not found — skipping translation loading")
    except Exception as e:
        print(f"  Warning: Could not load translations: {e}")
    return translations


def build_viewer_data(load_excel=True):
    """Decode all TOS files and build the viewer payload."""

    # Gather TOS files
    talk_files = sorted(glob.glob('original\\REALM\\TALK\\*.TOS'))
    map_files = sorted(glob.glob('original\\REALM\\MAP\\*.TOS'))
    all_files = talk_files + map_files
    all_files = [f for f in all_files
                 if '_parsed' not in f
                 and '_encoded' not in f
                 and '_roundtrip' not in f]

    print(f"Found {len(all_files)} TOS files ({len(talk_files)} TALK, {len(map_files)} MAP)")

    # Load translations
    translations = {}
    if load_excel:
        translations = load_translations('DiffRealm_Text.xlsx')

    records = []
    record_id = 0
    decode_errors = []

    for tos_file in all_files:
        name = os.path.basename(tos_file)
        stem = name.replace('.TOS', '')
        path_type = 'TALK' if '\\TALK\\' in tos_file else 'MAP'

        # Decode the TOS binary → parsed file
        parsed_file = tos_file.replace('.TOS', '_parsed.TOS')
        try:
            decode_tos(tos_file)
        except Exception as e:
            decode_errors.append(f"{name}: {e}")
            continue

        if not os.path.exists(parsed_file):
            continue

        # Read parsed blocks
        with open(parsed_file, 'rb') as f:
            lines = [l.rstrip(b'\n') for l in f.readlines()]

        for line in lines:
            if not line or line[0:1] != b'{':
                continue

            try:
                brace_end = line.index(b'}')
                block_num = int(line[1:brace_end])
            except (ValueError, IndexError):
                continue

            content = line[brace_end + 1:]
            raw = bytes_to_unicode_tagged(content)
            text = strip_tags_for_display(raw)
            tags = extract_tags(raw)
            portrait, window, colors = extract_metadata(tags)

            # Check for English translation
            english = ''
            key = (stem, block_num)
            if key in translations:
                english = '\n'.join(translations[key])

            records.append({
                'id': record_id,
                'file': name,
                'path': path_type,
                'block': block_num,
                'raw': raw,
                'text': text,
                'english': english,
                'portrait': portrait,
                'window': window,
                'colors': colors,
                'tags': tags,
            })
            record_id += 1

        # Clean up parsed file
        try:
            os.remove(parsed_file)
        except OSError:
            pass

    if decode_errors:
        print(f"  Decode errors ({len(decode_errors)}):")
        for err in decode_errors:
            print(f"    {err}")

    file_names = sorted(set(r['file'] for r in records))
    translated_count = sum(1 for r in records if r['english'])

    payload = {
        'meta': {
            'totalBlocks': len(records),
            'translatedBlocks': translated_count,
            'fileCount': len(file_names),
            'files': file_names,
        },
        'records': records,
    }

    return payload


def main():
    load_excel = '--no-excel' not in sys.argv

    print("Building Different Realm script viewer data...")
    data = build_viewer_data(load_excel=load_excel)

    output_dir = Path('script_viewer')
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / 'viewer-data.js'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('window.DR_VIEWER_DATA = ')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')

    size_kb = output_path.stat().st_size / 1024
    meta = data['meta']
    print(f"\nDone! Wrote {output_path} ({size_kb:.1f} KB)")
    print(f"  {meta['totalBlocks']} blocks from {meta['fileCount']} files")
    print(f"  {meta['translatedBlocks']} blocks have English translations")


if __name__ == '__main__':
    main()
