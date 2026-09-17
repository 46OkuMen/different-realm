import openpyxl

# Load the workbook
wb = openpyxl.load_workbook('DiffRealm_Text.xlsx')

# Stats storage
sheet_stats = []
grand_total_strings = 0
grand_total_truly_translated = 0  # EN != JP
grand_total_placeholders = 0      # EN == JP (copied from JP, not translated)

print('='*120)
print('TRANSLATION PROGRESS ANALYSIS - DiffRealm_Text.xlsx')
print('='*120)
print('')
print('IMPORTANT: This project stores translations in Column G.')
print('Column G = English (target language)')
print('Column E = Japanese (source language)')
print('Status: Translated when EN text is DIFFERENT from JP text')
print('Status: Placeholder when EN text is IDENTICAL to JP text (not yet translated)')
print('='*120)

# Process each worksheet
for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    
    total_strings = 0
    truly_translated = 0        # EN != JP
    placeholders = 0            # EN == JP
    
    examples_translated = []
    examples_placeholder = []
    
    # Iterate through rows (skip header if present, start from row 2)
    for row in ws.iter_rows(min_row=2, values_only=False):
        col_e = row[4]  # Column E (Japanese)
        col_g = row[6]  # Column G (English)
        
        # Check if column E has text (Japanese)
        jp_text = col_e.value if col_e else None
        en_text = col_g.value if col_g else None
        
        if jp_text and isinstance(jp_text, str) and jp_text.strip():
            total_strings += 1
            
            # Normalize for comparison
            jp_normalized = jp_text.strip()
            en_normalized = en_text.strip() if (en_text and isinstance(en_text, str)) else ''
            
            # Check if truly translated (different text)
            if en_normalized and en_normalized != jp_normalized:
                truly_translated += 1
                if len(examples_translated) < 3:
                    examples_translated.append((jp_normalized[:45], en_normalized[:45]))
            else:
                # Placeholder (same as JP or empty)
                placeholders += 1
                if len(examples_placeholder) < 3:
                    examples_placeholder.append(jp_normalized[:50])
    
    # Calculate percentage
    pct_translated = (truly_translated / total_strings * 100) if total_strings > 0 else 0
    
    sheet_stats.append({
        'name': sheet_name,
        'total': total_strings,
        'translated': truly_translated,
        'placeholder': placeholders,
        'pct': pct_translated,
        'examples_translated': examples_translated,
        'examples_placeholder': examples_placeholder
    })
    
    grand_total_strings += total_strings
    grand_total_truly_translated += truly_translated
    grand_total_placeholders += placeholders

# Print summary table
header_fmt = '{:<20} {:<10} {:<12} {:<12} {:<12}'
print('')
print(header_fmt.format('Sheet Name', 'Total', 'Translated', 'Placeholder', '% Translated'))
print('-' * 70)

for stats in sheet_stats:
    print('{:<20} {:<10} {:<12} {:<12} {:<11.1f}%'.format(
        stats['name'], 
        stats['total'], 
        stats['translated'], 
        stats['placeholder'], 
        stats['pct']
    ))

print('-' * 70)
grand_pct = (grand_total_truly_translated / grand_total_strings * 100) if grand_total_strings > 0 else 0
print('{:<20} {:<10} {:<12} {:<12} {:<11.1f}%'.format(
    'GRAND TOTAL', 
    grand_total_strings, 
    grand_total_truly_translated, 
    grand_total_placeholders, 
    grand_pct
))

# Show examples
print('')
print('')
print('='*120)
print('EXAMPLE TRANSLATIONS (where EN text differs from JP text):')
print('='*120)
for stats in sheet_stats:
    if stats['examples_translated']:
        print('')
        print('[{}]'.format(stats['name']))
        for jp, en in stats['examples_translated']:
            print('  JP: {}'.format(jp))
            print('  EN: {}'.format(en))
            print()

# Only show first 10 sheets with placeholders
print('')
print('')
print('='*120)
print('EXAMPLE STRINGS WAITING FOR TRANSLATION (First 3 placeholders per sheet, showing first 10 sheets):')
print('='*120)
for idx, stats in enumerate(sheet_stats):
    if idx >= 10:
        print('')
        print('[... and {} more sheets with placeholder strings ...]'.format(len(sheet_stats) - 10))
        break
    if stats['examples_placeholder']:
        print('')
        print('[{}]'.format(stats['name']))
        for jp in stats['examples_placeholder']:
            print('  {}'.format(jp))

print('')
print('')
print('='*120)
print('SUMMARY:')
print('='*120)
print('Total strings to translate: {:,}'.format(grand_total_strings))
print('Strings translated:         {:,} ({:.1f}%)'.format(grand_total_truly_translated, grand_pct))
print('Strings awaiting translation: {:,} ({:.1f}%)'.format(grand_total_placeholders, 100 - grand_pct))
print('Number of TOS files:        {}'.format(len(sheet_stats)))
