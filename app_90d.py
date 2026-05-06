import streamlit as st
import json
import math
import smtplib
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. Config (定数・設定)
# ==========================================
st.set_page_config(page_title="JUOG UTUC_Consolidative 90-Day CRF", layout="wide")

FACILITY_LIST = ["選択してください", "愛知県がんセンター", "秋田大学", "愛媛大学", "大分大学", "大阪公立大学", "大阪大学", "大阪府済生会野江病院", "岡山大学", "香川大学", "鹿児島大学", "関西医科大学", "岐阜大学", "九州大学病院", "京都大学", "久留米大学", "神戸大学", "国立がん研究センター中央病院", "国立病院機構四国がんセンター", "札幌医科大学", "千葉大学", "筑波大学", "東京科学大学", "東京慈恵会医科大学", "東京慈恵会医科大学附属柏病院", "東北大学", "鳥取大学", "富山大学", "長崎大学病院", "名古屋大学", "奈良県立医科大学", "新潟大学大学院 医歯学総合研究科", "浜松医科大学", "原三信病院", "兵庫医科大学", "弘前大学", "北海道大学", "三重大学", "横浜市立大学", "琉球大学", "和歌山県立医科大学", "その他"]
SURGERY_LIST = ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "転移巣切除"]
DRUG_LIST = ["BCG注入療法", "抗がん剤注入療法", "プラチナ製剤併用療法（GC等）", "維持療法（アベルマブ等）", "EVP再開", "ペムブロリズマブ単剤", "ニボルマブ単剤", "放射線治療", "その他"]

# 🔴 左旧コードより一字一句違わず復元
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

# 🔴 左旧コードより一字一句違わず復元
HELP_CYTO = """【尿細胞診結果】
* Negative: 陰性（クラスI・II）
* AUC: 非定型細胞
* SHGUC: 高異型度癌疑い
* HGUC: 高異型度癌（クラスIV・V相当）
* LGUC: 低異型度腫瘍"""

st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; }
    .block-container { max-width: 1100px !important; padding-top: 1.5rem !important; padding-bottom: 5rem !important; margin: auto !important; }
    h1 { font-size: 26px !important; color: #0F172A; text-align: center; margin-bottom: 40px !important; font-weight: 800; }
    .juog-header { background-color: #1E3A8A; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; }
    label { font-weight: 600 !important; color: #334155 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. State Management (状態管理)
# ==========================================
def init_state():
    if 'crf_state_initialized' not in st.session_state:
        defaults = {
            "facility_name": "選択してください", "patient_id": "", "reporter_email": "",
            "op_date_90": None, "vital_abnormality_90": "未評価", "vital_detail_90": "",
            "cytology_90": "選択してください",
            "cd_grade_90": "選択してください", "cd_date_90": None, "cd_detail_90": "", 
            "has_ctcae_90": False, "ae_status": "", 
            "adj_plan_90": "選択してください", "adj_other_90": "", "adj_start_90": None, "adj_end_90": None, "adj_ongoing_90": False,
            "pfs_intra_status": "未選択", "pfs_intra_date": None, "pfs_intra_site": [], "pfs_intra_site_other": "", "pfs_intra_tx": [], "pfs_intra_tx_other": "", "intra_op_date_90": None, "intra_tx_start_90": None, "intra_tx_end_90": None, "intra_tx_ongoing_90": False, "pfs_intra_path_90": "",
            "pfs_recist_status": "未選択", "pfs_recist_date": None, "pfs_recist_site": [], "pfs_recist_site_other": "", "pfs_recist_tx": "選択してください", "pfs_recist_tx_detail": "", "extra_op_date_90": None, "extra_tx_start_90": None, "extra_tx_end_90": None, "extra_tx_ongoing_90": False,
            "status_alive_90": "未選択", "final_visit_date_90": None, "death_cause_90": "選択してください", "death_date_90": None,
            "wbc_90": None, "hb_90": None, "plt_90": None, "ast_90": None, "alt_90": None, "ldh_90": None, "alb_90": None, "cre_90": None, "egfr_90": None, "crp_90": None,
            "neutro_90": None, "lympho_90": None, "mono_90": None, "eosino_90": None, "baso_90": None
        }
        for k, v in defaults.items():
            st.session_state[k] = v
        st.session_state['crf_state_initialized'] = True

# ==========================================
# 3. Transform Layer
# ==========================================
def normalize(v):
    if v is None or v == "" or v in ["選択してください", "未選択", "未評価"]: return "NA"
    if isinstance(v, list): return ", ".join(v) if v else "NA"
    if isinstance(v, (date, datetime)): return v.strftime("%Y-%m-%d")
    if isinstance(v, float) and math.isnan(v): return "NA"
    return str(v)

def build_payload(state):
    p = {k: v for k, v in state.items() if not k.startswith("crf_")}
    if p.get("vital_abnormality_90") != "異常あり": p["vital_detail_90"] = None
    if p.get("cd_grade_90") in ["選択してください", "未評価", "Grade 0"]: p["cd_date_90"] = None; p["cd_detail_90"] = None
    if not p.get("has_ctcae_90"): p["ae_status"] = None
    if p.get("adj_plan_90") in ["選択してください", "無治療（経過観察）"]:
        p["adj_other_90"] = None; p["adj_start_90"] = None; p["adj_end_90"] = None; p["adj_ongoing_90"] = False
    if p.get("pfs_intra_status") != "あり":
        p["pfs_intra_date"] = None; p["pfs_intra_site"] = []; p["pfs_intra_site_other"] = None
        p["pfs_intra_tx"] = []; p["pfs_intra_tx_other"] = None; p["intra_op_date_90"] = None
        p["pfs_intra_path_90"] = None; p["intra_tx_start_90"] = None; p["intra_tx_end_90"] = None; p["intra_tx_ongoing_90"] = False
    if p.get("pfs_recist_status") != "あり":
        p["pfs_recist_date"] = None; p["pfs_recist_site"] = []; p["pfs_recist_site_other"] = None
        p["pfs_recist_tx"] = "選択してください"; p["pfs_recist_tx_detail"] = None
        p["extra_op_date_90"] = None; p["extra_tx_start_90"] = None; p["extra_tx_end_90"] = None; p["extra_tx_ongoing_90"] = False
    if p.get("status_alive_90") == "生存": p["death_date_90"] = None; p["death_cause_90"] = "選択してください"
    elif p.get("status_alive_90") == "死亡": p["final_visit_date_90"] = None
    return {k: normalize(v) for k, v in p.items()}

# ==========================================
# 4. Validation (EDC仕様)
# ==========================================
def is_empty(v):
    if v is None: return True
    if isinstance(v, str) and v.strip() == "": return True
    if v in ["選択してください", "未選択", "未評価"]: return True
    if isinstance(v, list) and len(v) == 0: return True
    return False

def validate(d):
    err = []
    today = date.today()
    required = [("facility_name", "施設名"), ("patient_id", "識別コード"), ("op_date_90", "初回手術日/予定日"), ("cytology_90", "尿細胞診結果"), ("status_alive_90", "生存状況")]
    for k, label in required:
        if is_empty(d.get(k)): err.append(f"・{label}")
    status = d.get("status_alive_90")
    if status == "生存" and not d.get("final_visit_date_90"): err.append("・最終生存確認日")
    if status == "死亡":
        if not d.get("death_date_90"): err.append("・死亡日")
        if d.get("death_cause_90") == "選択してください": err.append("・死因")
    if d.get("vital_abnormality_90") == "異常あり" and not d.get("vital_detail_90"): err.append("・身体所見の異常詳細")
    if d.get("has_ctcae_90") and is_empty(d.get("ae_status")): err.append("・有害事象の詳細（CTCAE）")
    cd = d.get("cd_grade_90")
    if not is_empty(cd) and cd not in ["Grade 0"]:
        if is_empty(d.get("cd_date_90")): err.append("・合併症発現日")
        if is_empty(d.get("cd_detail_90")): err.append("・合併症詳細")
    if d.get("pfs_intra_status") == "あり":
        if is_empty(d.get("pfs_intra_date")): err.append("・尿路内再発の診断日")
        if is_empty(d.get("pfs_intra_site")): err.append("・尿路内再発部位")
    return err

# ==========================================
# 5. Email (左旧コード文言で完全復元)
# ==========================================
def build_report(payload):
    return f"""【JUOG 90D報告】
施設名: {payload['facility_name']} / ID: {payload['patient_id']}
報告者: {payload['reporter_email']}
手術日: {payload['op_date_90']}

--- 1. 身体所見・検査データ ---
身体所見の異常: {payload['vital_abnormality_90']} ({payload['vital_detail_90']})
尿細胞診結果: {payload['cytology_90']}
血液検査: WBC:{payload['wbc_90']}, Hb:{payload['hb_90']}, PLT:{payload['plt_90']}, AST:{payload['ast_90']}, ALT:{payload['alt_90']}, LDH:{payload['ldh_90']}, Alb:{payload['alb_90']}, Cre:{payload['cre_90']}, eGFR:{payload['egfr_90']}, CRP:{payload['crp_90']}
白血球分画: Neutro {payload['neutro_90']}%, Lympho {payload['lympho_90']}%, Mono {payload['mono_90']}%, Eosino {payload['eosino_90']}%, Baso {payload['baso_90']}%

--- 2. 安全性評価および術後補助療法 ---
合併症(CD): {payload['cd_grade_90']} (発現日: {payload['cd_date_90']}) / 詳細: {payload['cd_detail_90']}
現在の治療: {payload['adj_plan_90']} / 開始日: {payload['adj_start_90']}

--- 3. 再発評価 ---
尿路内再発: {payload['pfs_intra_status']} (診断日: {payload['pfs_intra_date']})
尿路外再発: {payload['pfs_recist_status']} (診断日: {payload['pfs_recist_date']})

--- 4. 生存状況 ---
生存状況: {payload['status_alive_90']} (生存確認/死亡日: {payload['final_visit_date_90'] if payload['status_alive_90']=='生存' else payload['death_date_90']})
"""

def send_email(body, pid, facility, user_email=None):
    try:
        mail_user = st.secrets["email"]["user"]; mail_pass = st.secrets["email"]["pass"]
        to_addrs = ["urosec@kmu.ac.jp", "yoshida.tks@kmu.ac.jp"]
        if user_email: to_addrs.append(user_email)
        msg = MIMEMultipart(); msg['From'] = mail_user; msg['To'] = ", ".join(to_addrs)
        msg['Subject'] = f"【JUOG 90D報告】（{facility} / ID: {pid}）"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(mail_user, mail_pass); server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"メール送信エラー: {e}"); return False

# ==========================================
# 6. UI Layer
# ==========================================
def render_ui():
    st.title("JUOG UTUC_Consolidative 術後90日目 CRF")
    with st.sidebar:
        st.markdown('<div class="juog-header">📌 入力ガイド</div>', unsafe_allow_html=True)
        st.info(HELP_CD)
        st.info(HELP_CYTO)

    with st.form("crf_form"):
        st.markdown('<div class="juog-header">1. 基本情報・評価対象期間</div>', unsafe_allow_html=True)
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.selectbox("施設名*", FACILITY_LIST, key="facility_name")
            st.text_input("研究対象者識別コード*", key="patient_id")
        with col_h2:
            st.text_input("報告者メールアドレス*", key="reporter_email")
            st.date_input("手術日（非施行例は予定日）*", value=None, key="op_date_90")

        tab1, tab2, tab3, tab4 = st.tabs(["🩺 身体所見・検査", "📋 安全性・術後補助療法", "🖼 再発評価 (PFS)", "⚖️ 生存確認 (OS)"])

        with tab1:
            st.markdown('<div class="juog-header">身体所見・検査データ</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.radio("身体所見の異常*", ["未評価", "異常なし", "異常あり"], key="vital_abnormality_90", horizontal=True)
                if st.session_state.get("vital_abnormality_90") == "異常あり":
                    st.text_input("異常の詳細*", key="vital_detail_90")
            with c2:
                st.selectbox("尿細胞診結果*", ["選択してください", "Negative (クラスI・II)", "AUC (非定型細胞)", "SHGUC (高異型度癌疑い)", "HGUC (クラスIV・V相当)", "LGUC (低異型度腫瘍)", "判定不能", "未実施"], key="cytology_90", help=HELP_CYTO)
            
            st.markdown("---")
            with st.expander("🔬 血液検査データ（任意入力） *※未入力は「NA」として処理されます*"):
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.number_input("WBC (/μL)*", value=None, key="wbc_90", step=0.1)
                    st.number_input("Hb (g/dL)*", value=None, key="hb_90", step=0.1)
                    st.number_input("PLT (x10^4/μL)*", value=None, key="plt_90", step=0.1)
                    st.number_input("AST (U/L)*", value=None, key="ast_90", step=0.1)
                    st.number_input("ALT (U/L)*", value=None, key="alt_90", step=0.1)
                with bc2:
                    st.number_input("LDH (U/L)*", value=None, key="ldh_90", step=0.1)
                    st.number_input("Alb (g/dL)*", value=None, key="alb_90", step=0.1)
                    st.number_input("Cre (mg/dL)*", value=None, key="cre_90", step=0.01)
                    st.number_input("eGFR (mL/min)*", value=None, key="egfr_90", step=0.1)
                    st.number_input("CRP (mg/dL)*", value=None, key="crp_90", step=0.01)
                st.markdown("**白血球分画 (%)**")
                d1, d2, d3, d4, d5 = st.columns(5)
                with d1: st.number_input("Neutro*", value=None, key="neutro_90")
                with d2: st.number_input("Lympho*", value=None, key="lympho_90")
                with d3: st.number_input("Mono*", value=None, key="mono_90")
                with d4: st.number_input("Eosino*", value=None, key="eosino_90")
                with d5: st.number_input("Baso*", value=None, key="baso_90")

        with tab2:
            st.markdown('<div class="juog-header">2. 安全性評価および術後補助療法の状況</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("合併症 (Clavien-Dindo分類)*", ["選択してください", "未評価", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"], key="cd_grade_90", help=HELP_CD)
                if st.session_state.get("cd_grade_90") not in ["選択してください", "未評価", "Grade 0"]:
                    st.date_input("合併症の発現日*", value=None, key="cd_date_90")
                    st.text_area("外科的合併症の詳細内容*", key="cd_detail_90")
                st.markdown("---")
                st.checkbox("薬剤関連等の有害事象（CTCAE準拠）を報告する", key="has_ctcae_90")
                if st.session_state.get("has_ctcae_90"):
                    st.text_area("有害事象の詳細*", value="", key="ae_status", placeholder="発現日、内容、重症度、処置、転帰などを記入")
            with c2:
                st.selectbox("現在の治療実施状況（補助療法等）*", ["選択してください", "無治療（経過観察）", "術前からのEVP継続投与", "術前からのEV単独継続", "術前からのペムブロリズマブ継続", "ニボルマブ単剤", "GC療法", "GCarbo療法", "放射線治療", "その他"], key="adj_plan_90")
                if st.session_state.get("adj_plan_90") not in ["選択してください", "無治療（経過観察）"]:
                    st.text_input("治療の詳細（※その他の場合）*", key="adj_other_90")
                    st.markdown("###### 治療日程")
                    ax1, ax2 = st.columns(2)
                    with ax1: st.date_input("開始日*", value=None, key="adj_start_90")
                    with ax2:
                        st.checkbox("現在も継続中", key="adj_ongoing_90")
                        if not st.session_state.get("adj_ongoing_90"):
                            st.date_input("終了日*", value=None, key="adj_end_90")

        with tab3:
            st.markdown('<div class="juog-header">3. 再発評価 (PFS判定)</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**【尿路内再発】**")
                st.radio("尿路内再発の有無*", ["未選択", "なし", "あり"], key="pfs_intra_status", horizontal=True)
                if st.session_state.get("pfs_intra_status") == "あり":
                    st.date_input("診断日（組織・画像・膀胱鏡等）*", value=None, key="pfs_intra_date")
                    st.multiselect("再発部位*", ["膀胱", "対側腎盂", "対側尿管", "同側残存尿管", "その他"], key="pfs_intra_site")
                    st.multiselect("実施した治療*", ["経過観察", "TURBT", "BCG注入療法", "抗がん剤注入療法", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "その他"], key="pfs_intra_tx")
                    st.date_input("手術実施日（※手術ありの場合）*", value=None, key="intra_op_date_90")
                    st.text_area("組織型、Grade、pTNM分類 等*", key="pfs_intra_path_90")
            with c2:
                st.markdown("**【尿路外再発】**")
                st.radio("尿路外再発の有無*", ["未選択", "なし", "あり"], key="pfs_recist_status", horizontal=True)
                if st.session_state.get("pfs_recist_status") == "あり":
                    st.date_input("診断日（画像・組織等）*", value=None, key="pfs_recist_date")
                    st.multiselect("再発部位*", ["肺", "リンパ節", "肝", "骨", "手術局所", "その他"], key="pfs_recist_site")
                    st.selectbox("実施治療*", ["選択してください", "プラチナ製剤併用療法", "維持療法", "EVP再開", "免疫チェックポイント阻害剤", "転移巣切除", "放射線治療", "その他"], key="pfs_recist_tx")
                    st.date_input("薬物療法開始日", value=None, key="extra_tx_start_90")

        with tab4:
            st.markdown('<div class="juog-header">4. 生存状況確認 (Overall Survival)</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.radio("生存状況*", ["未選択", "生存", "死亡"], key="status_alive_90", horizontal=True)
                if st.session_state.get("status_alive_90") == "生存":
                    st.date_input("最終生存確認日*", value=None, key="final_visit_date_90")
            with c2:
                if st.session_state.get("status_alive_90") == "死亡":
                    st.date_input("死亡日*", value=None, key="death_date_90")
                    st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], key="death_cause_90")
            st.divider()
            # 🔴 送信ボタンを最後のタブ内にのみ配置
            return st.form_submit_button("🚀 90日目データを確定送信", type="primary", use_container_width=True)

# ==========================================
# 7. Controller
# ==========================================
init_state()
submitted = render_ui()

if submitted:
    curr = st.session_state.to_dict()
    errors = validate(curr)
    if errors:
        st.error("⚠️ 入力不備があります。修正してください：")
        for e in errors: st.markdown(f"- 🔴 **{e}**")
    else:
        payload = build_payload(curr)
        rep = build_report(payload)
        if send_email(rep, payload['patient_id'], payload['facility_name'], payload['reporter_email']):
            st.success("✅ 確定送信されました。事務局および報告者宛に控えメールを送信しました。")
            st.balloons()
            st.download_button(label="📄 構造化データ(JSON)を保存", data=json.dumps(payload, ensure_ascii=False, indent=2), file_name=f"JUOG_90D_{payload['patient_id']}.json", mime="application/json")
