import streamlit as st
import pandas as pd
import io

# 严谨模式：页面配置
st.set_page_config(page_title="抓鬼", layout="wide")

# 1. 登录逻辑
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 审计系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == "0224":  # 这里是你预设的密码
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# 2. 审计核心逻辑
def run_audit(df):
    df.columns = df.columns.str.strip()
    agg_rules = {
        '个人实际销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }
    
    if '用户名' not in df.columns:
        st.error("❌ 无法分析：Excel 中缺少 '用户名' 列！")
        return pd.DataFrame()

    existing_cols = [c for c in agg_rules.keys() if c in df.columns]
    for col in existing_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    grouped = df.groupby('用户名')[existing_cols].agg({k: agg_rules[k] for k in existing_cols}).reset_index()

    def get_labels(row):
        m = []
        v = row.get('个人实际销量', 0); c = row.get('投注单数', 0)
        r = row.get('RTP', 0); p = row.get('个人游戏盈亏', 0)
        # 你的四项审计条件
        if 1000 <= v <= 2000 and c < 12: m.append("疑似刷人数")
        if v > 500000 and 0.995 <= r <= 1: m.append("疑似刷量")
        if p > 100000: m.append("盈利大会员")
        if v > 2000 and c < 10: m.append("疑似对刷")
        return " | ".join(m) if m else None

    grouped['异常标记'] = grouped.apply(get_labels, axis=1)
    return grouped[grouped['异常标记'].notna()]

# 3. 界面逻辑
st.title("📊 异常用户自动筛查系统")
uploaded_file = st.file_uploader("请上传 Excel 档案 (.xlsx 或 .xls)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        file_bytes = uploaded_file.read()
        
        # 强力兼容模式：按顺序尝试四种读取方式
        data = None
        
        # 尝试 1: 标准 Excel (xlsx/xls)
        try:
            data = pd.read_excel(io.BytesIO(file_bytes))
        except:
            # 尝试 2: 旧版 xls (xlrd)
            try:
                data = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
            except:
                # 尝试 3: 如果其实是 HTML 网页格式
                try:
                    # 使用 html5lib 解决你的报错
                    tables = pd.read_html(io.BytesIO(file_bytes), flavor='html5lib')
                    data = tables[0]
                except:
                    # 尝试 4: 最后的倔强
                    data = pd.read_csv(io.BytesIO(file_bytes))

        if data is not None:
            res = run_audit(data)
            if not res.empty:
                st.warning(f"分析完成：发现 {len(res)} 个异常账户")
                st.dataframe(res, use_container_width=True)
                csv = res.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 导出审计结果", csv, "audit_report.csv")
            else:
                st.success("✅ 扫描完毕，未发现异常用户。")
        else:
            st.error("所有读取方式均失败。")
            
    except Exception as e:
        st.error(f"解析失败。错误详情：{e}")
        st.info("💡 终极解决办法：用 Excel 打开文件，点『另存为』，选择『.xlsx』格式再上传。")
