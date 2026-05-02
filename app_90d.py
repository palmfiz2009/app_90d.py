import streamlit as st
import json
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ページ設定 ---
st.set_page_config(page_title="JUOG UTUC_Consolidative 90-Day CRF", layout="wide")

# --- JUOG専用デザインCSS (完全維持) ---
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

# --- ヘルプテキスト (詳細版維持) ---
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

# --- セッション状態初期化 (デフォルト None) ---
if 'init_90d_done' not in st.session_state:
    st.session_state['init_90d_done'] = True
    defaults = {
        "facility_name": "選択してください", "patient_id": "",
        "op_date_90": None, "eval_date_90": None, "vital_abnormality_90": None, "vital_detail_90": "",
        "wbc_90": None, "hb_90": None, "plt_90": None, "ast_90": None, "alt_90": None,
        "ldh_90": None, "alb_90": None, "cre_90": None, "egfr_90": None, "crp_90": None,
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
st.markdown('<div class="top-info-bar">', unsafe_allow_html=True)
col_h1, col_h2 = st.columns(2)
with col_h1:
    idx_fac = FACILITY_LIST.index(st.session_state.facility_name) if st.session_state.facility_name in FACILITY_LIST else 0
    st.session_state.facility_name = st.selectbox("施設名*", FACILITY_LIST, index=idx_fac)
with col_h2:
    st.session_state.patient_id = st.text_input("研究対象者識別コード*", value=st.session_state.patient_id)
st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🩺 診察・検査", "📋 安全性・治療状況", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

with tab1:
    st.markdown('<div class="juog-header">1. 身体所見・検査 (術後90日±14日)</div>', unsafe_allow_html=True)
    c_top1, c_top2 = st.columns(2)
    with c_top1:
        st.session_state.op_date_90 = st.date_input("手術実施日*", value=st.session_state.op_date_90)
        if st.session_state.op_date_90:
            target_90 = st.session_state.op_date_90 + timedelta(days=90)
            st.info(f"90日目目安: {target_90} (許容範囲: {target_90 - timedelta(days=14)} ～ {target_90 + timedelta(days=14)})")
        st.session_state.eval_date_90 = st.date_input("評価実施日(来院日)*", value=st.session_state.eval_date_90)
        st.session_state.vital_abnormality_90 = st.radio("身体所見の異常*", ["異常なし", "異常あり"], index=None, horizontal=True)
        if st.session_state.vital_abnormality_90 == "異常あり": st.session_state.vital_detail_90 = st.text_input("異常の詳細*")
    with c_top2:
        cyto_opts = ["選択してください", "NILM (Class I・II)", "AUC (Class III相当)", "SHGUC (Class IV相当)", "HGUC (Class V相当)", "LGUC", "判定不能", "未実施"]
        idx_cyto = cyto_opts.index(st.session_state.cytology_90) if st.session_state.cytology_90 in cyto_opts else 0
        st.session_state.cytology_90 = st.selectbox("尿細胞診結果*", cyto_opts, index=idx_cyto)

    st.markdown("---")
    # 採血レイアウト維持 (デフォルト空欄)
    bc1, bc2 = st.columns(2)
    with bc1:
        st.session_state.wbc_90 = st.number_input("WBC (/μL)*", value=st.session_state.wbc_90, step=1.0)
        st.session_state.hb_90 = st.number_input("Hb (g/dL)*", value=st.session_state.hb_90, step=0.1)
        st.session_state.plt_90 = st.number_input("PLT (x10^4/μL)*", value=st.session_state.plt_90, step=1.0)
        st.session_state.ast_90 = st.number_input("AST (U/L)*", value=st.session_state.ast_90, step=1.0)
        st.session_state.alt_90 = st.number_input("ALT (U/L)*", value=st.session_state.alt_90, step=1.0)
    with bc2:
        st.session_state.ldh_90 = st.number_input("LDH (U/L)*", value=st.session_state.ldh_90, step=1.0)
        st.session_state.alb_90 = st.number_input("Alb (g/dL)*", value=st.session_state.alb_90, step=0.1)
        st.session_state.cre_90 = st.number_input("Cre (mg/dL)*", value=st.session_state.cre_90, step=0.01)
        st.session_state.egfr_90 = st.number_input("eGFR (mL/min/1.73m²)*", value=st.session_state.egfr_90, step=0.1)
        st.session_state.crp_90 = st.number_input("CRP (mg/dL)*", value=st.session_state.crp_90, step=0.01)

    st.markdown('<p style="font-size:18px; font-weight:bold; margin-top:20px; margin-bottom:5px;">白血球分画 (%)</p>', unsafe_allow_html=True)
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
        st.session_state.cd_grade_90 = st.selectbox("術後90日までの合併症 (CD分類)*", cd_opts, index=idx_cd, help=HELP_CD)
        if st.session_state.cd_grade_90 not in ["選択してください", "Grade 0"]:
            st.session_state.cd_detail_90 = st.text_area("合併症の詳細内容*", value=st.session_state.cd_detail_90)
    with c2:
        adj_opts = ["選択してください", "無治療（経過観察）", "後治療を計画中", "EVP継続投与", "ペムブロ維持", "ニボ単剤", "GC療法", "GCarbo療法", "その他"]
        idx_adj = adj_opts.index(st.session_state.adj_plan_90) if st.session_state.adj_plan_90 in adj_opts else 0
        st.session_state.adj_plan_90 = st.selectbox("現在の治療実施状況*", adj_opts, index=idx_adj)
        if st.session_state.adj_plan_90 == "その他":
            st.session_state.adj_other_90 = st.text_area("詳細*", value=st.session_state.adj_other_90)

with tab3:
    st.markdown('<div class="juog-header">3. 再発評価 (PFS判定)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("【尿路内再発】")
        st.session_state.pfs_intra_status = st.radio("尿路内再発の有無 (膀胱・対側上部尿路)*", ["なし", "あり"], index=None, horizontal=True)
        if st.session_state.pfs_intra_status == "あり":
            st.session_state.pfs_intra_date = st.date_input("尿路内再発確定日*", value=st.session_state.pfs_intra_date)
            st.session_state.pfs_intra_site = st.multiselect("部位", ["膀胱内", "対側尿管", "対側腎盂", "尿道"])
            st.session_state.pfs_intra_tx = st.selectbox("尿路内再発に対する治療内容*", ["未選択", "TURBT", "内視鏡的焼灼術", "注入療法", "温存療法", "経過観察", "その他"])
    with c2:
        st.subheader("【尿路外再発・進行】")
        st.session_state.pfs_recist_status = st.radio("尿路外・RECIST進行の有無*", ["なし", "あり"], index=None, horizontal=True)
        if st.session_state.pfs_recist_status == "あり":
            st.session_state.pfs_recist_date = st.date_input("再発・進行確定日(PFSイベント日)*", value=st.session_state.pfs_recist_date)
            st.session_state.pfs_recist_site = st.multiselect("進行部位*", ["手術局所", "領域リンパ節", "遠隔リンパ節", "肺", "肝", "骨", "既存転移巣の増大", "その他"])
            st.session_state.pfs_recist_tx = st.selectbox("治療内容*", ["未選択", "EVP再開", "薬剤変更", "転移巣切除", "放射線治療", "集学的治療(TACE併用等詳細を記載)", "その他"])

with tab4:
    st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.status_alive_90 = st.radio("生存状況 (術後90日時点)*", ["生存", "死亡"], index=None, horizontal=True)
        if st.session_state.status_alive_90 == "生存":
            st.session_state.final_visit_date_90 = st.date_input("最終生存確認日(最終来院日)*", value=st.session_state.final_visit_date_90)
    with c2:
        if st.session_state.status_alive_90 == "死亡":
            st.session_state.death_date_90 = st.date_input("死亡日*", value=st.session_state.death_date_90)
            st.session_state.death_cause_90 = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"])

    st.divider()

    # --- 送信ロジック ---
    if st.button("🚀 90日目データを確定送信", type="primary", use_container_width=True):
        h_errors = [] # ハードエラー（統計破綻）
        s_warnings = [] # ソフト警告（臨床的欠損/許容）
        d = st.session_state

        # 1. 必須基本情報
        if d.facility_name == "選択してください": h_errors.append("・施設名")
        if not d.patient_id: h_errors.append("・識別コード")
        if not d.op_date_90: h_errors.append("・手術実施日")
        if not d.eval_date_90: h_errors.append("・評価来院日")
        if d.cd_grade_90 == "選択してください": h_errors.append("・CD分類")
        if d.status_alive_90 is None: h_errors.append("・生存状況")

        # 2. 論理整合性チェック (時間軸)
        if d.op_date_90:
            if d.eval_date_90 and d.eval_date_90 < d.op_date_90: h_errors.append("・評価来院日が手術日より過去です")
            if d.pfs_intra_status == "あり" and d.pfs_intra_date and d.pfs_intra_date < d.op_date_90: h_errors.append("・尿路内再発日が手術日より過去です")
            if d.pfs_recist_status == "あり" and d.pfs_recist_date and d.pfs_recist_date < d.op_date_90: h_errors.append("・尿路外進行日が手術日より過去です")
            if d.status_alive_90 == "死亡" and d.death_date_90 and d.death_date_90 < d.op_date_90: h_errors.append("・死亡日が手術日より過去です")
            
            # 90日窓チェック (ソフト警告に緩和)
            target = d.op_date_90 + timedelta(days=90)
            if d.eval_date_90 and not (target - timedelta(days=14) <= d.eval_date_90 <= target + timedelta(days=14)):
                s_warnings.append(f"評価日が術後90日窓外（規定：{target-timedelta(days=14)}〜{target+timedelta(days=14)}）")

        # 3. 生存×CD分類整合性
        if d.status_alive_90 == "死亡":
            if d.cd_grade_90 != "Grade V": h_errors.append("・死亡なのにCD分類がGrade V以外です")
            if d.death_cause_90 == "選択してください": h_errors.append("・死因未選択")
        elif d.status_alive_90 == "生存":
            if d.cd_grade_90 == "Grade V": h_errors.append("・生存なのにCD分類がGrade Vになっています")
            if not d.final_visit_date_90: h_errors.append("・最終生存確認日を入力してください")

        # 4. ソフト警告（緩和項目）
        if d.vital_abnormality_90 is None: s_warnings.append("身体所見（異常の有無）")
        if d.cytology_90 == "選択してください": s_warnings.append("尿細胞診結果")
        
        # 採血項目の警告 (Noneを検知)
        imp_labs = {"WBC":d.wbc_90, "Hb":d.hb_90, "PLT":d.plt_90, "Cre":d.cre_90}
        for k, v in imp_labs.items():
            if v is None: s_warnings.append(k)
        
        # 分画合計チェック
        diff_sum = (d.neutro_90 or 0) + (d.lympho_90 or 0) + (d.mono_90 or 0) + (d.eosino_90 or 0) + (d.baso_90 or 0)
        if diff_sum > 0 and not (98.0 <= diff_sum <= 102.0):
            s_warnings.append(f"白血球分画合計({diff_sum:.1f}%)")
        elif diff_sum == 0.0:
            s_warnings.append("白血球分画")

        # --- 送信判断 ---
        if h_errors:
            st.error("以下の論理矛盾または必須情報漏れがあります。修正してください：\n" + "\n".join(h_errors))
        elif s_warnings:
            st.session_state.needs_confirm = True
            st.session_state.pending_s_warnings = s_warnings
            st.rerun()
        else:
            st.session_state.do_send = True

    # 警告確認ダイアログ
    if st.session_state.needs_confirm:
        st.warning(f"確認：以下の項目が未入力、または規定範囲外です ({', '.join(st.session_state.pending_s_warnings)})。このまま送信しますか？")
        if st.button("⚠️ はい、不備を承知で送信します"):
            st.session_state.do_send = True
            st.session_state.needs_confirm = False

    # 最終送信
    if st.session_state.do_send:
        def f_val(v): return str(v) if v is not None else "N/A"
        rep = f"""
【JUOG 90D CRF報告】
施設: {st.session_state.facility_name} / ID: {st.session_state.patient_id}
手術日: {st.session_state.op_date_90} / 評価日: {st.session_state.eval_date_90}
生存: {st.session_state.status_alive_90} (CD:{st.session_state.cd_grade_90})
主要採血: WBC:{f_val(st.session_state.wbc_90)}, Hb:{f_val(st.session_state.hb_90)}, Cre:{f_val(st.session_state.cre_90)}
"""
        if send_email(rep, st.session_state.patient_id, st.session_state.facility_name):
            st.success("術後90日目データが正常に送信されました。")
            st.balloons()
        st.session_state.do_send = False
