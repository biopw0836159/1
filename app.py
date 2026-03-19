import streamlit as st
import pandas as pd

# 严谨模式：页面配置
st.set_page_config(page_title="严谨审计系统", layout="wide")

# 1. 设置多人访问密码
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 审计系统登录")
    pwd = st.text_input("请输入访问密码", type="password")
    if st.button("进入系统"):
        if pwd == "888":  # 这里是你预设的密码
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# 2. 严谨审计核心逻辑
def run_audit(df):
    # 统一名目格式
    df.columns = df.columns.str.strip()
    
    # 定义名目与聚合规则 (条件 5: 同名自动汇总)
    agg_rules = {
        '个人销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }
    
    # 提取现有字段并执行 GroupBy
    existing_cols = [c for c in agg_rules.keys() if c in df.columns]
    if '用户名' not in df.columns:
        st.error("Excel 中缺少 '用户名' 这一列！")
        return pd.DataFrame()

    # 执行汇总计算
    grouped = df.groupby('用户名')[existing_cols].agg({k: agg_rules[k] for k in existing_cols}).reset_index()

    # 执行四项标记判定
    def get_labels(row):
        m = []
        v = row.get('个人销量', 0)
        c = row.get('投注单数', 0)
        r = row.get('RTP', 0)
        p = row.get('个人游戏盈亏', 0)
        
        if 1000 <= v <= 2000 and c < 12: m.append("疑似刷人数")
        if v > 500000 and 0.995 <= r <= 1: m.append("疑似刷量")
        if p > 100000: m.append("盈利大会员")
        if v > 2000 and c < 10: m.append("疑似对刷")
        return " | ".join(m) if m else None

    grouped['异常标记'] = grouped.apply(get_labels, axis=1)
    # 只返回有问题的用户
    return grouped[grouped['异常标记'].notna()]

# 3. 网页交互界面
st.title("📊 异常用户自动筛查系统")
st.info("说明：系统会自动将同一用户名的销量、单数、盈亏加总，并进行严谨审计。")

uploaded_file = st.file_uploader("请上传 Excel 档案 (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        data = pd.read_excel(uploaded_file)
        res = run_audit(data)
        
        if not res.empty:
            st.warning(f"分析完成：发现 {len(res)} 个异常账户")
            # 完整展示结果
            st.dataframe(res, use_container_width=True)
            # 导出功能
            csv = res.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出审计结果 (CSV)", csv, "audit_report.csv", "text/csv")
        else:
            st.success("✅ 扫描完毕，未发现异常用户。")
    except Exception as e:
        st.error(f"处理出错：{e}")
