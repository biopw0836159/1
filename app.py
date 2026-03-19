import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="抓鬼", layout="wide")

# 1. 登录逻辑
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 审计系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == "0224":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# 2. 审计逻辑
def run_audit(df):
    df.columns = df.columns.str.strip()
    agg_rules = {
        '个人实际销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }
    # 检查核心列
    if '用户名' not in df.columns:
        st.error("❌ 找不到 '用户名' 列，请检查表头！")
        return pd.DataFrame()
    
    existing_cols = [c for c in agg_rules.keys() if c in df.columns]
    
    # 确保数据是数字
    for col in existing_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    grouped = df.groupby('用户名')[existing_cols].agg({k: agg_rules[k] for k in existing_cols}).reset_index()

    def get_labels(row):
        m = []
        v = row.get('个人实际销量', 0); c = row.get('投注单数', 0)
        r = row.get('RTP', 0); p = row.get('个人游戏盈亏', 0)
        if 1000 <= v <= 2000 and c < 12: m.append("疑似刷人数")
        if v > 500000 and 0.995 <= r <= 1: m.append("疑似刷量")
        if p > 100000: m.append("盈利大会员")
        if v > 2000 and c < 10: m.append("疑似对刷")
        return " | ".join(m) if m else None

    grouped['异常标记'] = grouped.apply(get_labels, axis=1)
    return grouped[grouped['异常标记'].notna()]

# 3. 界面逻辑
st.title("📊 异常用户自动筛查系统")
uploaded_file = st.file_uploader("请上传 Excel 档案", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # --- 强力读取逻辑 ---
        file_bytes = uploaded_file.read()
        try:
            # 尝试 1: 常规读取
            data = pd.read_excel(io.BytesIO(file_bytes))
        except:
            try:
                # 尝试 2: 强制 xlrd 读取
                data = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
            except:
                # 尝试 3: 如果是伪装成 xls 的 HTML 网页格式
                data = pd.read_html(io.BytesIO(file_bytes))[0]
        
        res = run_audit(data)
        
        if not res.empty:
            st.warning(f"发现 {len(res)} 个异常账户")
            st.dataframe(res, use_container_width=True)
            csv = res.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出结果", csv, "audit.csv")
        else:
            st.success("✅ 未发现异常。")
            
    except Exception as e:
        st.error(f"无法解析此文件。原因：{e}")
        st.info("💡 终极解决办法：请用 Excel 打开该文件，点『另存为』，选择『.xlsx』格式再上传。")
