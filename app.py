import streamlit as st
import pandas as pd
import io

# 1. 页面配置
st.set_page_config(page_title="抓鬼", layout="wide")

# 2. 登录逻辑
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

# 3. 核心审计逻辑
def run_audit(df):
    # 彻底清理：去掉空行，清理表头空格
    df = df.dropna(how='all').reset_index(drop=True)
    df.columns = df.columns.astype(str).str.strip()
    
    # 自动兼容：常见列名转换
    rename_dict = {
        '个人销量': '个人实际销量',
        '实际销量': '个人实际销量',
        '盈亏': '个人游戏盈亏'
    }
    df = df.rename(columns=rename_dict)
    
    required = ['用户名', '个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ 识别失败：表格中缺少列 {', '.join(missing)}")
        st.write("当前检测到的列名有：", list(df.columns))
        return pd.DataFrame()

    # 强制转换数值
    for col in ['个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 汇总计算
    grouped = df.groupby('用户名').agg({
        '个人实际销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }).reset_index()

    # 审计标记逻辑
    def get_labels(row):
        m = []
        v, c, r, p = row['个人实际销量'], row['投注单数'], row['RTP'], row['个人游戏盈亏']
        if 1000 <= v <= 2000 and c < 12: m.append("疑似刷人数")
        if v > 500000 and 0.995 <= r <= 1: m.append("疑似刷量")
        if p > 100000: m.append("盈利大会员")
        if v > 2000 and c < 10: m.append("疑似对刷")
        return " | ".join(m) if m else None

    grouped['异常标记'] = grouped.apply(get_labels, axis=1)
    return grouped[grouped['异常标记'].notna()]

# 4. 界面与暴力读取
st.title("📊 异常用户自动筛查系统")
uploaded_file = st.file_uploader("请上传 Excel (.xlsx 或 .xls)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.read()
        data = None
        
        # --- 暴力尝试开始 ---
        # 尝试 1: 现代模式
        try:
            data = pd.read_excel(io.BytesIO(file_bytes))
        except:
            # 尝试 2: 经典模式 (xlrd)
            try:
                data = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
            except:
                # 尝试 3: 网页伪装模式 (html5lib)
                try:
                    tables = pd.read_html(io.BytesIO(file_bytes), flavor='html5lib')
                    data = tables[0]
                except:
                    # 尝试 4: 编码探测模式 (处理乱码 CSV 伪装成 XLS)
                    try:
                        data = pd.read_csv(io.BytesIO(file_bytes), encoding='gbk')
                    except:
                        try:
                            data = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8-sig')
                        except:
                            st.error("❌ 无法识别。此文件可能存在加密或非标准编码。")

        if data is not None:
            # 如果第一行是干扰项，尝试自动下移
            if '用户名' not in data.columns and data.shape[0] > 1:
                # 假设第一行是无效标题，尝试将第二行设为表头
                new_header = data.iloc[0]
                data = data[1:]
                data.columns = new_header
            
            res = run_audit(data)
            if not res.empty:
                st.warning(f"✅
