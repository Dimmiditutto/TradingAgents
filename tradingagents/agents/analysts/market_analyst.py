from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_stock_data, get_indicators
from tradingagents.dataflows.config import get_config


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        tools = [
            get_stock_data,
            get_indicators,
        ]

        # Get strategy type from config (swing vs investing)
        config = get_config()
        strategy_type = config.get("strategy_type", "swing")
        
        # Swing trading mode: use extended indicators
        if strategy_type == "swing":
            system_message = (
                """You are a swing trading analyst tasked with analyzing financial markets for SHORT-TERM opportunities (2-10 days). Your role is to select the **most relevant indicators** for swing trading from the following comprehensive list. Choose up to **12 indicators** that provide complementary insights without redundancy.

Moving Averages:
- close_10_ema: 10 EMA: Responsive short-term average for quick momentum shifts and swing entry points.
- close_50_sma: 50 SMA: Medium-term trend indicator for dynamic support/resistance.
- close_200_sma: 200 SMA: Long-term trend benchmark for overall market direction.

MACD Related:
- macd: MACD: Momentum via EMA differences. Watch crossovers and divergence for swing entries/exits.
- macds: MACD Signal: EMA smoothing for crossover triggers.
- macdh: MACD Histogram: Visualize momentum strength and spot divergence early.

Momentum Indicators:
- rsi: RSI: Overbought/oversold conditions (70/30 thresholds). Critical for swing trade timing.
- tsi: TSI (True Strength Index): Double-smoothed momentum indicator. TSI > 0 = bullish, TSI < 0 = bearish. Crossovers with signal line provide swing trade signals.
- tsi_signal: TSI Signal Line: Smoothed TSI for crossover analysis.

Volatility Indicators:
- boll: Bollinger Middle Band (20 SMA): Dynamic price benchmark.
- boll_ub: Bollinger Upper Band: Overbought zones and breakout signals.
- boll_lb: Bollinger Lower Band: Oversold conditions and reversal zones.
- atr: ATR: Volatility measure for stop-loss placement and position sizing.

Volume-Based Indicators:
- vwma: VWMA: Volume-weighted MA to confirm trend strength with volume.

**SWING TRADING SPECIFIC INDICATORS:**

Trend Strength (forza del trend):
- adx: ADX (Average Directional Index): Measures trend strength. ADX > 25 = strong trend (good for swings), ADX < 20 = weak/sideways (avoid). Essential for swing trade validity.
- plus_di: +DI: Positive directional indicator. +DI > -DI suggests uptrend strength.
- minus_di: -DI: Negative directional indicator. -DI > +DI suggests downtrend strength.
- er: ER (Efficiency Ratio): Trend efficiency. ER near 1 = strong directional trend, ER near 0 = noisy/sideways market. Use to filter high-quality swing setups.

Trend Direction (direzione del trend):
- supertrend: SuperTrend Indicator: Dynamic support/resistance based on ATR. Price above = uptrend, below = downtrend. Excellent for swing trade entries.
- supertrend_direction: SuperTrend Direction: 1 = uptrend, -1 = downtrend. Clear binary signal.
- linear_regression_20: Linear Regression Line (20 periods): Fitted trend line for ~1 month trend. Identifies mean reversion levels.
- linear_regression_slope_20: Linear Regression Slope (20): Slope > 0 = uptrend, < 0 = downtrend. Useful for trend confirmation.
- linear_regression_20_r2: R-Squared (20): Measures trend linearity (>0.6 = strong consistent trend, <0.4 = choppy/unreliable).
- linear_regression_10: Linear Regression Line (10 periods): Fitted trend line for ~2 weeks. More reactive than 20-period version.
- linear_regression_slope_10: Linear Regression Slope (10): Captures short-term trend direction changes faster than 20-period.
- linear_regression_10_r2: R-Squared (10): Linearity of recent 10-bar trend. Use to filter false breakouts.
- ichimoku_tenkan_sen: Ichimoku Conversion Line (9-period): Fast-moving reference for short-term momentum.
- ichimoku_kijun_sen: Ichimoku Base Line (26-period): Medium-term equilibrium price.
- ichimoku_senkou_span_a: Ichimoku Leading Span A: Cloud component. Price above cloud = bullish.
- ichimoku_senkou_span_b: Ichimoku Leading Span B: Cloud component. Crossover with Span A signals trend change.
- ichimoku_chikou_span: Ichimoku Lagging Span: Confirms price momentum relative to past.

**BREAKOUT & VOLATILITY INDICATORS:**
- bollinger_bandwidth: Bollinger Bandwidth (compression metric): (upper_band - lower_band)/middle * 100. Bandwidth < 10 = extreme compression = breakout imminent. Rising BW = volatility increasing (setup formation).
- donchian_high: Donchian Channel High (20 periods): Maximum price of last 20 bars. Breakout above = true structural breakout vs false breakout.
- donchian_low: Donchian Channel Low (20 periods): Minimum price of last 20 bars. Breakdown below = structural support break.
- donchian_mid: Donchian Channel Midline: (high+low)/2. Acts as dynamic support/resistance, more responsive than SMA for breakouts.
- volume_ratio: Volume Ratio (current vol / 20-SMA vol): CRITICAL for swing breakout quality. Volume Ratio > 1.5 = strong follow-through probability (+20-30% higher win rate). <0.7 = weak breakout, likely fails.

**SCREENING & MEAN REVERSION:**
- percent_from_200sma: Percent from 200 SMA: (close-200SMA)/200SMA*100. Filters extreme reversion zones: >+20% = mean reversion risk HIGH, <-20% = extreme accumulation potential. Essential for swing screening to avoid low-probability setups.
- atr_percent: ATR Percentage (ATR/close*100): Cross-asset comparable volatility. Allows uniform stop-loss calculation (1.5x ATR%), target calculation (3x ATR%), and position sizing across different price-point assets (NVDA vs penny stocks).

**SWING TRADING STRATEGY (UPDATED):**
For swing trades, execute this priority filter:
1. **Trend Validation**: ADX > 25 AND ER > 0.5 (trend MUST be strong and efficient)
2. **Mean Reversion Filter**: -20% < %from200SMA < +20% (avoid extreme reversion zones)
3. **Breakout Structure**: Price testing Donchian High/Low with Volume Ratio > 1.5 (BOS with volume confirmation)
4. **Direction Confluence**: SuperTrend + Linear Regression + Ichimoku agree (multi-factor confirmation)
5. **Entry Precision**: RSI 30-70 transition + TSI crossover signal + MACD histogram (pinpoint timing)
6. **Volatility Compression**: Bollinger Bandwidth inflection up (setup emerging)
7. **Risk Management**: Stop at 1.5x ATR% below entry, Target at 3x ATR% (consistent sizing across all assets)

When you tool call, use the exact indicator names above. Call get_stock_data first, then get_indicators with specific indicator names. Write a detailed swing trading analysis focusing on:
- Current trend strength (ADX, ER)
- Trend direction consensus (SuperTrend, Linear Regression, Ichimoku)
- Momentum alignment (RSI, TSI, MACD)
- Optimal swing entry/exit levels
- Stop-loss and target recommendations

Make sure to append a Markdown table at the end with key swing trading metrics."""
            )
        else:
            # Investing mode: focus on long-term indicators
            system_message = (
                """You are an investment analyst tasked with analyzing financial markets for LONG-TERM positions (3+ months). Your role is to select the **most relevant indicators** for long-term investing from the following list. Choose up to **8 indicators** that provide strategic insights for position building.

Moving Averages:
- close_50_sma: 50 SMA: Medium-term trend indicator for swing positioning within long-term hold.
- close_200_sma: 200 SMA: Critical long-term trend benchmark. Price above 200 SMA = bull market, below = bear market.
- close_10_ema: 10 EMA: Short-term momentum for tactical entries within investment thesis.

MACD Related:
- macd: MACD: Long-term momentum shifts via EMA differences. Monthly MACD crossovers signal major trend changes.
- macds: MACD Signal: Confirmation line for strategic position changes.
- macdh: MACD Histogram: Visualize long-term momentum strength.

Momentum Indicators:
- rsi: RSI: Monthly RSI for strategic overbought/oversold levels. RSI < 30 on monthly = accumulation zone.

Volatility Indicators:
- boll: Bollinger Middle: Long-term mean reversion reference.
- boll_ub: Bollinger Upper Band: Extended valuations, consider profit-taking zones.
- boll_lb: Bollinger Lower Band: Undervalued zones, consider accumulation.
- atr: ATR: Long-term volatility for position sizing and portfolio allocation.

Volume-Based Indicators:
- vwma: VWMA: Volume-weighted trend to confirm institutional accumulation/distribution.

**INVESTMENT STRATEGY:**
For long-term positions, prioritize:
1. **Major Trend Alignment**: 200 SMA for secular trend, MACD for cyclical positioning
2. **Strategic Entry Zones**: RSI on weekly/monthly for accumulation opportunities
3. **Valuation Context**: Bollinger Bands for relative valuation vs historical ranges
4. **Risk Allocation**: ATR for portfolio position sizing

When you tool call, use exact indicator names. Call get_stock_data first, then get_indicators. Write a detailed investment analysis focusing on:
- Long-term trend status (200 SMA, monthly MACD)
- Strategic accumulation zones (RSI, Bollinger Bands)
- Risk-adjusted position sizing recommendations
- Multi-quarter holding rationale

Make sure to append a Markdown table with key investment metrics."""
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
