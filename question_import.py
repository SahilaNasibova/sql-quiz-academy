"""Parse teacher uploads as data; never execute workbook formulas or SQL text."""
import csv
import io
import re
import unicodedata
import zipfile
from openpyxl import load_workbook

ALIASES = {
    'prompt': ['prompt','question','sual','sual metni'],
    'topic': ['topic','movzu'],
    'A': ['a','variant a','a varianti','option a'],
    'B': ['b','variant b','b varianti','option b'],
    'C': ['c','variant c','c varianti','option c'],
    'D': ['d','variant d','d varianti','option d'],
    'answer': ['answer','correct answer','duzgun cavab','cavab'],
    'points': ['points','point','bal'],
    'explanation': ['explanation','izah','qisa izah'],
}
REQUIRED = {'prompt','A','B','C','D','answer'}


def normalized(value):
    value=str(value or '').strip().lower().translate(str.maketrans({'ə':'e','ı':'i'}))
    value=''.join(c for c in unicodedata.normalize('NFKD',value) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+',' ',value).strip()

LOOKUP={normalized(alias):name for name,aliases in ALIASES.items() for alias in aliases}


def header_mapping(row):
    mapping={}
    for i,value in enumerate(row):
        name=LOOKUP.get(normalized(value))
        if name:
            if name in mapping:
                raise ValueError(f'Təkrarlanan sütun: {name}.')
            mapping[name]=i
    return mapping


def cell(row,index):
    value=row[index] if index < len(row) else None
    return '' if value is None else str(value).strip()


def parse_questions(data,filename,default_topic='Oracle SQL',default_points=1):
    if not data or len(data)>5_000_000:
        raise ValueError('Fayl boş olmamalı və ən çox 5 MB olmalıdır.')
    if not default_topic.strip() or not 1 <= int(default_points) <= 100:
        raise ValueError('Standart mövzu və 1–100 arası bal seçin.')
    suffix=filename.rsplit('.',1)[-1].lower()
    workbook=None
    if suffix=='xlsx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist())>50_000_000:
                    raise ValueError('Excel faylının açılmış həcmi çox böyükdür.')
            workbook=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
            sheets=[(sheet.title,sheet.iter_rows(values_only=True)) for sheet in workbook]
        except ValueError:
            raise
        except Exception:
            raise ValueError('Excel faylı oxunmadı. Etibarlı .xlsx faylı seçin.') from None
    elif suffix=='csv':
        try:
            content=data.decode('utf-8-sig')
            try:
                dialect=csv.Sniffer().sniff(content[:8192],delimiters=',;\t')
            except csv.Error:
                dialect=csv.excel
            sheets=[('CSV',csv.reader(io.StringIO(content),dialect))]
        except UnicodeDecodeError:
            raise ValueError('CSV faylını UTF-8 kodlaşdırması ilə saxlayın.') from None
    else:
        raise ValueError('Yalnız .xlsx və .csv faylları dəstəklənir.')
    items=[]
    recognized=False
    try:
        for title,rows in sheets:
            mapping=None
            for number,row in enumerate(rows,1):
                if mapping is None:
                    candidate=header_mapping(row)
                    if REQUIRED.issubset(candidate):
                        mapping=candidate
                        recognized=True
                    if number>=20 and mapping is None:
                        break
                    continue
                if not any(value is not None and str(value).strip() for value in row):
                    continue
                values={name:cell(row,index) for name,index in mapping.items()}
                if any(not values.get(name) for name in REQUIRED):
                    raise ValueError(f'{title}, sətir {number}: sual, dörd variant və düzgün cavab doldurulmalıdır.')
                answer=values['answer'].upper().strip()
                match=re.fullmatch(r'([ABCD])(?:[.)])?',answer)
                if not match:
                    raise ValueError(f'{title}, sətir {number}: düzgün cavab A, B, C və ya D olmalıdır.')
                raw_points=values.get('points') or str(default_points)
                try:
                    points=float(raw_points)
                    if not points.is_integer() or not 1<=points<=100:
                        raise ValueError()
                except ValueError:
                    raise ValueError(f'{title}, sətir {number}: bal 1–100 arası tam ədəd olmalıdır.') from None
                items.append(dict(topic=values.get('topic') or default_topic.strip(),prompt=values['prompt'],
                                  options=[values[k] for k in 'ABCD'],answer='ABCD'.index(match[1]),
                                  points=int(points),explanation=values.get('explanation','')))
                if len(items)>500:
                    raise ValueError('Bir faylda ən çox 500 sual ola bilər.')
        if not recognized:
            raise ValueError('Sütunlar tanınmadı. Sual, Variant A, Variant B, Variant C, Variant D və Düzgün cavab sütunları tələb olunur. İngilis şablonu da dəstəklənir.')
        if not items:
            raise ValueError('Faylda sual tapılmadı.')
        return items
    finally:
        if workbook:
            workbook.close()
