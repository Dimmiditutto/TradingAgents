from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import os
from .stockstats_utils import StockstatsUtils

def get_YFin_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):

    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    # Create ticker object
    ticker = yf.Ticker(symbol.upper())

    # Fetch historical data for the specified date range
    data = ticker.history(start=start_date, end=end_date)

    # Check if data is empty
    if data.empty:
        return (
            f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        )

    # Remove timezone info from index for cleaner output
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Round numerical values to 2 decimal places for cleaner display
    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].round(2)

    # Convert DataFrame to CSV string
    csv_string = data.to_csv()

    # Add header information
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    return header + csv_string

def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:

    best_ind_params = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross setups. "
            "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
            "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
            "Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
            "Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
        # ==================== SWING TRADING INDICATORS ====================
        # Trend Strength
        "adx": (
            "ADX (Average Directional Index): Measures trend strength regardless of direction. "
            "Usage: ADX > 25 = strong trend (good for swings), ADX < 20 = weak/sideways (avoid). "
            "Tips: Essential for validating swing trade setups. Always check before entering position."
        ),
        "plus_di": (
            "+DI (Plus Directional Indicator): Measures upward directional movement. "
            "Usage: +DI > -DI suggests uptrend strength. Use with ADX to confirm bullish swing setups. "
            "Tips: Rising +DI with ADX > 25 = strong uptrend."
        ),
        "minus_di": (
            "-DI (Minus Directional Indicator): Measures downward directional movement. "
            "Usage: -DI > +DI suggests downtrend strength. Use with ADX to confirm bearish swing setups. "
            "Tips: Rising -DI with ADX > 25 = strong downtrend."
        ),
        "er": (
            "ER (Efficiency Ratio): Measures trend efficiency vs noise. "
            "Usage: ER near 1 = strong directional trend, ER near 0 = noisy/sideways market. "
            "Tips: Filter swing trades: only trade when ER > 0.5 for high-quality setups."
        ),
        # Trend Direction
        "supertrend": (
            "SuperTrend: Dynamic support/resistance based on ATR. "
            "Usage: Price above SuperTrend = uptrend, below = downtrend. Excellent for swing entries. "
            "Tips: Combines volatility and price action. Low false signals in trending markets."
        ),
        "supertrend_direction": (
            "SuperTrend Direction: Binary trend signal. "
            "Usage: +1 = uptrend, -1 = downtrend. Clear directional signal for swing positioning. "
            "Tips: Direction flip = potential trend reversal. Confirm with other indicators."
        ),
        "linear_regression": (
            "Linear Regression Line: Fitted trend line over 20 periods. "
            "Usage: Identifies mean reversion opportunities. Price far from line = potential reversion. "
            "Tips: Use slope + R² together to assess trend quality."
        ),
        "linear_regression_slope": (
            "Linear Regression Slope: Trend inclination measure. "
            "Usage: Slope > 0 = uptrend, < 0 = downtrend. Magnitude shows trend strength. "
            "Tips: Steep slope + high R² = strong consistent trend."
        ),
        "linear_regression_r2": (
            "R-Squared: Measures linearity/consistency of trend. "
            "Usage: R² near 1 = consistent linear trend, near 0 = choppy price action. "
            "Tips: Only swing trade when R² > 0.6 for reliable trends."
        ),
        # Ichimoku Cloud Components
        "ichimoku_tenkan_sen": (
            "Ichimoku Conversion Line (Tenkan-sen): 9-period high+low midpoint. "
            "Usage: Fast-moving reference for short-term momentum. "
            "Tips: Price crossing Tenkan-sen signals short-term trend change."
        ),
        "ichimoku_kijun_sen": (
            "Ichimoku Base Line (Kijun-sen): 26-period high+low midpoint. "
            "Usage: Medium-term equilibrium price. Acts as dynamic support/resistance. "
            "Tips: Strong signal when Tenkan crosses Kijun."
        ),
        "ichimoku_senkou_span_a": (
            "Ichimoku Leading Span A (Cloud boundary): Average of Tenkan and Kijun, shifted forward. "
            "Usage: Forms cloud top/bottom. Price above cloud = bullish, below = bearish. "
            "Tips: Cloud acts as dynamic support/resistance zone."
        ),
        "ichimoku_senkou_span_b": (
            "Ichimoku Leading Span B (Cloud boundary): 52-period high+low midpoint, shifted forward. "
            "Usage: Forms cloud top/bottom. Thicker cloud = stronger support/resistance. "
            "Tips: Cloud color change = major trend reversal signal."
        ),
        "ichimoku_chikou_span": (
            "Ichimoku Lagging Span (Chikou): Current close shifted back 26 periods. "
            "Usage: Confirms price momentum relative to past. Chikou above past price = bullish. "
            "Tips: Chikou crossing price confirms trend strength."
        ),
        # TSI Momentum
        "tsi": (
            "TSI (True Strength Index): Double-smoothed momentum indicator with optimized swing params (13/7). "
            "Usage: TSI > 0 indicates bullish momentum, TSI < 0 bearish. Crossover with signal line provides trade signals. "
            "Tips: (13/7) params give 2-3 bar lead vs RSI, smoother without whipsaws. Essential for swing timing."
        ),
        "tsi_signal": (
            "TSI Signal Line: Smoothed TSI for crossover analysis. "
            "Usage: When TSI crosses above signal = buy signal, crosses below = sell signal. "
            "Tips: Use with TSI for timing swing trade entries/exits."
        ),
        # Updated Linear Regression (dual periods)
        "linear_regression_20": (
            "Linear Regression Line (20 periods): Fitted trend over ~1 month. Mean reversion reference line. "
            "Usage: Distance from LR line identifies overbought/oversold extremes. "
            "Tips: Use r2_20 to qualify trend linearity (>0.6 = reliable, <0.4 = choppy)."
        ),
        "linear_regression_slope_20": (
            "Linear Regression Slope (20): First derivative of 20-period trend line. "
            "Usage: Slope > 0 = uptrend, < 0 = downtrend. Magnitude shows trend strength. "
            "Tips: Steep slope + r2 > 0.6 = strong trend for swing entries."
        ),
        "linear_regression_20_r2": (
            "R-Squared (20): Linearity metric of 20-period regression (0-1). "
            "Usage: R² > 0.6 = consistent linear trend (swing-valid). R² < 0.4 = choppy. "
            "Tips: Filter out choppy markets; only trade when R² > 0.55."
        ),
        "linear_regression_10": (
            "Linear Regression Line (10 periods): Fitted trend over ~2 weeks. More reactive than 20-period. "
            "Usage: Captures recent trend inflections faster. Use with 20-period for confluent signal. "
            "Tips: When 10-period slope flips sign, potential reversal forming."
        ),
        "linear_regression_slope_10": (
            "Linear Regression Slope (10): First derivative of 10-period trend line. "
            "Usage: Faster trend direction changes than 20-period. Early reversal detection. "
            "Tips: Divergence between slope_10 and slope_20 = inflection point (potential swing reversal)."
        ),
        "linear_regression_10_r2": (
            "R-Squared (10): Linearity of recent 10-bar trend. "
            "Usage: High r2_10 with negative slope_10 = pre-reversal compression (setup forming). "
            "Tips: Monitor r2_10 < 0.3 = choppy oscillation (avoid), r2_10 > 0.7 = clean micro-trend."
        ),
        # NEW: Volume and Breakout Indicators
        "bollinger_bandwidth": (
            "Bollinger Bandwidth: (upper-lower)/middle*100. Volatility compression metric. "
            "Usage: BW < 10 = extreme squeeze=breakout imminent. Rising BW = volatility increasing. "
            "Tips: Rising from compression = setup inflection. Monitor change rate, not absolute value."
        ),
        "volume_ratio": (
            "Volume Ratio: current_volume / SMA(volume,20). Breakout quality metric. "
            "Usage: VR > 1.5 = STRONG BOS (high follow-through). VR < 0.7 = WEAK BOS (high failure). "
            "Tips: CRITICAL for swing: BOS w/ VR>1.5 has 20-30% higher win rate. Filter breakouts by VR."
        ),
        "donchian_high": (
            "Donchian Channel High (20): MAX(high,20). Structural resistance based on actual price. "
            "Usage: Breakout above = true BOS vs false breakout. More reliable than Bollinger for swing. "
            "Tips: Breakout above Donchian + rising ADX + VR>1.5 = high-confidence swing entry."
        ),
        "donchian_low": (
            "Donchian Channel Low (20): MIN(low,20). Structural support based on actual price. "
            "Usage: Breakdown below = structural support loss. Test of Donchian Low = swing short setup. "
            "Tips: When price holds above Donchian Low after touch, reversal likely (mean reversion setup)."
        ),
        "donchian_mid": (
            "Donchian Midline: (Donchian_High + Donchian_Low)/2. Dynamic center-pivot. "
            "Usage: Acts as dynamic S/R, more responsive than 50 SMA for breakout context. "
            "Tips: Price crossing Donchian Mid from below = momentum shift confirmation."
        ),
        # NEW: Screening Metrics
        "percent_from_200sma": (
            "Percent from 200 SMA: (close-200SMA)/200SMA*100. Mean-reversion distance metric. "
            "Usage: >+20% = anti-reversion risk HIGH. <-20% = extreme accumulation potential. "
            "Tips: CRITICAL filter for swing screening. Avoid setups >|25%| (statistically low win rate)."
        ),
        "atr_percent": (
            "ATR Percent: (ATR/close)*100. Cross-asset comparable volatility (vs absolute ATR). "
            "Usage: Allows uniform position sizing: 1.5x ATR% stop, 3x ATR% target across all assets. "
            "Tips: ATR% >3% = volatile (reduce size). ATR% <1% = stable (increase size). Normalize your system."
        ),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )

    end_date = curr_date
    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    # Optimized: Get stock data once and calculate indicators for all dates
    try:
        indicator_data = _get_stock_stats_bulk(symbol, indicator, curr_date)
        
        # Generate the date range we need
        current_dt = curr_date_dt
        date_values = []
        
        while current_dt >= before:
            date_str = current_dt.strftime('%Y-%m-%d')
            
            # Look up the indicator value for this date
            if date_str in indicator_data:
                indicator_value = indicator_data[date_str]
            else:
                indicator_value = "N/A: Not a trading day (weekend or holiday)"
            
            date_values.append((date_str, indicator_value))
            current_dt = current_dt - relativedelta(days=1)
        
        # Build the result string
        ind_string = ""
        for date_str, value in date_values:
            ind_string += f"{date_str}: {value}\n"
        
    except Exception as e:
        print(f"Error getting bulk stockstats data: {e}")
        # Fallback to original implementation if bulk method fails
        ind_string = ""
        curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        while curr_date_dt >= before:
            indicator_value = get_stockstats_indicator(
                symbol, indicator, curr_date_dt.strftime("%Y-%m-%d")
            )
            ind_string += f"{curr_date_dt.strftime('%Y-%m-%d')}: {indicator_value}\n"
            curr_date_dt = curr_date_dt - relativedelta(days=1)

    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
        + ind_string
        + "\n\n"
        + best_ind_params.get(indicator, "No description available.")
    )

    return result_str


def _get_stock_stats_bulk(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to calculate"],
    curr_date: Annotated[str, "current date for reference"]
) -> dict:
    """
    Optimized bulk calculation of stock stats indicators.
    Fetches data once and calculates indicator for all available dates.
    Returns dict mapping date strings to indicator values.
    """
    from .config import get_config
    import pandas as pd
    import os
    
    config = get_config()
    online = config["data_vendors"]["technical_indicators"] != "local"
    
    # New indicators that use technical_calculations.py
    ADVANCED_INDICATORS = [
        'adx', 'plus_di', 'minus_di', 'er',
        'supertrend', 'supertrend_direction',
        'linear_regression_20', 'linear_regression_slope_20', 'linear_regression_20_r2',
        'linear_regression_10', 'linear_regression_slope_10', 'linear_regression_10_r2',
        'ichimoku_tenkan_sen', 'ichimoku_kijun_sen', 'ichimoku_senkou_span_a',
        'ichimoku_senkou_span_b', 'ichimoku_chikou_span',
        'tsi', 'tsi_signal',
        'bollinger_bandwidth', 'volume_ratio',
        'donchian_high', 'donchian_low', 'donchian_mid',
        'percent_from_200sma', 'atr_percent'
    ]
    
    # Get OHLCV data
    if not online:
        # Local data path
        try:
            data = pd.read_csv(
                os.path.join(
                    config.get("data_cache_dir", "data"),
                    f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                )
            )
        except FileNotFoundError:
            raise Exception("Yahoo Finance data not fetched yet!")
    else:
        # Online data fetching with caching
        today_date = pd.Timestamp.today()
        curr_date_dt = pd.to_datetime(curr_date)
        
        end_date = today_date
        start_date = today_date - pd.DateOffset(years=15)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
        )
        
        if os.path.exists(data_file):
            data = pd.read_csv(data_file)
            data["Date"] = pd.to_datetime(data["Date"])
        else:
            data = yf.download(
                symbol,
                start=start_date_str,
                end=end_date_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
            data = data.reset_index()
            data.to_csv(data_file, index=False)
    
    # Ensure consistent column names
    data.columns = data.columns.str.lower()
    if 'date' not in data.columns:
        data = data.reset_index()
        data.columns = data.columns.str.lower()
    
    # Use advanced calculation for new indicators
    if indicator in ADVANCED_INDICATORS:
        from .technical_calculations import get_all_indicators
        
        # Calculate all indicators at once
        indicators_dict = get_all_indicators(data, swing_mode=True)
        
        # Extract the requested indicator
        if indicator in indicators_dict:
            indicator_series = indicators_dict[indicator]
            
            # Special handling for R² which is a scalar
            if indicator == 'linear_regression_r2':
                r2_value = indicators_dict[indicator]
                result_dict = {}
                for _, row in data.iterrows():
                    date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                    result_dict[date_str] = f"{r2_value:.4f}"
                return result_dict
            
            # Create result dictionary
            result_dict = {}
            for idx, row in data.iterrows():
                date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                indicator_value = indicator_series.iloc[idx]
                
                if pd.isna(indicator_value):
                    result_dict[date_str] = "N/A"
                else:
                    result_dict[date_str] = f"{indicator_value:.4f}"
            
            return result_dict
        else:
            raise ValueError(f"Indicator {indicator} not found in calculated indicators")
    
    else:
        # Use stockstats for legacy indicators
        from stockstats import wrap
        
        df = wrap(data)
        if 'date' in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        
        # Calculate the indicator for all rows at once
        df[indicator]  # This triggers stockstats to calculate the indicator
        
        # Create a dictionary mapping date strings to indicator values
        result_dict = {}
        for _, row in df.iterrows():
            date_str = row["date"] if "date" in row else row.name
            indicator_value = row[indicator]
            
            # Handle NaN/None values
            if pd.isna(indicator_value):
                result_dict[date_str] = "N/A"
            else:
                result_dict[date_str] = str(indicator_value)
        
        return result_dict


def get_stockstats_indicator(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
) -> str:

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    curr_date = curr_date_dt.strftime("%Y-%m-%d")

    try:
        indicator_value = StockstatsUtils.get_stock_stats(
            symbol,
            indicator,
            curr_date,
        )
    except Exception as e:
        print(
            f"Error getting stockstats indicator data for indicator {indicator} on {curr_date}: {e}"
        )
        return ""

    return str(indicator_value)


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get company fundamentals overview from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info

        if not info:
            return f"No fundamentals data found for symbol '{ticker}'"

        fields = [
            ("Name", info.get("longName")),
            ("Sector", info.get("sector")),
            ("Industry", info.get("industry")),
            ("Market Cap", info.get("marketCap")),
            ("PE Ratio (TTM)", info.get("trailingPE")),
            ("Forward PE", info.get("forwardPE")),
            ("PEG Ratio", info.get("pegRatio")),
            ("Price to Book", info.get("priceToBook")),
            ("EPS (TTM)", info.get("trailingEps")),
            ("Forward EPS", info.get("forwardEps")),
            ("Dividend Yield", info.get("dividendYield")),
            ("Beta", info.get("beta")),
            ("52 Week High", info.get("fiftyTwoWeekHigh")),
            ("52 Week Low", info.get("fiftyTwoWeekLow")),
            ("50 Day Average", info.get("fiftyDayAverage")),
            ("200 Day Average", info.get("twoHundredDayAverage")),
            ("Revenue (TTM)", info.get("totalRevenue")),
            ("Gross Profit", info.get("grossProfits")),
            ("EBITDA", info.get("ebitda")),
            ("Net Income", info.get("netIncomeToCommon")),
            ("Profit Margin", info.get("profitMargins")),
            ("Operating Margin", info.get("operatingMargins")),
            ("Return on Equity", info.get("returnOnEquity")),
            ("Return on Assets", info.get("returnOnAssets")),
            ("Debt to Equity", info.get("debtToEquity")),
            ("Current Ratio", info.get("currentRatio")),
            ("Book Value", info.get("bookValue")),
            ("Free Cash Flow", info.get("freeCashflow")),
        ]

        lines = []
        for label, value in fields:
            if value is not None:
                lines.append(f"{label}: {value}")

        header = f"# Company Fundamentals for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving fundamentals for {ticker}: {str(e)}"


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get balance sheet data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_balance_sheet
        else:
            data = ticker_obj.balance_sheet
            
        if data.empty:
            return f"No balance sheet data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Balance Sheet data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving balance sheet for {ticker}: {str(e)}"


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get cash flow data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_cashflow
        else:
            data = ticker_obj.cashflow
            
        if data.empty:
            return f"No cash flow data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Cash Flow data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving cash flow for {ticker}: {str(e)}"


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get income statement data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_income_stmt
        else:
            data = ticker_obj.income_stmt
            
        if data.empty:
            return f"No income statement data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Income Statement data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving income statement for {ticker}: {str(e)}"


def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol of the company"]
):
    """Get insider transactions data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        data = ticker_obj.insider_transactions
        
        if data is None or data.empty:
            return f"No insider transactions data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Insider Transactions data for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving insider transactions for {ticker}: {str(e)}"