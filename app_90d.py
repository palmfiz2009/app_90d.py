import streamlit as st
from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 設定 ---
DEBUG_MODE = False  # Trueにするとメール送信をスキップして内容表示のみ

st.set_page_config(page_title="JUOG UTUC_Consolidative 90-Day CRF", layout="wide")

# --- CSS (レイアウト維持) ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .block-container { max-width: 1100px !important; padding-top: 1.5rem !important; margin: auto !important; }
    h1 { font-size: 26px !important; color: #0F172A; text-align: center; font-weight: 800; }
    .juog-header { background-color: #1E3A8A; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; }
    label { font-weight: 600 !important; color: #334155 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 施設リスト ---
FACILITY_LIST = ["選択してください", "愛知県がんセンター", "秋田大学", "愛媛大学", "大分大学", "大阪公立大学", "大阪大学", "大阪府済生会野江病院", "岡山大学", "香川大学", "鹿児島大学", "関西医科大学", "岐阜大学", "九州大学病院", "京都大学", "久留米大学", "神戸大学", "国立がん研究センター中央病院", "国立病院機構四国がんセンター", "札幌医科大学", "千葉大学", "筑波大学", "東京科学大学", "東京慈恵会医科大学", "東京慈恵会医科大学附属柏病院", "東北大学", "鳥取大学", "富山大学", "長崎大学病院", "名古屋大学", "奈良県立医科大学", "新潟大学大学院 医歯学総合研究科", "浜松医科大学", "原三信病院", "兵庫医科大学", "弘前大学", "北海道大学", "三重大学", "横浜市立大学", "琉球大学", "和歌山県立医科大学", "その他"]

HELP_CD = """
**Clavien-Dindo 分類 (術後90日評価)**
- Grade I：正常経過からの逸脱、薬物・外科・内視鏡・IVR不要。
- Grade II：薬物療法、輸血、TPNを要する。
- Grade III：外科・内視鏡・IVRを要する(IIIa:局麻, IIIb:全麻)。
- Grade IV：ICU管理。単一臓器(IVa)または多臓器不全(IVb)。
- Grade V：死亡。
"""

# --- セッション初期化 ---
if 'init_90d_done' not in st.session_state:
    st.session_state['init_90d_done'] = True
    defaults = {
        "fac_name": "選択してください", "p_id": "", "op_d": None, "eval_d": None,
        "v_abn": None, "v_det": "", "cyto": "選択してください",
        "wbc": 0.0, "hb": 0.0, "plt": 0.0, "ast": 0.0, "alt": 0.0, "ldh": 0.0, "alb": 0.0, "cre": 0.0, "egfr": 0.0, "crp": 0.0,
        "neu": 0.0, "lym": 0.0, "mon": 0.0, "eos": 0.0, "bas": 0.0,
        "cd_g": "選択してください", "cd_d": "", "adj_p": "選択してください", "adj_o": "",
        "pfs_i_s": None, "pfs_i_d": None, "pfs_i_tx": "未選択", "pfs_i_det": "",
        "pfs_r_s": None, "pfs_r_d": None, "pfs_r_site": [], "pfs_r_tx": "未選択", "pfs_r_det": "",
        "is_alive": None, "last_v": None, "d_cause": "選択してください", "d_date": None
    }
    for k, v in defaults.items(): st.session_state[k] = v

st.title("JUOG UTUC_Consolidative 術後90日目 CRF")

# --- 共通ヘッダー ---
col_h1, col_h2 = st.columns(2)
with col_h1: st.session_state.fac_name = st.selectbox("施設名*", FACILITY_LIST)
with col_h2: st.session_state.p_id = st.text_input("研究対象者識別コード*", value=st.session_state.p_id)

tab1, tab2, tab3, tab4 = st.tabs(["🩺 診察・検査", "📋 安全性・治療状況", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">1. 身体所見・検査 (術後90日±14日)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.op_d = st.date_input("手術実施日*", value=st.session_state.op_d)
        if st.session_state.op_d:
            target = st.session_state.op_d + timedelta(days=90)
            st.info(f"90日目目安: {target} (許容: {target-timedelta(days=14)} ～ {target+timedelta(days=14)})")
        st.session_state.eval_d = st.date_input("評価実施日(来院日)*", value=st.session_state.eval_d)
        st.session_state.v_abn = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=None, horizontal=True)
        if st.session_state.v_abn == "異常あり": st.session_state.v_det = st.text_input("異常の詳細*")
    with c2:
        cyto_opts = ["選択してください", "NILM (Class I・II)", "AUC (Class III相当)", "SHGUC (Class IV相当)", "HGUC (Class V相当)", "LGUC", "判定不能", "未実施"]
        st.session_state.cyto = st.selectbox("尿細胞診結果*", cyto_opts)

    st.markdown("---")
    bc1, bc2 = st.columns(2)
    with bc1:
        st.session_state.wbc = st.number_input("WBC (/μL)*", value=0.0, step=1.0)
        st.session_state.hb = st.number_input("Hb (g/dL)*", value=0.0, step=0.1)
        st.session_state.plt = st.number_input("PLT (x10^4/μL)*", value=0.0, step=1.0)
        st.session_state.ast = st.number_input("AST (U/L)*", value=0.0, step=1.0)
        st.session_state.alt = st.number_input("ALT (U/L)*", value=0.0, step=1.0)
    with bc2:
        st.session_state.ldh = st.number_input("LDH (U/L)*", value=0.0, step=1.0)
        st.session_state.alb = st.number_input("Alb (g/dL)*", value=0.0, step=0.1)
        st.session_state.cre = st.number_input("Cre (mg/dL)*", value=0.0, step=0.01)
        st.session_state.egfr = st.number_input("eGFR (mL/min/1.73m²)*", value=0.0, step=0.1)
        st.session_state.crp = st.number_input("CRP (mg/dL)*", value=0.0, step=0.01)

    st.markdown("### 白血球分画 (%)")
    d1, d2, d3, d4, d5 = st.columns(5)
    with d1: st.session_state.neu = st.number_input("Neutro*", value=0.0, step=0.1)
    with d2: st.session_state.lym = st.number_input("Lympho*", value=0.0, step=0.1)
    with d3: st.session_state.mon = st.number_input("Mono*", value=0.0, step=0.1)
    with d4: st.session_state.eos = st.number_input("Eosino*", value=0.0, step=0.1)
    with d5: st.session_state.bas = st.number_input("Baso*", value=0.0, step=0.1)
    
    diff_total = st.session_state.neu + st.session_state.lym + st.session_state.mon + st.session_state.eos + st.session_state.bas
    if diff_total > 0 and not (98.0 <= diff_total <= 102.0):
        st.error(f"⚠️ 分画の合計が {diff_total:.1f}% です。100%付近になるよう確認してください。")

with tab2:
    st.markdown('<div class="juog-header">2. 安全性評価および術後補助療法の状況</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cd_opts = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
        st.session_state.cd_g = st.selectbox("術後90日までの合併症 (CD分類)*", cd_opts, help=HELP_CD)
        if st.session_state.cd_g not in ["選択してください", "Grade 0"]: st.session_state.cd_d = st.text_area("合併症の詳細*")
    with c2:
        adj_opts = ["選択してください", "無治療", "後治療計画中", "EVP継続", "ペムブロ維持", "ニボ単剤", "GC療法", "GCarbo療法", "その他"]
        st.session_state.adj_p = st.selectbox("現在の治療実施状況*", adj_opts)

with tab3:
    st.markdown('<div class="juog-header">3. 再発評価 (PFS判定)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.pfs_i_s = st.radio("尿路内再発の有無 (膀胱・対側上部尿路)*", ["なし", "あり"], index=None, horizontal=True)
        if st.session_state.pfs_i_s == "あり":
            st.session_state.pfs_i_d = st.date_input("尿路内再発確定日*", value=st.session_state.pfs_i_d)
            st.session_state.pfs_i_site = st.multiselect("部位*", ["膀胱内", "対側尿管", "対側腎盂", "尿道"])
            st.session_state.pfs_i_tx = st.selectbox("治療内容*", ["未選択", "TURBT", "内視鏡焼灼", "注入療法", "その他"])
    with c2:
        st.session_state.pfs_r_s = st.radio("尿路外・RECIST進行の有無*", ["なし", "あり"], index=None, horizontal=True)
        if st.session_state.pfs_r_s == "あり":
            st.session_state.pfs_r_d = st.date_input("再発・進行確定日(PFSイベント日)*", value=st.session_state.pfs_r_d)
            st.session_state.pfs_r_site = st.multiselect("進行部位*", ["手術局所", "領域LN", "遠隔LN", "肺", "肝", "骨", "その他"])
            st.session_state.pfs_r_tx = st.selectbox("治療内容*", ["未選択", "EVP再開", "薬剤変更", "転移巣切除", "放射線", "集学的治療", "その他"])

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.is_alive = st.radio("生存状況 (術後90日時点)*", ["生存", "死亡"], index=None, horizontal=True)
        if st.session_state.is_alive == "生存": st.session_state.last_v = st.date_input("最終生存確認日*", value=st.session_state.last_v)
    with c2:
        if st.session_state.is_alive == "死亡":
            st.session_state.d_date = st.date_input("死亡日*", value=st.session_state.d_date)
            st.session_state.d_cause = st.selectbox("死因*", ["選択してください", "癌死", "治療関連死", "他病死", "不明"])

# --- バリデーション関数 ---
def validate():
    e = []
    d = st.session_state
    if d.fac_name == "選択してください": e.append("施設名が未選択です。")
    if not d.p_id: e.append("識別コードが未入力です。")
    if not d.op_d or not d.eval_d: e.append("手術日または評価日が未入力です。")
    if d.op_d and d.eval_d and d.eval_d < d.op_d: e.append("評価日が手術日より前になっています。")
    if d.cyto == "選択してください": e.append("尿細胞診の結果を選択してください。")
    if d.wbc == 0: e.append("WBCが0または未入力です。")
    if d.cd_g == "選択してください": e.append("CD分類を選択してください。")
    if d.is_alive == "死亡":
        if d.d_cause == "選択してください": e.append("死因を選択してください。")
        if d.cd_g != "Grade V": e.append("死亡の場合、CD分類はGrade Vである必要があります。")
    if d.pfs_r_s == "あり":
        if not d.pfs_r_d: e.append("進行確定日を入力してください。")
        if d.pfs_r_d and d.op_d and d.pfs_r_d < d.op_d: e.append("再発日が手術日より前になっています。")
    return e

# --- 送信セクション ---
st.divider()
if st.button("🚀 データを確定送信", type="primary", use_container_width=True):
    errors = validate()
    if errors:
        for err in errors: st.error(err)
    else:
        rep = f"JUOG 90D Report: ID {st.session_state.p_id}\nEval Date: {st.session_state.eval_d}\nPFS(R): {st.session_state.pfs_r_s}\nAlive: {st.session_state.is_alive}"
        if DEBUG_MODE:
            st.warning("DEBUG MODE: 以下の内容を送信したと仮定します。")
            st.code(rep)
        else:
            # 実際のメール送信ロジック（secretsが必要）
            st.success("事務局へ送信されました。")
