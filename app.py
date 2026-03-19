import streamlit as st
import pandas as pd
import io

# 1. 页面配置
st.set_page_config(page_title="抓鬼", layout="wide")

# 2. 登录逻辑 (888 密码)
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 审计系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == "888":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# 3. 核心审计逻辑
def run_audit(df):
    # 清理列名
    df.columns = df.columns.astype(str).str.strip()
    
    # 自动兼容列名
    if '个人销量' in df.columns and '个人实际销量' not in df.columns:
        df = df.rename(columns={'个人销量': '个人实际销量'})
    
    required = ['用户名', '个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Excel 缺少必要列：{', '.join(missing)}")
        return pd.DataFrame()

    # 强制数值化
    for col in ['个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 汇总计算
    grouped = df.groupby('用户名').agg({
        '个人实际销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }).reset_index()

    # 标记异常
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

# 4. 界面与文件处理
st.title("📊 异常用户自动筛查系统")
uploaded_file = st.file_uploader("请上传 Excel (.xlsx 或 .xls)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.read()
        data = None
        
        # 尝试读取 1: 标准/新版
        try:
            data = pd.read_excel(io.BytesIO(file_bytes))
        except:
            # 尝试读取 2: 旧版 xls
            try:
                data = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
            except:
                # 尝试读取 3: HTML 格式
                try:
                    tables = pd.read_html(io.BytesIO(file_bytes))
                    data = tables[0]
                except:
                    st.error("无法识别此 Excel 格式。")

        if data is not None:
            res = run_audit(data)
            if not res.empty:
                st.warning(f"✅ 发现 {len(res)} 个异常账户")
                st.dataframe(res, use_container_width=True)
                # 导出功能
                csv_data = res.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 导出审计结果", csv_data, "report.csv", "text/csv")
            else:
                st.success("✅ 未发现异常用户。")
                
    except Exception as e:
        st.error(f"解析出错：{e}")
