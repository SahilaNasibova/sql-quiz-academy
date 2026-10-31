from html import escape
import json
import streamlit as st

CSS = '''<style>
html, body, [class*="css"] {font-family: Inter, sans-serif;}
.stApp {background: #f5f7fc;}
.block-container {padding-top: 2rem;max-width:1450px;}
h1,h2,h3 {color:#101936;letter-spacing:-.035em;}
[data-testid="stSidebar"] {background:linear-gradient(160deg,#19253e,#111d33);border-right:1px solid #29364d;}
[data-testid="stSidebar"] * {color:#eef0ff;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {color:#aebbd9;}
[data-testid="stSidebar"] .stButton button {background:#293650;border:1px solid #53607c;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:12px;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:12px;border-radius:10px;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:linear-gradient(110deg,#8254fa,#6037e9);}
.brand {font-size:23px;font-weight:800;line-height:1.2;padding:10px 0 30px;}
.brand span {font-size:42px;color:#b294ff;float:left;margin-right:12px;}
.breadcrumb {color:#75809a;font-size:13px;margin-bottom:20px;}
.hero {background:linear-gradient(115deg,#7649f5,#5030d2);border-radius:15px;padding:30px 38px;display:flex;gap:24px;justify-content:space-between;align-items:center;color:white;margin:16px 0 20px;box-shadow:0 10px 30px #6744eb18;}
.hero h2 {color:white;font-size:30px;margin:0 0 8px;letter-spacing:-.025em;}
.hero p {color:#eee6ff;font-size:17px;max-width:480px;}
.code-window {background:#19243a;border:1px solid #9980f7;box-shadow:0 16px 25px #24116c55;border-radius:13px;padding:18px 24px;min-width:290px;font:14px/1.9 monospace;transform:rotate(-1deg);}
.dots {color:#f4c350;letter-spacing:5px;margin-bottom:10px;}.sql {color:#bd94ff;}.string {color:#eceb64;}
.stat {background:white;border:1px solid #e5eaf6;border-radius:12px;padding:18px;display:flex;gap:16px;align-items:center;margin-bottom:22px;min-height:100px;}
.stat-icon {color:#7146ed;background:#f0eaff;border-radius:12px;padding:12px;font-size:24px;}
.stat-label {font-size:13px;color:#455071;}.stat-value {font-weight:800;font-size:28px;color:#101936;}
.quiz-card {background:white;border:1px solid #e5eaf6;border-radius:13px;padding:22px;min-height:210px;}
.quiz-icon {font-size:32px;color:#7040f5;background:#f1ecff;border-radius:12px;display:inline-block;padding:10px 17px;margin-bottom:12px;}
.quiz-card h3 {font-size:19px;margin:0 0 9px;}.quiz-card p {font-size:14px;color:#68718d;line-height:1.6;}
.badge {font-size:12px;color:#17824c;background:#e3f8ec;border-radius:7px;padding:4px 9px;}
.panel {background:white;border:1px solid #e5eaf6;border-radius:13px;padding:22px;margin-top:20px;}
.tip {background:#ede6ff;}.empty {border:1px dashed #d7ddec;border-radius:9px;padding:20px;color:#737d98;font-size:14px;}
.stButton button {border-radius:9px;font-weight:600;}
.stButton button[kind="primary"] {background:linear-gradient(110deg,#8150fa,#6035e6);border:0;}
[data-testid="stMetric"] {background:white;border:1px solid #e5eaf6;padding:18px;border-radius:14px;}
@media(max-width:800px) {.hero{padding:22px;}.code-window{display:none;}.hero h2{font-size:24px;}.block-container{padding:1.2rem;}}
</style>'''


def dashboard(db,user,start):
    st.markdown('<div class="breadcrumb">⌂ &nbsp; / &nbsp; Platforma &nbsp; / &nbsp; İcmal</div>',unsafe_allow_html=True)
    st.title('SQL öyrən, biliklərini sına!')
    st.caption('Oracle SQL və PL/SQL üzrə şəxsi öyrənmə məkanınız.')
    st.markdown('''<div class="hero"><div><h2>SQL-ə hakim olmağa hazırsan?</h2><p>Praktik testlərlə biliklərini yoxla, yeni mövzuları öyrən və SQL bacarıqlarını inkişaf etdir.</p></div><div class="code-window"><div class="dots">● ● ●</div><span class="sql">SELECT</span> knowledge<br><span class="sql">FROM</span> academy<br><span class="sql">WHERE</span> success = <span class="string">'TRUE'</span>;</div></div>''',unsafe_allow_html=True)
    questions=db.questions()
    topics=sorted({q['topic'] for q in questions})
    results=[json.loads(r['result']) for r in db.results(user['email'])]
    stats=[('▤','Mövcud mövzular',str(len(topics))),('✓','Tamamlanan testlər',str(len(results))),('▥','Orta nəticə',f"{sum(r['percent'] for r in results)/len(results):.1f}%" if results else '—'),('♜','Ən yüksək nəticə',f"{max(r['percent'] for r in results):g}%" if results else '—')]
    for col,(icon,label,value) in zip(st.columns(4),stats):
        col.markdown(f'<div class="stat"><div class="stat-icon">{icon}</div><div><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div></div>',unsafe_allow_html=True)
    st.subheader('Biliklərini sına')
    if not topics:
        st.info('Müəllim sualları əlavə etdikdən sonra testlər burada görünəcək.')
    columns=st.columns(3)
    for i,topic in enumerate(topics):
        count=sum(q['topic']==topic for q in questions)
        with columns[i%3]:
            st.markdown(f'<div class="quiz-card"><div class="quiz-icon">{ "⌘" if "PL" in topic else "▱" }</div><h3>{escape(topic)}</h3><span class="badge">Bilik yoxlaması</span><p>▤ &nbsp; {count} sual &nbsp; · &nbsp; ◷ {db.duration()} dəqiqə</p><p>{escape(topic)} üzrə biliklərini praktiki suallarla sına.</p></div>',unsafe_allow_html=True)
            st.button('▶  Testə başla',key=f'dash_{topic}',type='primary',use_container_width=True,on_click=start,args=(topic,))
    left,right=st.columns([1.2,1])
    with left:
        st.markdown('<div class="panel"><h3>◷ &nbsp; Son nəticələrim</h3>'+(''.join(f'<p>{escape(r["finished"][:16])} UTC · <b>{r["percent"]}%</b></p>' for r in results[:3]) if results else '<div class="empty">Hələlik heç bir test nəticəniz yoxdur.<br>Testlərə başla və burada nəticələrini izlə!</div>')+'</div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel tip"><h3>♧ &nbsp; SQL ipucu</h3><p>NULL dəyərlərini yoxlamaq üçün <code>IS NULL</code> istifadə edin.</p><code>SELECT * FROM employees<br>WHERE department_id IS NULL;</code></div>',unsafe_allow_html=True)
