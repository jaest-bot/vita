import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mplfinance.original_flavor as mpf
import pandas as pd
import numpy as np
import matplotlib

# --- 頁面基本設定 ---
st.set_page_config(page_title="台股六大指標分析", layout="wide")

# 設定 Matplotlib 支援中文顯示
matplotlib.rc('font', family='Microsoft JhengHei') # Windows 預設微軟正黑體
matplotlib.rc('axes', unicode_minus=False)

# --- 側邊欄：使用者互動輸入區 ---
st.sidebar.header("📊 參數設定")
stock_id = st.sidebar.text_input("股票代號 (如: 2330.TW)", value="2330.TW")

# 預設日期設定
default_start = datetime(2025, 11, 19).date()
default_end = datetime(2026, 6, 13).date()

start_date_input = st.sidebar.date_input("開始日期", value=default_start)
end_date_input = st.sidebar.date_input("結束日期", value=default_end)

# --- 這裡對應第 28 行開始 ---
st.title(f"📈 {stock_id} 技術分析儀表板")
st.write(f"資料期間：{start_date_input} 至 {end_date_input}")


if stock_id in ["114514", "114514.TW"]:
    st.balloons()  
    st.snow()     
    st.success("🎉 歡迎加入王道征途！")
    st.info("💡 果然買股票就要etf！")

# --- 資料下載與快取 ---
@st.cache_data
def load_data(ticker, start_date, end_date):
    fetch_start = start_date - timedelta(days=60)
    df = yf.download(ticker, start=fetch_start, end=end_date)
    
    if df.empty:
        return df
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# 🚨 【被漏掉的關鍵扣子】：觸發下載並建立 df_raw
with st.spinner('正在下載資料中...'):
    df_raw = load_data(stock_id, start_date_input, end_date_input)

if df_raw.empty:
    st.error("⚠️ 查無資料，請確認股票代號或日期範圍是否正確。")
else:
    df = df_raw.copy()


    with st.spinner('正在下載資料中，請稍後...'):
        df_raw = load_data(stock_id, start_date_input, end_date_input)

    if df_raw.empty:
        st.error("⚠️ 查無資料，請確認股票代號或日期範圍是否正確。")
    else:
        df = df_raw.copy()

    # --- 1. 計算 SMA ---
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()

    # --- 2. 計算布林帶 ---
    df['middle_band'] = df['SMA_20']
    df['std_dev'] = df['Close'].rolling(window=20).std()
    df['upper_band'] = df['middle_band'] + (df['std_dev'] * 2)
    df['lower_band'] = df['middle_band'] - (df['std_dev'] * 2)

    # --- 3. 計算 RSV 與 KD/J 線 ---
    n = 9
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    df['RSV'] = ((df['Close'] - low_min) / (high_max - low_min)) * 100
    df['K'] = df['RSV'].ewm(alpha=1/3, adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1/3, adjust=False).mean()
    df['J'] = 3 * df['D'] - 2 * df['K']

    # --- 4. 計算 OBV ---
    df['OBV'] = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], -df['Volume'])
    df['OBV'] = df['OBV'].cumsum()

    # --- 5. 計算 MACD ---
    fast_period = 12
    slow_period = 26
    signal_period = 9
    df['EMA12'] = df['Close'].ewm(span=fast_period, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=slow_period, adjust=False).mean()
    df['DIF'] = df['EMA12'] - df['EMA26']
    df['MACD'] = df['DIF'].ewm(span=signal_period, adjust=False).mean()
    df['MACD Histogram'] = df['DIF'] - df['MACD']

    # --- 6. 計算 RSI ---
    def calculate_yahoo_rsi(series, period):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    df['RSI5'] = calculate_yahoo_rsi(df['Close'], period=5)
    df['RSI10'] = calculate_yahoo_rsi(df['Close'], period=10)

    # --- 7. 計算乖離率 BIAS ---
    df['BIAS10'] = ((df['Close'] - df['SMA_10']) / df['SMA_10']) * 100
    df['BIAS20'] = ((df['Close'] - df['SMA_20']) / df['SMA_20']) * 100
    df['B10-B20'] = df['BIAS10'] - df['BIAS20']

    # --- 裁切實際所需日期區間 ---
    start_datetime = pd.to_datetime(start_date_input)
    df = df.loc[start_datetime:].copy()
    
    # 將日期格式化為字串作為標籤，並建立純數值的 x 軸坐標
    date_labels = df.index.map(lambda x: x.strftime('%y-%m-%d')).tolist()
    x_indices = np.arange(len(df))
    
    x_ticks_pos = list(range(0, len(df), 18))
    x_ticks_labels = [date_labels[i] for i in x_ticks_pos]

    # 塞在計算完指標、切換完日期的 df 下方 (st.pyplot 之前)
    latest_data = df.iloc[-1]  # 取得最新一天的數據
    latest_rsi = latest_data['RSI5']
    latest_close = latest_data['Close']

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="最新收盤價", value=f"${latest_close:.2f}")
    with col2:
        if latest_rsi > 70:
            st.error("RSI 超買中!!!")
        elif latest_rsi < 30:
            st.success("RSI 進入超賣了!")
        else:
            st.warning("多空交戰中，燃!")


    # --- 繪圖區塊 (稍微加高畫布高度至 16 吋) ---
    fig = plt.figure(figsize=(20, 32), layout='constrained')

    # 核心設定：讓所有子圖共享同一個 X 軸
    # K線、均線、布林通道 (ax1)
    ax1 = fig.add_subplot(8, 1, (1, 3))
    mpf.candlestick2_ochl(ax1, df['Open'], df['Close'], df['High'], df['Low'], width=0.6, colorup='r', colordown='g', alpha=1)
    ax1.plot(x_indices, df['SMA_5'], label='5日均線', alpha=0.9, color='cyan', lw=1)
    ax1.plot(x_indices, df['SMA_10'], label='10日均線', alpha=0.9, color='purple', lw=1)
    ax1.plot(x_indices, df['SMA_20'], label='20日均線', alpha=0.9, color='orange', lw=1)
    ax1.plot(x_indices, df['upper_band'], label='上軌 (Upper)', alpha=0.9, color='gray', ls=':')
    ax1.plot(x_indices, df['lower_band'], label='下軌 (Lower)', alpha=0.9, color='gray', ls=':')
    ax1.legend(loc='upper left')
    ax1.set_title(f"{stock_id} 六大技術指標綜合分析", fontsize=16, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(x_ticks_pos)
    ax1.set_xticklabels([]) # 隱藏上方子圖的 X 軸標籤

    # OBV 與 Volume (ax2)
    ax2 = fig.add_subplot(8, 1, 4)
    conditions = [df['Close'] > df['Close'].shift(1), df['Close'] < df['Close'].shift(1)]
    choices = ['r', 'g']
    colors = np.select(conditions, choices, default='gray')
    ax2.plot(x_indices, df['OBV'], color='blue', linestyle='--', label='OBV')
    ax2.legend(loc='upper left')

    ax2_1 = ax2.twinx()
    # 【Bug 修復】：將 df.index 改為 x_indices 數值序列，避免類別型態衝突
    ax2_1.bar(x_indices, height=df['Volume'], color=colors, width=0.6, alpha=0.5, label='Volume')
    ax2_1.legend(loc='upper right')
    ax2.set_xticks(x_ticks_pos)
    ax2.set_xticklabels([])

    # KDJ (ax3)
    ax3 = fig.add_subplot(8, 1, 5)
    ax3.plot(x_indices, df['K'], label='K 線', color='cyan', lw=1)
    ax3.plot(x_indices, df['D'], label='D 線', color='purple', lw=1)
    ax3.plot(x_indices, df['J'], label='J 線', linestyle='--', color='orange')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(x_ticks_pos)
    ax3.set_xticklabels([])

    # MACD (ax4)
    ax4 = fig.add_subplot(8, 1, 6)
    ax4.plot(x_indices, df['DIF'], label='DIF (快線)', color='purple')
    ax4.plot(x_indices, df['MACD'], label='MACD (慢線)', color='skyblue')
    macd_colors = np.where(df['MACD Histogram'] >= 0, 'r', 'g')
    ax4.bar(x_indices, height=df['MACD Histogram'], color=macd_colors, alpha=0.6, label='柱狀圖')
    ax4.axhline(0, color='gray', linestyle='--', linewidth=1.2)
    macd_max = max(abs(df['MACD Histogram'].max()), abs(df['MACD Histogram'].min()), abs(df['DIF'].max())) * 1.5
    ax4.set_ylim(-macd_max, macd_max)
    ax4.legend(loc='upper left')
    ax4.set_xticks(x_ticks_pos)
    ax4.set_xticklabels([])

    # RSI (ax5)
    ax5 = fig.add_subplot(8, 1, 7)
    ax5.plot(x_indices, df['RSI5'], label='RSI 5', color='cyan', lw=1)
    ax5.plot(x_indices, df['RSI10'], label='RSI 10', color='purple', lw=1)
    ax5.set_ylim(0, 100)
    ax5.axhline(70, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
    ax5.axhline(30, color='green', linestyle='--', linewidth=0.8, alpha=0.5)
    ax5.legend(loc='upper left')
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(x_ticks_pos)
    ax5.set_xticklabels([])

    # 乖離率 BIAS (ax6)
    ax6 = fig.add_subplot(8, 1, 8)
    ax6.plot(x_indices, df['BIAS10'], label='BIAS 10', color='cyan', lw=1)
    ax6.plot(x_indices, df['BIAS20'], label='BIAS 20', color='purple', lw=1)
    bias_colors = np.where(df['B10-B20'] >= 0, 'r', 'g')
    ax6.bar(x_indices, height=df['B10-B20'], color=bias_colors, alpha=0.6, label='BIAS10 - BIAS20')
    ax6.axhline(0, color='gray', linestyle='--', linewidth=1.2)
    max_bias = max(df['B10-B20'].max(), 5)
    min_bias = min(df['B10-B20'].min(), -5)
    ax6.set_ylim(min_bias * 1.2, max_bias * 1.2)
    ax6.legend(loc='upper left')
    ax6.grid(True, alpha=0.3)

        # 【畫面優化】：只在最下方的子圖填入 X 軸的日期文字標籤
    ax6.set_xticks(x_ticks_pos)
    ax6.set_xticklabels(x_ticks_labels, rotation=45)

        # 渲染至 Streamlit 網頁
    st.pyplot(fig)

    # 顯示數據表格
    st.subheader("📝 近期數據紀錄")
    # 建立一個方便閱讀的 DataFrame
    df_display = df[['Close', 'Volume', 'SMA_5', 'K', 'D', 'MACD Histogram', 'RSI5', 'BIAS10']].tail(10).copy()
    # 將索引改回原本的可讀時間戳記（降序排序）
    st.dataframe(df_display.sort_index(ascending=False))
