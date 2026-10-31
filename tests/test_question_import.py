import io
import pytest
from openpyxl import Workbook
from core import Academy
from question_import import parse_questions


def workbook(rows):
    book=Workbook()
    for row in rows:
        book.active.append(row)
    data=io.BytesIO()
    book.save(data)
    return data.getvalue()

HEADER=['№','Sual','Variant A','Variant B','Variant C','Variant D','Düzgün cavab','Qısa izah']
ROW=[1,'Düzgün SQL hansıdır?',"SELECT * FROM loans WHERE name = 'A';",'UPDATE loans','DELETE loans','DROP loans','A','SELECT məlumatı oxuyur.']


def test_azerbaijani_workbook_import_is_usable_and_idempotent(tmp_path):
    items=parse_questions(workbook([HEADER,ROW]),'Oracle_SQL_15_Test_Suallari.xlsx')
    assert items[0]['topic']=='Oracle SQL' and items[0]['points']==1
    assert items[0]['options'][0]==ROW[2] and items[0]['explanation']==ROW[-1]
    db=Academy(f'sqlite:///{tmp_path}/import.db','teacher@example.com')
    db.provision_teacher('teacher-password')
    assert db.import_questions('teacher@example.com',items)==dict(added=1,skipped=0,total=1)
    assert db.import_questions('teacher@example.com',items)==dict(added=0,skipped=1,total=1)
    aid=db.start('teacher@example.com','Oracle SQL')
    db.answer('teacher@example.com',aid,0,0)
    assert db.finish('teacher@example.com',aid)['percent']==100


def test_english_csv_optional_columns_and_multiline_sql():
    data=b'prompt,A,B,C,D,answer\n"SQL\nSELECT 1 FROM dual;",1,0,NULL,Error,A\n'
    q=parse_questions(data,'questions.csv','PL/SQL',3)[0]
    assert '\nSELECT' in q['prompt'] and q['topic']=='PL/SQL' and q['points']==3
    assert q['explanation']==''


def test_explicit_topic_points_and_blank_rows():
    data=workbook([['Oracle quiz'],HEADER+['Mövzu','Bal'],ROW+['JOIN',5],[],[None]*10])
    q=parse_questions(data,'questions.xlsx')[0]
    assert q['topic']=='JOIN' and q['points']==5


def test_invalid_answer_reports_excel_row():
    row=ROW.copy();row[6]='E'
    with pytest.raises(ValueError,match='sətir 2'):
        parse_questions(workbook([HEADER,row]),'questions.xlsx')


def test_bad_row_prevents_partial_import(tmp_path):
    items=parse_questions(workbook([HEADER,ROW]),'questions.xlsx')
    db=Academy(f'sqlite:///{tmp_path}/atomic.db','teacher@example.com')
    with pytest.raises(ValueError):
        db.import_questions('teacher@example.com',items+[{**items[0],'points':0}])
    assert not db.questions()
    with pytest.raises(PermissionError):
        db.import_questions('student@example.com',items)


def test_duplicate_rows_in_same_batch_are_skipped(tmp_path):
    items=parse_questions(workbook([HEADER,ROW,ROW]),'questions.xlsx')
    db=Academy(f'sqlite:///{tmp_path}/duplicates.db','teacher@example.com')
    assert db.import_questions('teacher@example.com',items)==dict(added=1,skipped=1,total=2)


def test_missing_headers_and_invalid_file():
    with pytest.raises(ValueError,match='Sütunlar'):
        parse_questions(workbook([['Wrong','Columns']]),'questions.xlsx')
    with pytest.raises(ValueError,match='Excel'):
        parse_questions(b'not an excel file','questions.xlsx')


def test_more_than_500_questions_is_rejected():
    with pytest.raises(ValueError,match='500'):
        parse_questions(workbook([HEADER]+[ROW]*501),'questions.xlsx')
