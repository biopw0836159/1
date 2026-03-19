import streamlit as st
import pandas as pd
import io

# 1. 页面配置：严谨模式
st.set_page_config(page_title="抓鬼", layout="wide")

# 2. 登录逻辑 (保持 0224 密码)
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
    # 清理表头空格
    df.columns = [str(c).strip() for c in df.columns]
    
    # 自动兼容常见列名
    rename_dict = {
        '个人销量': '个人实际销量',
        '实际销量': '个人实际销量',
        '会员账号': '用户名',
        '账号': '用户名'
    }
    df = df.rename(columns=rename_dict)
    
    # 检查核心列
    required = ['用户名', '个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ 识别失败：表格中缺少列 {', '.join(missing)}")
        st.info("💡 建议：请确保 Excel 第一行包含以上准确的列名。")
        return pd.DataFrame(), False

    # 强制数值化，确保计算不崩溃
    for col in ['个人实际销量', '投注单数', '个人游戏盈亏', 'RTP']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 汇总计算（按用户名加总）
    grouped = df.groupby('用户名').agg({
        '个人实际销量': 'sum',
        '投注单数': 'sum',
        '个人游戏盈亏': 'sum',
        'RTP': 'mean'
    }).reset_index()

    # 标记异常逻辑
    def get_labels(row):
        m = []
        v, c, r, p = row['个人实际销量'], row['投注单数'], row['RTP'], row['个人游戏盈亏']
        # 条件 1-4
        if 1000 <= v <= 2000 and c < 12: m.append("疑似刷人数")
        if v > 500000 and 0.995 <= r <= 1: m.append("疑似刷量")
        if p > 100000: m.append("盈利大会员")
        if v > 2000 and c < 10: m.append("疑似对刷")
        return " | ".join(m) if m else None

    grouped['异常标记'] = grouped.apply(get_labels, axis=1)
    return grouped, True

# 4. 界面
st.title("📊 异常用户自动筛查系统")
st.info("💡 模式：严谨稳定版。请上传手动另存为的 .xlsx 文件。")

uploaded_file = st.file_uploader("请上传转换后的 Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # 稳定读取 xlsx
        data = pd.read_excel(uploaded_file)
        
        if data is not None:
            res_all, success = run_audit(data)
            
            if success:
                # 过滤出有问题的
                res_flagged = res_all[res_all['异常标记'].notna()]
                
                if not res_flagged.empty:
                    st.warning(f"✅ 扫描完成：发现 {len(res_flagged)} 个异常账户")
                    st.dataframe(res_flagged, use_container_width=True)
                    csv = res_flagged.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 导出审计结果 (CSV)", csv, "audit_report.csv", "text/csv")
                else:
                    st.success("✅ 扫描完毕，未发现符合异常条件的账户。")
                    with st.expander("点击查看已汇总的所有用户数据"):
                        st.dataframe(res_all)
                
    except Exception as e:
        st.error(f"解析出错：{e}")
