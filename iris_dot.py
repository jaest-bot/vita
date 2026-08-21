import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="自訂 X/Y 軸與點大小互動分析", layout="wide")
st.title("資料分析神器：快取、Plotly 與動態尺寸調整")

# 1. 效能優化：快取讀取資料的函數，避免每次使用者點擊都重新下載/讀取
@st.cache_data
def load_data():
    # 模擬讀取遠端大型檔案
    return pd.read_csv("iris.csv")

data = load_data()

# 2. 檔案上傳元件 (可以讓學生上傳自己的 CSV)
st.subheader("自訂資料上傳")
uploaded_file = st.file_uploader("上傳你的 CSV 檔案 (可選)", type=["csv"])

if uploaded_file is not None:
    # 如果有上傳檔案，就用上傳的檔案覆蓋預設資料
    data = pd.read_csv(uploaded_file)
    st.success("檔案讀取成功！")

# 3. 嵌入 Plotly 互動圖
st.subheader("Plotly 互動圖表展示")

# 取得資料表的所有欄位
columns = list(data.columns)
# 篩選出數值型欄位，供點選「點大小依據」使用
numerical_columns = list(data.select_dtypes(include=['number']).columns)

if len(columns) >= 2:
    # 建立四欄位排版，將下拉選單水平排列
    control_col1, control_col2, control_col3, control_col4 = st.columns(4)

    with control_col1:
        # 預設 X 軸為 sepal_length（如果存在於欄位中）
        default_x_idx = columns.index('sepal_length') if 'sepal_length' in columns else 0
        x_axis = st.selectbox("選擇 X 軸數據", options=columns, index=default_x_idx)

    with control_col2:
        # 預設 Y 軸為 petal_length（如果存在於欄位中）
        default_y_idx = columns.index('petal_length') if 'petal_length' in columns else min(1, len(columns)-1)
        y_axis = st.selectbox("選擇 Y 軸數據", options=columns, index=default_y_idx)

    with control_col3:
        # 預設色彩分類為 species（如果存在於欄位中）
        color_options = ["無"] + columns
        default_color_idx = color_options.index('species') if 'species' in color_options else 0
        color_axis = st.selectbox("選擇色彩分類", options=color_options, index=default_color_idx)
        color_col = color_axis if color_axis != "無" else None

    with control_col4:
        # 點大小可選擇「固定大小」或依據「數值欄位」動態縮放
        size_options = ["固定大小"] + numerical_columns
        # 預設將 petal_width 設為點大小依據（如果存在於欄位中）
        default_size_idx = size_options.index('petal_width') if 'petal_width' in size_options else 0
        size_axis = st.selectbox("選擇點大小依據（數值欄位）", options=size_options, index=default_size_idx)

    # 根據使用者的選擇，動態調整滑桿的標題與點大小的設定
    if size_axis != "固定大小":
        point_size = st.slider("調整點的最大尺寸 (Max Size)", min_value=5, max_value=20, value=15)
        size_col = size_axis
        size_max_val = point_size
    else:
        point_size = st.slider("調整點的固定尺寸 (Marker Size)", min_value=1, max_value=30, value=10)
        size_col = None
        size_max_val = None

    # 繪製 Plotly 散佈圖
    fig = px.scatter(
        data,
        x=x_axis,
        y=y_axis,
        color=color_col,
        size=size_col,
        size_max=size_max_val,
        title=f"自訂動態散佈圖：{x_axis} 與 {y_axis} 的關聯性分析",
        labels={x_axis: x_axis, y_axis: y_axis}
    )
    
    # 如果使用者選擇的是固定大小，手動強制更新圖表的 marker size
    if size_col is None:
        fig.update_traces(marker=dict(size=point_size))
        
    # 使用 st.plotly_chart 將 Plotly 圖像渲染到網頁上
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("資料欄位不足，無法繪製雙軸散佈圖。請確保資料表至少含有 2 個欄位。")

# 顯示資料預覽
st.write("資料預覽（前 5 筆）：")
st.dataframe(data.head(), use_container_width=True)
