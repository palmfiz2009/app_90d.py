import streamlit as st
import json
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="JUOG UTUC_Trial 90-Day CRF", layout="wide")

# --- JUOG専用デザインCSS ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .block-container { 
        max-width: 1100px !important; 
        padding-top: 1.5rem !important; 
        padding-bottom: 5rem !important; 
        margin: auto !important;
    }
    h1 { 
        font-size: 26px !important; 
        color: #0F172A; 
        text-align: center; 
        margin-top: 0px !important; 
        margin-bottom: 30px !important; 
        font-weight: 800; 
        height: 40px;
    }
    .top-info-bar {
        background-color: transparent !important;
        padding: 0px !important;
        margin-bottom: 25px !important;
        border: none !important;
        min-height: 80px;
    }
    .juog-header {
        background-color: #1E3A8A;
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px;
        margin-top: 25px;
        margin-bottom: 15px;
    }
    label { font-weight: 600 !important; color: #334155 !important; }
    div[data-baseweb="select"] ul { white-space: normal !important; }
    div[role="option"] { line-height: 1.4 !important; padding: 8px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid #E2E8F0; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        color: #64748B !important;
        padding: 10px 4px !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1E3A8A !important;
        border-bottom: 3px solid #1E3A8A !important;
    }
    .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextInput input, .stTextArea textarea {
        background-color: transparent !important;
        border: 1px solid #E2E8F0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 施設リスト ---
FACILITY_LIST = [
    "選択してください", "愛知県がんセンター", "秋田大学", "愛媛大学", "大分大学", "大阪公立大学", 
    "大阪大学", "大阪府済生会野江病院", "岡山大学", "香川大学", "鹿児島大学", "関西医科大学", 
    "岐阜大学", "九州大学病院", "京都大学", "久留米大学", "神戸大学", "国立がん研究センター中央病院", 
    "国立病院機構四国がんセンター", "札幌医科大学", "千葉大学", "筑波大学", "東京科学大学", 
    "東京慈恵会医科大学", "東京慈恵会医科大学附属柏病院", "東北大学", "鳥取大学", "富山大学", 
    "長崎大学病院", "名古屋大学", "奈良県立医科大学", "新潟大学大学院 医歯学総合研究科", 
    "浜松医科大学", "原三信病院", "兵庫医科大学", "弘前大学", "北海道大学", "三重大学", 
    "横浜市立大学", "琉球大学", "和歌山県立医科大学", "その他"
]

# --- ヘルプテキスト定義 (CD分類詳細) ---
HELP_CD = """
**Clavien-Dindo 分類 (術後90日評価)**
Gradingの原則：

- **Grade I**：正常な術後経過からの逸脱で、薬物療法、または外科的治療、内視鏡的治療、IVR 治療を要さないもの。
ただし、制吐剤、解熱剤、鎮痛剤、利尿剤による治療、電解質補充、理学療法は必要とする治療には含めない。また、ベッドサイドでの創感染の開放は Grade I とする。

- **Grade II**：制吐剤、解熱剤、鎮痛剤、利尿剤以外の薬物療法を要する。輸血および中心静脈栄養を要する場合を含む。

- **Grade III**：外科的治療、内視鏡的治療、IVR 治療を要する。
    - **Grade IIIa**：全身麻酔を要さない治療
    - **Grade IIIb**：全身麻酔下での治療

- **Grade IV**：ICU 管理を要する、生命を脅かす合併症（中枢神経系の合併症を含む）
    - **Grade IVa**：単一の臓器不全（透析を含む）
    - **Grade IVb**：多臓器不全

- **Grade V**：患者の死亡
"""

# --- セッション状態初期化 ---
if 'init_90d_done' not in st.session_state:
    st.session_state['init_90d_done'] = True
    defaults = {
        "facility_name": "選択してください", "patient_id": "",
        "eval_date_90": None, "vital_abnormality_90": None, "vital_detail_90": "",
        "wbc_90": None, "hb_90": None, "plt_90": None, "neutro_90": None, "ast_90": None, "alt_90": None, "cre_90": None, "egfr_90": None, "crp_90": None,
        "pfs_status_90": None, "pfs_date_90": None, "pfs_intra_uro": [], "pfs_extra_uro": [], "pfs_existing_met": "なし",
        "img_status_90": None, "cysto_status_90": None,
        "cd_grade_90": "選択してください", "cd_detail_90": "",
        "adj_plan_90": "選択してください", "adj_other_90": "",
        "status_alive_90": None, "death_cause_90": "未選択", "death_date_90": None,
        "needs_confirm": False, "do_send": False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def send_email(report_content, pid, facility):
    try:
        mail_user = st.secrets["email"]["user"]; mail_pass = st.secrets["email"]["pass"]
        to_addrs = ["urosec@kmu.ac.jp", "yoshida.tks@kmu.ac.jp"]
        msg = MIMEMultipart(); msg['From'] = mail_user; msg['To'] = ", ".join(to_addrs)
        msg['Subject'] = f"【JUOG 90D報告】（{facility} / ID: {pid}）"
        msg.attach(MIMEText(report_content, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mail_user, mail_pass); server.send_message(msg); server.quit()
        return True
    except: return False

st.title("JUOG UTUC_Trial 術後90日目(12週) CRF")

# --- 共通ヘッダー ---
st.markdown('<div class="top-info-bar">', unsafe_allow_html=True)
col_h1, col_h2 = st.columns(2)
with col_h1:
    idx_fac = FACILITY_LIST.index(st.session_state.facility_name) if st.session_state.facility_name in FACILITY_LIST else 0
    st.session_state.facility_name = st.selectbox("施設名*", FACILITY_LIST, index=idx_fac)
with col_h2:
    st.session_state.patient_id = st.text_input("研究対象者識別コード*", value=st.session_state.patient_id)
st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🩺 診察・血液検査", "🖼 再発評価 (PFS)", "📋 安全性・治療", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">1. 身体所見・血液検査 (術後90日±14日)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.eval_date_90 = st.date_input("評価実施日*", value=st.session_state.eval_date_90)
        st.session_state.vital_abnormality_90 = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=None, horizontal=True)
        if st.session_state.vital_abnormality_90 == "異常あり": st.session_state.vital_detail_90 = st.text_input("異常の詳細*")
        st.session_state.wbc_90 = st.number_input("WBC (/μL)*", value=st.session_state.wbc_90, step=1)
        st.session_state.hb_90 = st.number_input("Hb (g/dL)*", value=st.session_state.hb_90, step=0.1)
    with c2:
        st.session_state.ast_90 = st.number_input("AST (U/L)*", value=st.session_state.ast_90, step=1)
        st.session_state.alt_90 = st.number_input("ALT (U/L)*", value=st.session_state.alt_90, step=1)
        st.session_state.cre_90 = st.number_input("Cre (mg/dL)*", value=st.session_state.cre_90, step=0.01)
        st.session_state.egfr_90 = st.number_input("eGFR (mL/min/1.73m²)*", value=st.session_state.egfr_90, step=0.1)
        st.session_state.crp_90 = st.number_input("CRP (mg/dL)*", value=st.session_state.crp_90, step=0.01)

with tab2:
    st.markdown('<div class="juog-header">2. 画像・再発評価 (PFS判定)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.img_status_90 = st.radio("CT/MRI検査の実施*", ["実施", "未実施"], index=None, horizontal=True)
        st.session_state.cysto_status_90 = st.radio("膀胱鏡検査の実施*", ["実施", "未実施"], index=None, horizontal=True)
        st.session_state.pfs_status_90 = st.radio("術後再発・増悪の有無*", ["なし", "あり"], index=None, horizontal=True)
    
    with c2:
        if st.session_state.pfs_status_90 == "あり":
            st.session_state.pfs_date_90 = st.date_input("再発・増悪確定日*", value=st.session_state.pfs_date_90)
            st.session_state.pfs_intra_uro = st.multiselect("尿路内再発部位", ["膀胱内", "対側上部尿路", "その他"])
            st.session_state.pfs_extra_uro = st.multiselect("尿路外再発・遠隔転移", ["手術局所・領域リンパ節", "肺", "肝", "骨", "遠隔リンパ節", "その他"])
            st.session_state.pfs_existing_met = st.radio("登録時既存転移巣の増大", ["なし", "あり", "既存病変なし"], horizontal=True)

with tab3:
    st.markdown('<div class="juog-header">3. 安全性および後治療の確認</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cd_opts = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
        idx_cd = cd_opts.index(st.session_state.cd_grade_90) if st.session_state.cd_grade_90 in cd_opts else 0
        st.session_state.cd_grade_90 = st.selectbox("術後90日目までの手術関連合併症 (CD分類)*", cd_opts, index=idx_cd, help=HELP_CD)
        if st.session_state.cd_grade_90 not in ["選択してください", "Grade 0"]:
            st.session_state.cd_detail_90 = st.text_area("合併症の詳細内容*", value=st.session_state.cd_detail_90)
    
    with c2:
        adj_opts = ["選択してください", "無治療（経過観察）", "EVP継続投与", "ペムブロ維持", "ニボ単剤（術後補助）", "GC/GCarbo", "その他"]
        idx_adj = adj_opts.index(st.session_state.adj_plan_90) if st.session_state.adj_plan_90 in adj_opts else 0
        st.session_state.adj_plan_90 = st.selectbox("現在の治療実施状況*", adj_opts, index=idx_adj)
        if st.session_state.adj_plan_90 == "その他":
            st.session_state.adj_other_90 = st.text_area("治療詳細*", value=st.session_state.adj_other_90)

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.status_alive_90 = st.radio("生存状況 (術後90日時点)*", ["生存", "死亡"], index=None, horizontal=True)
    
    with c2:
        if st.session_state.status_alive_90 == "死亡":
            st.session_state.death_date_90 = st.date_input("死亡日*", value=st.session_state.death_date_90)
            st.session_state.death_cause_90 = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "他病死", "治療関連死", "不明"])

    st.divider()

    # --- バリデーション & 送信 ---
    if st.button("🚀 90日目データを確定送信", type="primary", use_container_width=True):
        h_errors = []
        if st.session_state.facility_name == "選択してください": h_errors.append("・施設名")
        if not st.session_state.patient_id: h_errors.append("・識別コード")
        if not st.session_state.eval_date_90: h_errors.append("・評価実施日")
        if st.session_state.pfs_status_90 is None: h_errors.append("・再発・増悪の有無")
        elif st.session_state.pfs_status_90 == "あり" and not st.session_state.pfs_date_90: h_errors.append("・再発確定日")
        if st.session_state.cd_grade_90 == "選択してください": h_errors.append("・CD分類")
        if st.session_state.status_alive_90 is None: h_errors.append("・生存状況")
        elif st.session_state.status_alive_90 == "死亡" and st.session_state.death_cause_90 == "選択してください": h_errors.append("・死因")

        if h_errors:
            st.error("以下の必須項目を入力してください：\n" + "\n".join(h_errors))
        else:
            s_errors = [k for k, v in {"WBC":st.session_state.wbc_90, "Hb":st.session_state.hb_90, "Cre":st.session_state.cre_90}.items() if v is None]
            if s_errors:
                st.session_state.needs_confirm = True
                st.session_state.pending_s_errors = s_errors
                st.rerun()
            else:
                st.session_state.do_send = True

    if st.session_state.needs_confirm:
        st.warning(f"以下の血液データが空です：{', '.join(st.session_state.pending_s_errors)}。送信しますか？")
        if st.button("⚠️ はい、不足を承知で送信します"):
            st.session_state.do_send = True
            st.session_state.needs_confirm = False

    if st.session_state.do_send:
        def f_val(v): return str(v) if v is not None else "N/A"
        rep = f"""
【JUOG 90D CRF報告】
施設: {st.session_state.facility_name} / ID: {st.session_state.patient_id}
評価日: {st.session_state.eval_date_90}

【血液検査】
WBC:{f_val(st.session_state.wbc_90)}, Hb:{f_val(st.session_state.hb_90)}, Cre:{f_val(st.session_state.cre_90)}

【再発評価 (PFS)】
状況: {st.session_state.pfs_status_90} / 確定日: {st.session_state.pfs_date_90}
尿路内: {st.session_state.pfs_intra_uro} / 尿路外: {st.session_state.pfs_extra_uro}
既存病変増大: {st.session_state.pfs_existing_met}

【安全性・治療】
CD分類: {st.session_state.cd_grade_90} (詳細: {st.session_state.cd_detail_90})
現在の治療: {st.session_state.adj_plan_90}

【最終転帰】
生存状況: {st.session_state.status_alive_90} / 死因: {st.session_state.death_cause_90} / 死亡日: {st.session_state.death_date_90}
"""
        if send_email(rep, st.session_state.patient_id, st.session_state.facility_name):
            st.success("術後90日目のデータが正常に事務局へ送信されました。")
            st.balloons()
        st.session_state.do_send = False
