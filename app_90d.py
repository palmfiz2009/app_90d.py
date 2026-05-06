import streamlit as st
import json
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# --- ページ設定 ---
st.set_page_config(page_title="JUOG UTUC_Consolidative 90-Day CRF", layout="wide")

# --- 便利関数：数値の整形（NA対応） ---
def fmt(val):
    return "NA" if val is None else str(val)

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
        margin-bottom: 80px !important; 
        font-weight: 800; 
        height: 40px;
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
    .lab-font { font-size: 13px !important; color: #475569 !important; font-weight: 500 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 定数・リスト定義 ---
FACILITY_LIST = ["選択してください", "愛知県がんセンター", "秋田大学", "愛媛大学", "大分大学", "大阪公立大学", "大阪大学", "大阪府済生会野江病院", "岡山大学", "香川大学", "鹿児島大学", "関西医科大学", "岐阜大学", "九州大学病院", "京都大学", "久留米大学", "神戸大学", "国立がん研究センター中央病院", "国立病院機構四国がんセンター", "札幌医科大学", "千葉大学", "筑波大学", "東京科学大学", "東京慈恵会医科大学", "東京慈恵会医科大学附属柏病院", "東北大学", "鳥取大学", "富山大学", "長崎大学病院", "名古屋大学", "奈良県立医科大学", "新潟大学大学院 医歯学総合研究科", "浜松医科大学", "原三信病院", "兵庫医科大学", "弘前大学", "北海道大学", "三重大学", "横浜市立大学", "琉球大学", "和歌山県立医科大学", "その他"]

SURGERY_LIST = ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "転移巣切除"]
DRUG_LIST = ["BCG注入療法", "抗がん剤注入療法", "プラチナ製剤併用療法（GC等）", "維持療法（アベルマブ等）", "EVP再開", "ペムブロリズマブ単剤", "ニボルマブ単剤", "放射線治療", "その他"]

HELP_CD = """【Clavien-Dindo分類 (術後90日評価)】
* Grade I：正常な術後経過からの逸脱で、薬物療法、外科的治療、内視鏡的治療、IVR治療を要さないもの。（制吐剤、解熱剤、鎮痛剤、利尿剤などは含めない）
* Grade II：制吐剤、解熱剤、鎮痛剤、利尿剤以外の薬物療法を要する。（輸血および中心静脈栄養を含む）
* Grade III：外科的、内視鏡的、または放射線学的介入を要する。
  * IIIa：全身麻酔を要さない治療
  * IIIb：全身麻酔下での治療
* Grade IV：ICU管理を要する、生命を脅かす合併症。
  * IVa：単一の臓器不全
  * IVb：多臓器不全
* Grade V：患者の死亡"""

HELP_CYTO = """【尿細胞診結果】
* Negative: 陰性（クラスI・II）
* AUC: 非定型細胞
* SHGUC: 高異型度癌疑い
* HGUC: 高異型度癌（クラスIV・V相当）
* LGUC: 低異型度腫瘍"""

# --- セッション状態初期化 ---
if 'init_90d_perfect_v4' not in st.session_state:
    st.session_state['init_90d_perfect_v4'] = True
    LAB_KEYS = ["wbc_90", "hb_90", "plt_90", "ast_90", "alt_90", "ldh_90", "alb_90", "cre_90", "egfr_90", "crp_90", "neutro_90", "lympho_90", "mono_90", "eosino_90", "baso_90"]
    defaults = {
        "is_locked": False,
        "facility_name": "選択してください", "patient_id": "", "reporter_email": "",
        "op_date_90": None, "vital_abnormality_90": None, "vital_detail_90": "",
        "cytology_90": "選択してください",
        "cd_grade_90": "選択してください", "cd_date_90": None, "cd_detail_90": "", 
        "has_ctcae_90": False, "ae_status": "", 
        "adj_plan_90": "選択してください", "adj_other_90": "", "adj_start_90": None, "adj_end_90": None, "adj_ongoing_90": False,
        "pfs_intra_status": None, "pfs_intra_date": None, "pfs_intra_site": [], "pfs_intra_site_other": "", 
        "pfs_intra_tx": [], "pfs_intra_tx_other": "", "pfs_intra_tx_status": None,
        "intra_op_date_90": None, "intra_tx_start_90": None, "intra_tx_end_90": None, "intra_tx_ongoing_90": False, "pfs_intra_path_90": "",
        "pfs_recist_status": None, "pfs_recist_date": None, "pfs_recist_site": [], "pfs_recist_site_other": "", 
        "pfs_recist_tx": "選択してください", "pfs_recist_tx_status": None,
        "pfs_recist_tx_detail": "", "extra_op_date_90": None, "extra_tx_start_90": None, "extra_tx_end_90": None, "extra_tx_ongoing_90": False,
        "status_alive_90": None, "final_visit_date_90": None, "death_cause_90": "選択してください", "death_date_90": None
    }
    for lab in LAB_KEYS: defaults[lab] = ""
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def get_idx(options, value):
    try: return options.index(value)
    except: return 0

def send_email(report_content, pid, facility, user_email=None):
    try:
        mail_user = st.secrets["email"]["user"]; mail_pass = st.secrets["email"]["pass"]
        to_addrs = ["urosec@kmu.ac.jp", "yoshida.tks@kmu.ac.jp"]
        if user_email and user_email not in to_addrs: to_addrs.append(user_email)
        msg = MIMEMultipart(); msg['From'] = mail_user; msg['To'] = ", ".join(to_addrs)
        msg['Subject'] = f"【JUOG 90D報告】（{facility} / ID: {pid}）"
        msg.attach(MIMEText(report_content, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465); server.login(mail_user, mail_pass); server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"メール送信エラー: {e}"); return False

# ロック状態の取得
L = st.session_state.get("is_locked", False)

st.title("JUOG UTUC_Consolidative 術後90日目 CRF")

# --- 1. 基本情報・評価対象期間 ---
st.markdown('<div class="juog-header">1. 基本情報・評価対象期間</div>', unsafe_allow_html=True)
col_h1, col_h2 = st.columns(2)
with col_h1:
    st.session_state.facility_name = st.selectbox("施設名*", FACILITY_LIST, index=get_idx(FACILITY_LIST, st.session_state.facility_name), disabled=L)
    st.session_state.patient_id = st.text_input("研究対象者識別コード*", value=st.session_state.patient_id, disabled=L)
with col_h2:
    st.session_state.reporter_email = st.text_input("報告者メールアドレス*", value=st.session_state.reporter_email, disabled=L)
    st.session_state.op_date_90 = st.date_input("手術日（非施行例は予定日）*", value=st.session_state.op_date_90 if st.session_state.op_date_90 is not None else date.today(), disabled=L)
    if st.session_state.op_date_90:
        min_d = st.session_state.op_date_90 + timedelta(days=30)
        max_d = st.session_state.op_date_90 + timedelta(days=90)
        st.info(f"📅 評価対象期間 (手術日から30日〜90日): {min_d.strftime('%Y/%m/%d')} 〜 {max_d.strftime('%Y/%m/%d')}")

tab1, tab2, tab3, tab4 = st.tabs(["🩺 身体所見・検査", "📋 安全性・術後補助療法", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">身体所見・検査データ</div>', unsafe_allow_html=True)
    c_top1, c_top2 = st.columns(2)
    with c_top1:
        st.session_state.vital_abnormality_90 = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=(0 if st.session_state.vital_abnormality_90=="異常なし" else 1 if st.session_state.vital_abnormality_90=="異常あり" else None), horizontal=True, disabled=L)
        if st.session_state.vital_abnormality_90 == "異常あり":
            st.session_state.vital_detail_90 = st.text_input("異常の詳細*", value=st.session_state.vital_detail_90, disabled=L)
    with c_top2:
        cyto_opts = ["選択してください", "Negative (クラスI・II)", "AUC (非定型細胞)", "SHGUC (高異型度癌疑い)", "HGUC (クラスIV・V相当)", "LGUC (低異型度腫瘍)", "判定不能", "未実施"]
        st.session_state.cytology_90 = st.selectbox("尿細胞診結果*", cyto_opts, index=get_idx(cyto_opts, st.session_state.cytology_90), help=HELP_CYTO, disabled=L)

    st.markdown("---")
    bc1, bc2 = st.columns(2)
    lab_h = "数値を入力。測定していない場合は NA と入力してください（空欄不可）"
    with bc1:
        st.session_state.wbc_90 = st.text_input("WBC (/μL)*", value=st.session_state.wbc_90, help=lab_h, disabled=L)
        st.session_state.hb_90 = st.text_input("Hb (g/dL)*", value=st.session_state.hb_90, help=lab_h, disabled=L)
        st.session_state.plt_90 = st.text_input("PLT (x10^4/μL)*", value=st.session_state.plt_90, help=lab_h, disabled=L)
        st.session_state.ast_90 = st.text_input("AST (U/L)*", value=st.session_state.ast_90, help=lab_h, disabled=L)
        st.session_state.alt_90 = st.text_input("ALT (U/L)*", value=st.session_state.alt_90, help=lab_h, disabled=L)
    with bc2:
        st.session_state.ldh_90 = st.text_input("LDH (U/L)*", value=st.session_state.ldh_90, help=lab_h, disabled=L)
        st.session_state.alb_90 = st.text_input("Alb (g/dL)*", value=st.session_state.alb_90, help=lab_h, disabled=L)
        st.session_state.cre_90 = st.text_input("Cre (mg/dL)*", value=st.session_state.cre_90, help=lab_h, disabled=L)
        st.session_state.egfr_90 = st.text_input("eGFR (mL/min)*", value=st.session_state.egfr_90, help=lab_h, disabled=L)
        st.session_state.crp_90 = st.text_input("CRP (mg/dL)*", value=st.session_state.crp_90, help=lab_h, disabled=L)

    st.markdown("<div class='lab-font'>白血球分画 (%)</div>", unsafe_allow_html=True)
    d1, d2, d3, d4, d5 = st.columns(5)
    st.session_state.neutro_90 = d1.text_input("Neutro*", value=st.session_state.neutro_90, help=lab_h, disabled=L)
    st.session_state.lympho_90 = d2.text_input("Lympho*", value=st.session_state.lympho_90, help=lab_h, disabled=L)
    st.session_state.mono_90 = d3.text_input("Mono*", value=st.session_state.mono_90, help=lab_h, disabled=L)
    st.session_state.eosino_90 = d4.text_input("Eosino*", value=st.session_state.eosino_90, help=lab_h, disabled=L)
    st.session_state.baso_90 = d5.text_input("Baso*", value=st.session_state.baso_90, help=lab_h, disabled=L)

with tab2:
    st.markdown('<div class="juog-header">2. 安全性評価および術後補助療法の状況</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cd_opts = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
        st.session_state.cd_grade_90 = st.selectbox("合併症 (Clavien-Dindo分類)*", cd_opts, index=get_idx(cd_opts, st.session_state.cd_grade_90), help=HELP_CD, disabled=L)
        if st.session_state.cd_grade_90 not in ["選択してください", "Grade 0"]:
            st.session_state.cd_date_90 = st.date_input("合併症の発現日*", value=st.session_state.cd_date_90 if st.session_state.cd_date_90 is not None else date.today(), disabled=L)
            st.session_state.cd_detail_90 = st.text_area("外科的合併症の詳細内容*", value=st.session_state.cd_detail_90, disabled=L)
        st.markdown("---")
        st.session_state.has_ctcae_90 = st.checkbox("薬剤関連等の有害事象（CTCAE準拠）を報告する", value=st.session_state.has_ctcae_90, disabled=L)
        if st.session_state.has_ctcae_90:
            st.session_state.ae_status = st.text_area("有害事象の詳細*", value=st.session_state.ae_status, placeholder="発現日、内容、重症度、処置、転帰などを記入", disabled=L)
            st.markdown("<div style='text-align: right;'><small>参照： <a href='https://jcog.jp/assets/CTCAEv6J_20260301_v28_0.pdf' target='_blank'>CTCAE v6.0 日本語訳 (JCOG版)</a></small></div>", unsafe_allow_html=True)
    with c2:
        adj_opts = ["選択してください", "無治療（経過観察）", "術前からのEVP継続投与", "術前からのEV単独継続（間欠療法等を含む）", "術前からのペムブロリズマブ単剤継続", "ニボルマブ単剤（術後補助療法）", "GC療法（術後補助療法）", "GCarbo療法（術後補助療法）", "放射線治療", "治験・その他薬物療法", "その他"]
        st.session_state.adj_plan_90 = st.selectbox("現在の治療実施状況（補助療法等）*", adj_opts, index=get_idx(adj_opts, st.session_state.adj_plan_90), disabled=L)
        if st.session_state.adj_plan_90 not in ["選択してください", "無治療（経過観察）"]:
            if st.session_state.adj_plan_90 in ["治験・その他薬物療法", "その他"]:
                st.session_state.adj_other_90 = st.text_input("治療の詳細*", value=st.session_state.adj_other_90, disabled=L)
            st.markdown("###### 治療日程")
            ax1, ax2 = st.columns(2)
            st.session_state.adj_start_90 = ax1.date_input(f"{st.session_state.adj_plan_90} 開始日*", value=st.session_state.adj_start_90 if st.session_state.adj_start_90 is not None else date.today(), disabled=L)
            st.session_state.adj_ongoing_90 = ax2.checkbox("現在も継続中", value=st.session_state.adj_ongoing_90, disabled=L)
            if not st.session_state.adj_ongoing_90:
                st.session_state.adj_end_90 = ax2.date_input(f"{st.session_state.adj_plan_90} 終了日*", value=st.session_state.adj_end_90 if st.session_state.adj_end_90 is not None else date.today(), disabled=L)
            else: st.session_state.adj_end_90 = None

with tab3:
    st.markdown('<div class="juog-header">3. 再発評価 (Progressive Disease)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**【尿路内再発】**")
        st.session_state.pfs_intra_status = st.radio("尿路内再発の有無*", ["なし", "あり"], index=(0 if st.session_state.pfs_intra_status=="なし" else 1 if st.session_state.pfs_intra_status=="あり" else None), horizontal=True, disabled=L)
        if st.session_state.pfs_intra_status == "あり":
            st.session_state.pfs_intra_date = st.date_input("診断日（組織・画像等）*", value=st.session_state.pfs_intra_date if st.session_state.pfs_intra_date is not None else date.today(), disabled=L)
            st.session_state.pfs_intra_site = st.multiselect("再発部位*", ["膀胱", "対側腎盂", "対側尿管", "同側残存尿管", "その他"], default=st.session_state.pfs_intra_site, disabled=L)
            if "その他" in st.session_state.pfs_intra_site: st.session_state.pfs_intra_site_other = st.text_input("部位詳細*", value=st.session_state.pfs_intra_site_other, disabled=L)
            st.session_state.pfs_intra_tx = st.multiselect("実施した治療*", ["経過観察", "TURBT", "BCG注入療法", "抗がん剤注入療法", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "その他"], default=st.session_state.pfs_intra_tx, disabled=L)
            if st.session_state.pfs_intra_tx and "経過観察" not in st.session_state.pfs_intra_tx:
                st.session_state.pfs_intra_tx_status = st.radio("尿路内再発治療の状況*", ["実施済み・継続中", "今後の予定"], index=get_idx(["実施済み・継続中", "今後の予定"], st.session_state.pfs_intra_tx_status), horizontal=True, disabled=L)
                if st.session_state.pfs_intra_tx_status == "実施済み・継続中":
                    if any(x in SURGERY_LIST for x in st.session_state.pfs_intra_tx):
                        st.session_state.intra_op_date_90 = st.date_input("手術実施日*", value=st.session_state.intra_op_date_90 if st.session_state.intra_op_date_90 is not None else date.today(), disabled=L)
                        st.session_state.pfs_intra_path_90 = st.text_area("組織型、Grade等*", value=st.session_state.pfs_intra_path_90, disabled=L)
                    if any(x in DRUG_LIST or x in ["TURBT", "BCG注入療法", "抗がん剤注入療法"] for x in st.session_state.pfs_intra_tx):
                        ix1, ix2 = st.columns(2)
                        st.session_state.intra_tx_start_90 = ix1.date_input("治療開始日*", value=st.session_state.intra_tx_start_90 if st.session_state.intra_tx_start_90 is not None else date.today(), disabled=L)
                        st.session_state.intra_tx_ongoing_90 = ix2.checkbox("尿路内治療 継続中", value=st.session_state.intra_tx_ongoing_90, disabled=L)
                        if not st.session_state.intra_tx_ongoing_90: st.session_state.intra_tx_end_90 = ix2.date_input("治療終了日*", value=st.session_state.intra_tx_end_90 if st.session_state.intra_tx_end_90 is not None else date.today(), disabled=L)
            if "その他" in st.session_state.pfs_intra_tx: st.session_state.pfs_intra_tx_other = st.text_input("尿路内治療「その他」詳細*", value=st.session_state.pfs_intra_tx_other, disabled=L)

    with c2:
        st.markdown("**【尿路外再発】**")
        st.session_state.pfs_recist_status = st.radio("尿路外再発の有無*", ["なし", "あり"], index=(0 if st.session_state.pfs_recist_status=="なし" else 1 if st.session_state.pfs_recist_status=="あり" else None), horizontal=True, disabled=L)
        if st.session_state.pfs_recist_status == "あり":
            st.session_state.pfs_recist_date = st.date_input("診断日（画像・組織等）*", value=st.session_state.pfs_recist_date if st.session_state.pfs_recist_date is not None else date.today(), disabled=L)
            st.session_state.pfs_recist_site = st.multiselect("再発部位*", ["肺", "リンパ節", "肝", "骨", "手術局所", "その他"], default=st.session_state.pfs_recist_site, disabled=L)
            if "その他" in st.session_state.pfs_recist_site: st.session_state.pfs_recist_site_other = st.text_input("部位詳細(外)*", value=st.session_state.pfs_recist_site_other, disabled=L)
            st.session_state.pfs_recist_tx = st.selectbox("実施治療*", ["選択してください", "プラチナ製剤併用療法（GC等）", "維持療法（アベルマブ等）", "EVP再開", "ペムブロリズマブ単剤", "ニボルマブ単剤", "転移巣切除", "放射線治療", "その他"], index=get_idx(["選択してください", "プラチナ製剤併用療法（GC等）", "維持療法（アベルマブ等）", "EVP再開", "ペムブロリズマブ単剤", "ニボルマブ単剤", "転移巣切除", "放射線治療", "その他"], st.session_state.pfs_recist_tx), disabled=L)
            if st.session_state.pfs_recist_tx != "選択してください":
                st.session_state.pfs_recist_tx_status = st.radio("尿路外治療の状況*", ["実施済み・継続中", "今後の予定"], index=get_idx(["実施済み・継続中", "今後の予定"], st.session_state.pfs_recist_tx_status), horizontal=True, disabled=L)
                if st.session_state.pfs_recist_tx_status == "実施済み・継続中":
                    if st.session_state.pfs_recist_tx == "転移巣切除":
                        st.session_state.extra_op_date_90 = st.date_input("外手術実施日*", value=st.session_state.extra_op_date_90 if st.session_state.extra_op_date_90 is not None else date.today(), disabled=L)
                    if st.session_state.pfs_recist_tx in DRUG_LIST:
                        ex1, ex2 = st.columns(2)
                        st.session_state.extra_tx_start_90 = ex1.date_input("外治療開始日*", value=st.session_state.extra_tx_start_90 if st.session_state.extra_tx_start_90 is not None else date.today(), disabled=L)
                        st.session_state.extra_tx_ongoing_90 = ex2.checkbox("尿路外治療 継続中", value=st.session_state.extra_tx_ongoing_90, disabled=L)
                        if not st.session_state.extra_tx_ongoing_90: st.session_state.extra_tx_end_90 = ex2.date_input("外治療終了日*", value=st.session_state.extra_tx_end_90 if st.session_state.extra_tx_end_90 is not None else date.today(), disabled=L)
            if st.session_state.pfs_recist_tx == "その他": st.session_state.pfs_recist_tx_detail = st.text_input("外治療「その他」詳細*", value=st.session_state.pfs_recist_tx_detail, disabled=L)

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.status_alive_90 = st.radio("生存状況*", ["生存", "死亡"], index=(0 if st.session_state.status_alive_90=="生存" else 1 if st.session_state.status_alive_90=="死亡" else None), horizontal=True, disabled=L)
        if st.session_state.status_alive_90 == "生存":
            st.session_state.final_visit_date_90 = st.date_input("最終生存確認日*", value=st.session_state.final_visit_date_90 if st.session_state.final_visit_date_90 is not None else date.today(), disabled=L)
            # 生存時は死亡情報をリセット
            st.session_state.death_date_90 = None; st.session_state.death_cause_90 = "選択してください"
    with c2:
        if st.session_state.status_alive_90 == "死亡":
            st.session_state.death_date_90 = st.date_input("死亡日*", value=st.session_state.death_date_90 if st.session_state.death_date_90 is not None else date.today(), disabled=L)
            st.session_state.death_cause_90 = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], index=get_idx(["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], st.session_state.death_cause_90), disabled=L)
    st.divider()
    submitted = st.button("🚀 90日目データを確定送信", type="primary", use_container_width=True, disabled=L)
    if submitted:
        err = []; d = st.session_state; today = date.today()
        # ロジック・必須チェック
        if d.facility_name == "選択してください": err.append("・施設名")
        if not d.patient_id: err.append("・研究対象者識別コード")
        if not d.reporter_email or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", d.reporter_email): err.append("・報告者メールアドレス不正")
        if not d.op_date_90: err.append("・手術日")
        if d.vital_abnormality_90 is None: err.append("・身体所見の有無")
        if d.cytology_90 == "選択してください": err.append("・尿細胞診結果")
        if d.status_alive_90 == "生存" and d.death_date_90: err.append("・[論理エラー] 生存症例に死亡日が入力されています")
        
        # 採血パース
        lab_labels = {"wbc_90": "WBC", "hb_90": "Hb", "plt_90": "PLT", "ast_90": "AST", "alt_90": "ALT", "ldh_90": "LDH", "alb_90": "Alb", "cre_90": "Cre", "egfr_90": "eGFR", "crp_90": "CRP", "neutro_90": "Neutro", "lympho_90": "Lympho", "mono_90": "Mono", "eosino_90": "Eosino", "baso_90": "Baso"}
        parsed_labs = {}; missing_labs_warning = []; invalid_labs = []; missing_input_flag = False
        for k, label in lab_labels.items():
            val_s = str(d.get(k, "")).strip().upper()
            if val_s == "": missing_input_flag = True
            elif val_s in ["NA", "N/A"]: missing_labs_warning.append(label); parsed_labs[k] = None
            else:
                try:
                    num = float(val_s)
                    if num <= 0: invalid_labs.append(label)
                    parsed_labs[k] = num
                except: err.append(f"・検査値: {label} は数値またはNAで入力してください")
        if missing_input_flag: err.append("・採血検査に未入力項目があります（NAまたは数値必須）")
        if invalid_labs: err.append(f"・[数値エラー] 0以下のあり得ない数値: {', '.join(invalid_labs)}")

        # 日程・論理チェック
        if d.op_date_90:
            if (today - d.op_date_90).days < 75: err.append("・[期間不備] 手術から75日未満の報告は不可です")
            evs = {"cd_date_90": "合併症", "pfs_intra_date": "内再発日", "intra_op_date_90": "再発手術", "intra_tx_start_90": "内治療開始", "pfs_recist_date": "外再発日", "extra_op_date_90": "外再発手術", "extra_tx_start_90": "外治療開始", "final_visit_date_90": "最終生存確認日", "death_date_90": "死亡日"}
            for k, l in evs.items():
                val = d.get(k)
                if val:
                    diff = (val - d.op_date_90).days
                    if diff < 0: err.append(f"・[日付矛盾] {l}が手術日より前です")
                    if diff < 30 or diff > 104: err.append(f"・[日付エラー] {l}は手術後30日〜90日（+14日猶予）以内の日付を入力してください（それ以降は次回CRF範囲です）")
                    if val > today: err.append(f"・[日付エラー] {l}に未来日は入力不可です")

        if err: st.error("修正が必要な項目：\n" + "\n".join(err))
        else:
            rep = f"【JUOG 90D報告】\n施設: {d.facility_name} / ID: {d.patient_id}\n報告者: {d.reporter_email}\n手術日: {d.op_date_90}\n\n"
            rep += "--- 1. 採血データ ---\n"
            for k, label in lab_labels.items(): rep += f"{label}: {fmt(parsed_labs.get(k))}\n"
            rep += f"\n--- 2. 安全性 ---\nCD分類: {d.cd_grade_90} ({d.cd_date_90})\n補助療法: {d.adj_plan_90}\n"
            rep += f"\n--- 3. PFS ---\n尿路内: {d.pfs_intra_status} (状況: {d.pfs_intra_tx_status})\n尿路外: {d.pfs_recist_status} (状況: {d.pfs_recist_tx_status})\n"
            rep += f"\n--- 4. OS ---\n状況: {d.status_alive_90} (確認日: {d.final_visit_date_90 if d.status_alive_90=='生存' else d.death_date_90})\n"
            if send_email(rep, d.patient_id, d.facility_name, d.reporter_email):
                st.session_state["is_locked"] = True
                st.success("確定送信されました。内容をロックしました。"); st.balloons()
                if missing_labs_warning: st.warning(f"⚠️ 以下の欠損項目をNAとして受理しました: {', '.join(missing_labs_warning)}")
                st.rerun()
