import streamlit as st
import json
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

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
    </style>
    """, unsafe_allow_html=True)

# --- 定数・リスト定義 ---
FACILITY_LIST = ["選択してください", "愛知県がんセンター", "秋田大学", "愛媛大学", "大分大学", "大阪公立大学", "大阪大学", "大阪府済生会野江病院", "岡山大学", "香川大学", "鹿児島大学", "関西医科大学", "岐阜大学", "九州大学病院", "京都大学", "久留米大学", "神戸大学", "国立がん研究センター中央病院", "国立病院機構四国がんセンター", "札幌医科大学", "千葉大学", "筑波大学", "東京科学大学", "東京慈恵会医科大学", "東京慈恵会医科大学附属柏病院", "東北大学", "鳥取大学", "富山大学", "長崎大学病院", "名古屋大学", "奈良県立医科大学", "新潟大学大学院 医歯学総合研究科", "浜松医科大学", "原三信病院", "兵庫医科大学", "弘前大学", "北海道大学", "三重大学", "横浜市立大学", "琉球大学", "和歌山県立医科大学", "その他"]

SURGERY_LIST = ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "転移巣切除", "手術（転移巣切除）"]
DRUG_LIST = ["BCG注入療法", "抗がん剤注入療法", "プラチナ製剤併用療法（GC療法）", "プラチナ製剤併用療法（GCarbo療法）", "維持療法（アベルマブ等）", "EVP継続投与", "ペムブロ維持", "ニボルマブ単剤（術後補助療法として）", "ニボ単剤", "GC療法", "GCarbo療法", "放射線治療", "ペムブロリズマブ単剤", "ニボルマブ単剤", "サシツズマブ ゴビテカン（SG）", "FGFR阻害薬", "治験（HER2標的ADC、TROP2標的ADC、その他）"]

HELP_CD = "Clavien-Dindo 分類 (術後90日評価) 原則：\n- Grade I：薬物・外科介入不要\n- Grade II：薬物療法(輸血・TPN含)\n- Grade IIIa/b: 外科的介入\n- Grade IVa/b: 生命を脅かす合併症\n- Grade V: 死亡"

HELP_CYTO = "【尿細胞診結果】\n- Negative: クラスI・II\n- AUC: 非定型細胞\n- SHGUC: 高異型度癌疑い\n- HGUC: クラスIV・V相当\n- LGUC: 低異型度腫瘍"

# --- セッション状態初期化 ---
if 'init_90d_v32' not in st.session_state:
    st.session_state['init_90d_v32'] = True
    LAB_KEYS = ["wbc_90", "hb_90", "plt_90", "ast_90", "alt_90", "ldh_90", "alb_90", "cre_90", "egfr_90", "crp_90", "neutro_90", "lympho_90", "mono_90", "eosino_90", "baso_90"]
    defaults = {
        "facility_name": "選択してください", "patient_id": "", "reporter_email": "",
        "op_date_90": None, "eval_date_90": None, "vital_abnormality_90": None, "vital_detail_90": "",
        "cytology_90": "選択してください",
        "cd_grade_90": "選択してください", "cd_detail_90": "",
        "adj_plan_90": "選択してください", "adj_other_90": "", "adj_start_90": None, "adj_end_90": None, "adj_ongoing_90": False, "adj_op_date_90": None,
        "pfs_intra_status": None, "pfs_intra_date": None, "pfs_intra_site": [], "pfs_intra_site_other": "", "pfs_intra_tx": [], "pfs_intra_tx_other": "", "intra_op_date_90": None, "intra_tx_start_90": None, "intra_tx_end_90": None, "intra_tx_ongoing_90": False, "pfs_intra_path_90": "",
        "pfs_recist_status": None, "pfs_recist_date": None, "pfs_recist_site": [], "pfs_recist_site_other": "", "pfs_recist_tx": "選択してください", "pfs_recist_tx_detail": "", "extra_op_date_90": None, "extra_tx_start_90": None, "extra_tx_end_90": None, "extra_tx_ongoing_90": False,
        "status_alive_90": None, "final_visit_date_90": None, "death_cause_90": "選択してください", "death_date_90": None,
        "needs_confirm": False, "do_send": False
    }
    for lab in LAB_KEYS: defaults[lab] = None
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def get_idx(options, value):
    try: return options.index(value)
    except: return 0

def send_email(report_content, pid, facility, user_email=None):
    try:
        mail_user = st.secrets["email"]["user"]; mail_pass = st.secrets["email"]["pass"]
        to_addrs = ["urosec@kmu.ac.jp", "yoshida.tks@kmu.ac.jp"]
        if user_email: to_addrs.append(user_email)
        msg = MIMEMultipart(); msg['From'] = mail_user; msg['To'] = ", ".join(to_addrs)
        msg['Subject'] = f"【JUOG 90D報告】（{facility} / ID: {pid}）"
        msg.attach(MIMEText(report_content, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465); server.login(mail_user, mail_pass); server.send_message(msg); server.quit()
        return True
    except: return False

st.title("JUOG UTUC_Consolidative 術後90日目 CRF")

# --- 施設・ID情報 ---
col_h1, col_h2 = st.columns(2)
with col_h1:
    st.session_state.facility_name = st.selectbox("施設名*", FACILITY_LIST, index=get_idx(FACILITY_LIST, st.session_state.facility_name))
    st.session_state.reporter_email = st.text_input("報告者メールアドレス*", value=st.session_state.reporter_email)
with col_h2:
    st.session_state.patient_id = st.text_input("研究対象者識別コード*", value=st.session_state.patient_id)

tab1, tab2, tab3, tab4 = st.tabs(["🩺 診察・検査", "📋 安全性・治療状況", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">1. 身体所見・検査 (術後90日±14日)</div>', unsafe_allow_html=True)
    c_top1, c_top2 = st.columns(2)
    with c_top1:
        st.session_state.op_date_90 = st.date_input("手術実施日*", value=st.session_state.op_date_90)
        st.session_state.eval_date_90 = st.date_input("評価実施日(来院日)*", value=st.session_state.eval_date_90)
        st.session_state.vital_abnormality_90 = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=None, horizontal=True)
        if st.session_state.vital_abnormality_90 == "異常あり": st.session_state.vital_detail_90 = st.text_input("異常の詳細*")
    with c_top2:
        cyto_opts = ["選択してください", "Negative (クラスI・II)", "AUC (クラスIII相当)", "SHGUC (クラスIV相当)", "HGUC (クラスV相当)", "LGUC", "判定不能", "未実施"]
        st.session_state.cytology_90 = st.selectbox("尿細胞診結果*", cyto_opts, index=get_idx(cyto_opts, st.session_state.cytology_90), help=HELP_CYTO)

    st.markdown("---")
    bc1, bc2 = st.columns(2)
    with bc1:
        st.session_state.wbc_90 = st.number_input("WBC (/μL)*", value=st.session_state.wbc_90)
        st.session_state.hb_90 = st.number_input("Hb (g/dL)*", value=st.session_state.hb_90)
        st.session_state.plt_90 = st.number_input("PLT (x10^4/μL)*", value=st.session_state.plt_90)
        st.session_state.ast_90 = st.number_input("AST (U/L)*", value=st.session_state.ast_90)
        st.session_state.alt_90 = st.number_input("ALT (U/L)*", value=st.session_state.alt_90)
    with bc2:
        st.session_state.ldh_90 = st.number_input("LDH (U/L)*", value=st.session_state.ldh_90)
        st.session_state.alb_90 = st.number_input("Alb (g/dL)*", value=st.session_state.alb_90)
        st.session_state.cre_90 = st.number_input("Cre (mg/dL)*", value=st.session_state.cre_90)
        st.session_state.egfr_90 = st.number_input("eGFR (mL/min)*", value=st.session_state.egfr_90)
        st.session_state.crp_90 = st.number_input("CRP (mg/dL)*", value=st.session_state.crp_90)

    st.markdown("**白血球分画 (%)**")
    d1, d2, d3, d4, d5 = st.columns(5)
    st.session_state.neutro_90 = d1.number_input("Neutro*", value=st.session_state.neutro_90)
    st.session_state.lympho_90 = d2.number_input("Lympho*", value=st.session_state.lympho_90)
    st.session_state.mono_90 = d3.number_input("Mono*", value=st.session_state.mono_90)
    st.session_state.eosino_90 = d4.number_input("Eosino*", value=st.session_state.eosino_90)
    st.session_state.baso_90 = d5.number_input("Baso*", value=st.session_state.baso_90)

with tab2:
    st.markdown('<div class="juog-header">2. 安全性評価および術後補助療法の状況</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cd_opts = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
        st.session_state.cd_grade_90 = st.selectbox("合併症 (CD分類)*", cd_opts, index=get_idx(cd_opts, st.session_state.cd_grade_90), help=HELP_CD)
        if st.session_state.cd_grade_90 not in ["選択してください", "Grade 0"]:
            st.session_state.cd_detail_90 = st.text_area("合併症の詳細内容*", value=st.session_state.cd_detail_90)
    with c2:
        # 指示通り「ニボルマブ単剤（術後補助療法として）」を追加
        adj_opts = ["選択してください", "無治療（経過観察）", "後治療を計画中", "EVP継続投与", "ペムブロ維持", "ニボルマブ単剤（術後補助療法として）", "GC療法", "GCarbo療法", "転移巣切除", "放射線治療", "その他"]
        st.session_state.adj_plan_90 = st.selectbox("現在の治療実施状況*", adj_opts, index=get_idx(adj_opts, st.session_state.adj_plan_90))
        
        # 補助療法の日程入力ロジック（フォローアップと共通）
        if st.session_state.adj_plan_90 == "転移巣切除":
            st.session_state.adj_op_date_90 = st.date_input(f"{st.session_state.adj_plan_90} 実施日*", value=st.session_state.adj_op_date_90, key="adj_op")
        
        if st.session_state.adj_plan_90 in DRUG_LIST or st.session_state.adj_plan_90 == "放射線治療":
            ax1, ax2 = st.columns(2)
            st.session_state.adj_start_90 = ax1.date_input(f"{st.session_state.adj_plan_90} 開始日*", value=st.session_state.adj_start_90, key="adj_start")
            st.session_state.adj_ongoing_90 = ax2.checkbox("継続中", value=st.session_state.adj_ongoing_90, key="adj_ongoing")
            if not st.session_state.adj_ongoing_90:
                st.session_state.adj_end_90 = ax2.date_input(f"{st.session_state.adj_plan_90} 終了日*", value=st.session_state.adj_end_90, key="adj_end")

        if st.session_state.adj_plan_90 == "その他":
            st.session_state.adj_other_90 = st.text_area("その他の詳細*", value=st.session_state.adj_other_90)

with tab3:
    st.markdown('<div class="juog-header">3. 再発評価 (PFS判定)</div>', unsafe_allow_html=True)
    # フォローアップCRFの形式に統一
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**【尿路内再発】**")
        st.session_state.pfs_intra_status = st.radio("尿路内再発の有無*", ["なし", "あり"], index=(0 if st.session_state.pfs_intra_status=="なし" else 1 if st.session_state.pfs_intra_status=="あり" else None), horizontal=True, key="r_intra_90")
        if st.session_state.pfs_intra_status == "あり":
            st.session_state.pfs_intra_date = st.date_input("診断日（組織・画像・膀胱鏡）*", value=st.session_state.pfs_intra_date, key="d_intra_90")
            st.session_state.pfs_intra_site = st.multiselect("再発部位*", ["膀胱", "対側腎盂", "対側尿管", "その他"], default=st.session_state.pfs_intra_site)
            
            intra_tx_opts = ["経過観察", "TURBT", "BCG注入療法", "抗がん剤注入療法", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "その他"]
            st.session_state.pfs_intra_tx = st.multiselect("実施した治療*", intra_tx_opts, default=st.session_state.pfs_intra_tx)
            
            if any(x in st.session_state.pfs_intra_tx for x in SURGERY_LIST):
                st.session_state.intra_op_date_90 = st.date_input("手術・処置実施日*", value=st.session_state.intra_op_date_90, key="i_op_90")
                st.session_state.pfs_intra_path_90 = st.text_area("組織型、Grade、pTNM分類 等*", value=st.session_state.pfs_intra_path_90, key="i_path_90")
            if any(x in st.session_state.pfs_intra_tx for x in ["BCG注入療法", "抗がん剤注入療法"]):
                ix1, ix2 = st.columns(2)
                st.session_state.intra_tx_start_90 = ix1.date_input("治療開始日*", value=st.session_state.intra_tx_start_90, key="i_start_90")
                st.session_state.intra_tx_ongoing_90 = ix2.checkbox("継続中", value=st.session_state.intra_tx_ongoing_90, key="i_ongoing_90")

    with c2:
        st.markdown("**【尿路外再発】**")
        st.session_state.pfs_recist_status = st.radio("尿路外再発の有無*", ["なし", "あり"], index=(0 if st.session_state.pfs_recist_status=="なし" else 1 if st.session_state.pfs_recist_status=="あり" else None), horizontal=True, key="r_extra_90")
        if st.session_state.pfs_recist_status == "あり":
            st.session_state.pfs_recist_date = st.date_input("診断日（画像・組織）*", value=st.session_state.pfs_recist_date, key="d_extra_90")
            # 「肺」を含む最新リストに統一
            st.session_state.pfs_recist_site = st.multiselect("再発部位*", ["肺", "リンパ節", "肝", "骨", "手術局所", "その他"], default=st.session_state.pfs_recist_site)
            
            extra_tx_opts = ["選択してください", "プラチナ製剤併用療法（GC等）", "維持療法（アベルマブ等）", "EVP再開", "ペムブロリズマブ単剤", "ニボルマブ単剤", "転移巣切除", "放射線治療", "その他"]
            st.session_state.pfs_recist_tx = st.selectbox("実施治療*", extra_tx_opts, index=get_idx(extra_tx_opts, st.session_state.pfs_recist_tx))
            
            if st.session_state.pfs_recist_tx in ["転移巣切除", "放射線治療"]:
                st.session_state.extra_op_date_90 = st.date_input(f"{st.session_state.pfs_recist_tx} 実施日*", value=st.session_state.extra_op_date_90, key="e_op_90")
            if st.session_state.pfs_recist_tx in DRUG_LIST:
                ex1, ex2 = st.columns(2)
                st.session_state.extra_tx_start_90 = ex1.date_input("治療開始日*", value=st.session_state.extra_tx_start_90, key="e_start_90")
                st.session_state.extra_tx_ongoing_90 = ex2.checkbox("継続中", value=st.session_state.extra_tx_ongoing_90, key="e_ongoing_90")

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.status_alive_90 = st.radio("生存状況*", ["生存", "死亡"], index=None, horizontal=True)
        if st.session_state.status_alive_90 == "生存":
            st.session_state.final_visit_date_90 = st.date_input("最終生存確認日*", value=st.session_state.final_visit_date_90)
    with c2:
        if st.session_state.status_alive_90 == "死亡":
            st.session_state.death_date_90 = st.date_input("死亡日*", value=st.session_state.death_date_90)
            st.session_state.death_cause_90 = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"])

    st.divider()

    if st.button("🚀 90日目データを確定送信", type="primary", use_container_width=True):
        err = []
        d = st.session_state
        if d.facility_name == "選択してください": err.append("・施設名")
        if not d.patient_id: err.append("・識別コード")
        if not d.op_date_90: err.append("・手術実施日")
        if d.status_alive_90 == "生存" and d.adj_plan_90 == "選択してください": err.append("・現在の治療状況")
        if d.pfs_intra_status == "あり" and not d.pfs_intra_tx: err.append("・尿路内再発の治療内容")
        
        if err: st.error("入力不備があります：\n" + "\n".join(err))
        else:
            rep = f"【JUOG 90D報告】ID:{d.patient_id} / 施設:{d.facility_name}\n生存:{d.status_alive_90} / PFS判定済"
            if send_email(rep, d.patient_id, d.facility_name, d.reporter_email):
                st.success("確定送信されました。"); st.balloons()
