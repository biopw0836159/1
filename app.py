import streamlit as st
import pandas as pd
import hashlib

# 1. 页面配置
st.set_page_config(page_title="抓鬼专家", layout="wide")

# 2. 样式美化 (重点修改侧边栏颜色)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    
    /* 【核心修改：侧边栏改为浅色，文字改为黑色】 */
    [data-testid="stSidebar"] { 
        background-color: #f1f5f9 !important; /* 浅灰蓝色底 */
        min-width: 350px !important; 
    }
    /* 强行覆盖侧边栏所有文字颜色为深色 */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .stToggle p { 
        color: #1e293b !important; 
        font-weight: 700 !important; 
    }

    /* 侧边栏巨型红色开关（保持不变） */
    [data-testid="collapsedControl"] {
        background-color: #ff4b4b !important; width: 130px !important; height: 48px !important;
        border-radius: 0 25px 25px 0 !important; top: 15px !important; color: white !important;
        box-shadow: 4px 4px 15px rgba(255, 75, 75, 0.5) !important;
    }
    [data-testid="collapsedControl"]::after { content: " ⚙️ 菜单开关"; font-size: 14px; font-weight: bold; color: white; }
    
    /* 统计看板 */
    .metric-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid #ef4444;
        text-align: center; margin-bottom: 10px;
    }
    .metric-value { font-size: 28px; font-weight: 800; color: #ef4444; }
    .metric-label { font-size: 13px; color: #64748b; font-weight: 600; }

    .title-banner {
        background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
        padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px;
    }
    .badge-red { background: #fee2e2; color: #ef4444; padding: 2px 8px; border-radius: 6px; font-weight: bold; border: 1px solid #fecaca; }
    .table-header {
        background-color: #e2e8f0; padding: 12px 10px; border-radius: 8px;
        font-weight: bold; color: #475569; margin-bottom: 10px; display: flex; align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 登录逻辑 (0224)
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("<div style='height:100px'></div>", unsafe_allow_html=True)
        st.title("🔐 欢迎光临")
        pwd = st.text_input("请输入访问密码", type="password")
        if st.button("进入系统", use_container_width=True):
            if pwd == "0224": st.session_state.auth = True; st.rerun()
            else: st.error("❌ 密码错误")
    st.stop()

# 4. 核心引擎 (保留所有条件：刷人数/刷量/盈利大户/对刷)
def run_audit_engine(df, rules):
    try:
        df.columns = [str(c).strip() for c in df.columns]
        mapping = {'user':['用户名','账号','会员'],'vol':['销量','投注'],'cnt':['单数','次数'],'profit':['盈亏','盈利'],'bonus':['奖金','派奖','中奖']}
        final_cols = {}
        for k, aliases in mapping.items():
            for col in df.columns:
                if any(a in col for a in aliases): final_cols[k] = col; break
        
        temp_df = pd.DataFrame()
        temp_df['用户名'] = df[final_cols['user']].astype(str)
        temp_df['销量'] = pd.to_numeric(df[final_cols['vol']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        temp_df['单数'] = pd.to_numeric(df[final_cols['cnt']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        temp_df['盈亏'] = pd.to_numeric(df[final_cols['profit']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        temp_df['奖金'] = pd.to_numeric(df[final_cols['bonus']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        grouped = temp_df.groupby('用户名').agg({'销量':'sum', '单数':'sum', '盈亏':'sum', '奖金':'sum'}).reset_index()
        grouped['RTP'] = grouped.apply(lambda x: x['奖金'] / x['销量'] if x['销量'] > 0 else 0, axis=1)

        def apply_logic(row):
            v, c, p, r = row['销量'], row['单数'], row['盈亏'], row['RTP']
            if rules.get('use_manual', False):
                match = True
                if rules['v_on'] and not (rules['v_min'] <= v <= rules['v_max']): match = False
                if rules['c_on'] and not (c <= rules['c_limit']): match = False
                if rules['p_on'] and not (rules['p_min'] <= p <= rules['p_max']): match = False
                if rules['r_on'] and not (rules['r_min'] <= r <= rules['r_max']): match = False
                return "手动筛选" if match else None
            
            m = []
            if 1000 <= v <= 2000 and c <= 12: m.append("疑似刷人数")
            if v > 2000 and c <= 10: m.append("疑似对刷")
            if v >= 500000 and 0.995 <= r <= 1.000: m.append("疑似刷量")
            if p >= 100000: m.append("盈利大会员")
            return " | ".join(m) if m else None

        grouped['原因'] = grouped.apply(apply_logic, axis=1)
        return grouped[grouped['原因'].notna()].copy()
    except: return None

# 5. 侧边栏 (已改为浅色高亮)
with st.sidebar:
    st.markdown("### ⚙️ 审计控制中心")
    use_manual = st.toggle("🚀 手动自定义模式", value=False)
    st.write("---")
    v_on = st.toggle("销量筛选", False); v_min = st.number_input("Min销量", 0.0); v_max = st.number_input("Max销量", 2000.0)
    c_on = st.toggle("单数限制", False); c_limit = st.number_input("单数 ≤", 12)
    p_on = st.toggle("盈亏限制", False); p_min = st.number_input("Min盈亏", 100000.0); p_max = st.number_input("Max盈亏", 1000000.0)
    r_on = st.toggle("RTP限制", False); r_min = st.number_input("Min RTP", 0.995, format="%.3f"); r_max = st.number_input("Max RTP", 1.000, format="%.3f")
    manual_btn = st.button("🔥 执行审计", type="primary")
    rules = {'use_manual':use_manual, 'v_on':v_on, 'v_min':v_min, 'v_max':v_max, 'c_on':c_on, 'c_limit':c_limit, 'p_on':p_on, 'p_min':p_min, 'p_max':p_max, 'r_on':r_on, 'r_min':r_min, 'r_max':r_max}

# 6. 主界面
st.markdown("<div class='title-banner'><h1>📊 抓抓抓</h1></div>", unsafe_allow_html=True)
file = st.file_uploader("📂 丢这边", type=["xlsx", "csv"])

if file:
    f_hash = hashlib.md5(file.getvalue()).hexdigest()
    if st.session_state.get("last_f") != f_hash or manual_btn:
        raw = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
        st.session_state.res_data = run_audit_engine(raw, rules)
        st.session_state.last_f = f_hash
        st.session_state.read_set = set()

    res = st.session_state.get("res_data")
    if res is not None and not res.empty:
        # --- 🚀 异常统计看板 ---
        st.markdown("### 🚨 异常捕获实况")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.markdown(f"<div class='metric-card'><div class='metric-value'>{len(res)}</div><div class='metric-label'>锁定异常总数</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='metric-card'><div class='metric-value'>{len(res[res['原因'].str.contains('刷人数')])}</div><div class='metric-label'>疑似刷人数</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='metric-card'><div class='metric-value'>{len(res[res['原因'].str.contains('刷量')])}</div><div class='metric-label'>疑似刷量</div></div>", unsafe_allow_html=True)
        k4.markdown(f"<div class='metric-card'><div class='metric-value'>{len(res[res['原因'].str.contains('盈利')])}</div><div class='metric-label'>盈利大会员</div></div>", unsafe_allow_html=True)
        k5.markdown(f"<div class='metric-card'><div class='metric-value'>{len(res[res['原因'].str.contains('对刷')])}</div><div class='metric-label'>疑似对刷</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        sc1, sc2, sc3 = st.columns([1, 2, 2])
        sort_col = sc2.selectbox("排序字段", ["销量", "盈亏", "单数", "RTP"], index=0)
        sort_dir = sc3.selectbox("排序顺序", ["由大到小", "由小到大"], index=0)
        res = res.sort_values(by=sort_col, ascending=(sort_dir == "由小到大"))

        st.markdown("""<div class='table-header'><div style='flex:0.8'>核查</div><div style='flex:2'>用户名</div><div style='flex:2.5'>原因</div><div style='flex:1.5'>总销量</div><div style='flex:1.2'>单数</div><div style='flex:1.5'>盈亏</div><div style='flex:1.2'>RTP</div></div>""", unsafe_allow_html=True)
        with st.container(height=500):
            for i, row in res.iterrows():
                u = row['用户名']; is_read = u in st.session_state.read_set
                cols = st.columns([0.8, 2, 2.5, 1.5, 1.2, 1.5, 1.2])
                if cols[0].checkbox(" ", key=f"k_{u}_{i}", value=is_read): st.session_state.read_set.add(u)
                else: st.session_state.read_set.discard(u)
                style = "color:#94a3b8; text-decoration:line-through;" if is_read else "color:#1e293b;"
                cols[1].markdown(f"<span style='{style}'>{u}</span>", unsafe_allow_html=True)
                cols[2].markdown(f"<span class='badge-red'>{row['原因']}</span>", unsafe_allow_html=True)
                cols[3].markdown(f"<span style='{style}'>{row['销量']:,.0f}</span>", unsafe_allow_html=True)
                cols[4].markdown(f"<span style='{style}'>{int(row['单数'])}</span>", unsafe_allow_html=True)
                cols[5].markdown(f"<span style='{style}'>{row['盈亏']:,.0f}</span>", unsafe_allow_html=True)
                cols[6].markdown(f"<span style='{style}'>{row['RTP']:.3f}</span>", unsafe_allow_html=True)
                st.divider()
        st.download_button("📥 导出审计结果", res.to_csv(index=False).encode('utf-8-sig'), "audit_report.csv")
    elif res is not None:
        st.success("✅ 扫描完毕，未发现异常。")
