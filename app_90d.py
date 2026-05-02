import streamlit as st
import json
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="JUOG UTUC_Consolidative 90-Day CRF", layout="wide")

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
    /* 入力欄の微調整 */
    .stNumberInput { margin-bottom: 10px; }
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

# --- セッション状態初期化 ---
if 'init_90d_done' not in st.session_state:
    st.session_state['init_90d_done'] = True
    defaults = {
        "facility_name": "選択してください", "patient_id": "",
        "op_date_90": None, "eval_date_90": None, "vital_abnormality_90": None, "vital_detail_90": "",
        "wbc_90": None, "hb_90": None, "plt_90": None,
        "ast_90": None, "alt_90": None, "ldh_90": None,
        "alb_90": None, "cre_90": None, "egfr_90": None, "crp_90": None,
        "neutro_90": None, "lympho_90": None, "mono_90": None, "eosino_90": None, "baso_90": None,
        "cytology_90": "選択してください",
        "cd_grade_90": "選択してください", "cd_detail_90": "",
        "adj_plan_90": "選択してください", "adj_other_90": "",
        "pfs_intra_status": None, "pfs_intra_date": None, "pfs_intra_site": [], "pfs_intra_tx": "未選択", "pfs_intra_tx_detail": "",
        "pfs_recist_status": None, "pfs_recist_date": None, "pfs_recist_site": [], "pfs_recist_tx": "未選択", "pfs_recist_tx_detail": "",
        "status_alive_90": None, "final_visit_date_90": None, "death_cause_90": "選択してください", "death_date_90": None,
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

st.title("JUOG UTUC_Consolidative 術後90日目 CRF")

# --- 共通ヘッダー ---
col_h1, col_h2 = st.columns(2)
with col_h1:
    idx_fac = FACILITY_LIST.index(st.session_state.facility_name) if st.session_state.facility_name in FACILITY_LIST else 0
    st.session_state.facility_name = st.selectbox("施設名*", FACILITY_LIST, index=idx_fac)
with col_h2:
    st.session_state.patient_id = st.text_input("研究対象者識別コード*", value=st.session_state.patient_id)

tab1, tab2, tab3, tab4 = st.tabs(["🩺 診察・検査", "📋 安全性・治療状況", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">1. 身体所見・検査 (術後90日±14日)</div>', unsafe_allow_html=True)
    
    # 基本情報
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.op_date_90 = st.date_input("手術実施日*", value=st.session_state.op_date_90)
        st.session_state.eval_date_90 = st.date_input("評価実施日(来院日)*", value=st.session_state.eval_date_90)
    with c2:
        st.session_state.vital_abnormality_90 = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=None, horizontal=True)
        cyto_opts = ["選択してください", "NILM (Class I・II)", "AUC (Class III相当)", "SHGUC (Class IV相当)", "HGUC (Class V相当)", "LGUC", "判定不能", "未実施"]
        idx_cyto = cyto_opts.index(st.session_state.cytology_90) if st.session_state.cytology_90 in cyto_opts else 0
        st.session_state.cytology_90 = st.selectbox("尿細胞診結果*", cyto_opts, index=idx_cyto)

    st.markdown("---")
    
    # 血液検査セクション (画像に基づいたレイアウト)
    st.markdown("**【血液検査データ】**")
    lab_col1, lab_col2 = st.columns(2)
    
    with lab_col1:
        st.session_state.wbc_90 = st.number_input("WBC (/μL)*", value=st.session_state.wbc_90, step=1)
        st.session_state.hb_90 = st.number_input("Hb (g/dL)*", value=st.session_state.hb_90, step=0.1)
        st.session_state.plt_90 = st.number_input("PLT (x10^4/μL)*", value=st.session_state.plt_90, step=0.1)
        st.session_state.ast_90 = st.number_input("AST (U/L)*", value=st.session_state.ast_90, step=1)
        st.session_state.alt_90 = st.number_input("ALT (U/L)*", value=st.session_state.alt_90, step=1)

    with lab_col2:
        st.session_state.ldh_90 = st.number_input("LDH (U/L)*", value=st.session_state.ldh_90, step=1)
        st.session_state.alb_90 = st.number_input("Alb (g/dL)*", value=st.session_state.alb_90, step=0.1)
        st.session_state.cre_90 = st.number_input("Cre (mg/dL)*", value=st.session_state.cre_90, step=0.01)
        st.session_state.egfr_90 = st.number_input("eGFR (mL/min/1.73m²)*", value=st.session_state.egfr_90, step=0.1)
        st.session_state.crp_90 = st.number_input("CRP (mg/dL)*", value=st.session_state.crp_90, step=0.01)

    # 白血球分画
    st.markdown("### 白血球分画 (%)")
    d1, d2, d3, d4, d5 = st.columns(5)
    with d1: st.session_state.neutro_90 = st.number_input("Neutro*", value=st.session_state.neutro_90, step=0.1)
    with d2: st.session_state.lympho_90 = st.number_input("Lympho*", value=st.session_state.lympho_90, step=0.1)
    with d3: st.session_state.mono_90 = st.number_input("Mono*", value=st.session_state.mono_90, step=0.1)
    with d4: st.session_state.eosino_90 = st.number_input("Eosino*", value=st.session_state.eosino_90, step=0.1)
    with d5: st.session_state.baso_90 = st.number_input("Baso*", value=st.session_state.baso_90, step=0.1)

with tab2:
    st.markdown('<div class="juog-header">2. 安全性評価および術後補助療法の状況</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cd_opts = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
        idx_cd = cd_opts.index(st.session_state.cd_grade_90) if st.session_state.cd_grade_90 in cd_opts else 0
        st.session_state.cd_grade_90 = st.selectbox("術後90日までの手術関連合併症 (CD分類)*", cd_opts, index=idx_cd)
        if st.session_state.cd_grade_90 not in ["選択してください", "Grade 0"]:
            st.session_state.cd_detail_90 = st.text_area("合併症の詳細内容*", value=st.session_state.cd_detail_90)
    
    with c2:
        adj_opts = ["選択してください", "無治療（経過観察）", "後治療を計画中", "EVP継続投与", "ペムブロ維持", "ニボ単剤", "GC療法", "GCarbo療法", "その他"]
        idx_adj = adj_opts.index(st.session_state.adj_plan_90) if st.session_state.adj_plan_90 in adj_opts else 0
        st.session_state.adj_plan_90 = st.selectbox("現在の治療実施状況*", adj_opts, index=idx_adj)

with tab3:
    st.markdown('<div class="juog-header">3. 再発評価 (PFS判定)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("【尿路内再発】")
        st.session_state.pfs_intra_status = st.radio("尿路内再発の有無*", ["なし", "あり"], index=None, horizontal=True)
    with c2:
        st.subheader("【尿路外再発・進行】")
        st.session_state.pfs_recist_status = st.radio("尿路外・RECIST進行の有無*", ["なし", "あり"], index=None, horizontal=True)

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.status_alive_90 = st.radio("生存状況 (術後90日時点)*", ["生存", "死亡"], index=None, horizontal=True)
        if st.session_state.status_alive_90 == "生存":
            st.session_state.final_visit_date_90 = st.date_input("最終生存確認日*", value=st.session_state.final_visit_date_90)
    with c2:
        if st.session_state.status_alive_90 == "死亡":
            st.session_state.death_date_90 = st.date_input("死亡日*", value=st.session_state.death_date_90)

    st.divider()

    # --- 送信ロジック ---
    if st.button("🚀 90日目データを確定送信", type="primary", use_container_width=True):
        # バリデーション（省略）
        st.session_state.do_send = True

    if st.session_state.do_send:
        def f_val(v): return str(v) if v is not None else "N/A"
        rep = f"施設: {st.session_state.facility_name}\nID: {st.session_state.patient_id}\nLab: WBC {f_val(st.session_state.wbc_90)}, Cre {f_val(st.session_state.cre_90)}"
        if send_email(rep, st.session_state.patient_id, st.session_state.facility_name):
            st.success("正常に送信されました。")
            st.balloons()
        st.session_state.do_send = False
