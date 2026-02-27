"""
FASE 2 Integration Examples - How to use MTF scoring in trading workflows

This file demonstrates three integration patterns:
1. Screener Mode: Scan multiple symbols for high-score signals
2. Single Symbol: Detailed analysis for trading execution
3. Agent Integration: Use MTF data in agent decision-making
"""

import pandas as pd
from datetime import datetime
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.structure_detector import SwingClassifier
from tradingagents.dataflows.scoring_engine import ScoringEngine, TradeDirection


# ==============================================================================
# PATTERN 1: SCREENER MODE - Scan watchlist for high-probability setups
# ==============================================================================

def screener_example():
    """
    Daily screener: Find best LONG and SHORT opportunities
    
    Cost: ~12 symbols × 2 calls = 24 calls (fits in 25 call/day budget)
    Output: Ranked list of high-confidence setups
    """
    
    print("\n" + "="*80)
    print("📊 SCREENER MODE - Multi-TimeFrame Confluence Scan")
    print("="*80)
    
    # Initialize
    mtf_layer = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    # Watchlist
    watchlist = [
        "SPY", "QQQ", "IWM",        # Broad market indices
        "AAPL", "MSFT", "GOOGL",    # Large cap tech
        "TSLA", "AMZN", "NVDA",     # Growth stocks
        "BA", "JPM", "XOM",         # Value stocks
    ]
    
    print(f"\nScanning {len(watchlist)} symbols...")
    print(f"Estimated API calls: {len(watchlist) * 2} (within 25 call/day budget)\n")
    
    all_scores = []
    
    # Scan each symbol
    for symbol in watchlist:
        try:
            print(f"  Analyzing {symbol}...", end=" ", flush=True)
            
            # Fetch multi-timeframe data
            mtf = mtf_layer.fetch_symbol_mtf(symbol)
            
            # Score both directions
            long_score, short_score = scorer.score_mtf_signal(mtf)
            
            all_scores.extend([long_score, short_score])
            
            print(f"✓ LONG:{long_score.total_score:.0f}/100 | SHORT:{short_score.total_score:.0f}/100")
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            continue
    
    # Rank by score
    print("\n" + "-"*80)
    print("🥇 TOP LONG SIGNALS (Score > 70)")
    print("-"*80)
    
    long_signals = [s for s in all_scores if s.direction == TradeDirection.LONG]
    long_ranked = scorer.rank_signals(long_signals)
    
    high_quality_longs = [s for s in long_ranked if s.total_score >= 70]
    
    if high_quality_longs:
        for i, signal in enumerate(high_quality_longs[:5], 1):
            print(f"\n{i}. {signal.symbol:6} LONG - Score: {signal.total_score:.0f}/100")
            print(f"   Components: Trend:{signal.trend_strength:.0f} | Conf:{signal.direction_confluence:.0f} | Vol:{signal.volume_quality:.0f}")
            print(f"   ADX: {signal.adx_value:.0f} | VR: {signal.volume_ratio:.2f} | ATR%: {signal.atr_pct:.2f}%")
            
            if signal.strengths:
                print(f"   Strengths:")
                for s in signal.strengths[:3]:
                    print(f"     ✓ {s}")
            
            if signal.weaknesses:
                print(f"   Weaknesses:")
                for w in signal.weaknesses[:2]:
                    print(f"     ⚠️ {w}")
    else:
        print("   (No high-quality LONG signals at this time)")
    
    # Short signals
    print("\n" + "-"*80)
    print("🥇 TOP SHORT SIGNALS (Score > 70)")
    print("-"*80)
    
    short_signals = [s for s in all_scores if s.direction == TradeDirection.SHORT]
    short_ranked = scorer.rank_signals(short_signals)
    
    high_quality_shorts = [s for s in short_ranked if s.total_score >= 70]
    
    if high_quality_shorts:
        for i, signal in enumerate(high_quality_shorts[:5], 1):
            print(f"\n{i}. {signal.symbol:6} SHORT - Score: {signal.total_score:.0f}/100")
            print(f"   Components: Trend:{signal.trend_strength:.0f} | Conf:{signal.direction_confluence:.0f} | Vol:{signal.volume_quality:.0f}")
            print(f"   ADX: {signal.adx_value:.0f} | VR: {signal.volume_ratio:.2f} | ATR%: {signal.atr_pct:.2f}%")
            
            if signal.strengths:
                print(f"   Strengths:")
                for s in signal.strengths[:3]:
                    print(f"     ✓ {s}")
    else:
        print("   (No high-quality SHORT signals at this time)")
    
    # Summary statistics
    print("\n" + "-"*80)
    print("📈 SCAN SUMMARY")
    print("-"*80)
    
    avg_long = sum(s.total_score for s in long_signals) / len(long_signals) if long_signals else 0
    avg_short = sum(s.total_score for s in short_signals) / len(short_signals) if short_signals else 0
    
    print(f"Total signals analyzed: {len(all_scores)}")
    print(f"Average LONG score: {avg_long:.0f}/100 ({len(high_quality_longs)} high-quality)")
    print(f"Average SHORT score: {avg_short:.0f}/100 ({len(high_quality_shorts)} high-quality)")
    print(f"Scan timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'long_signals': high_quality_longs,
        'short_signals': high_quality_shorts,
        'all_scores': all_scores,
    }


# ==============================================================================
# PATTERN 2: SINGLE SYMBOL - Detailed analysis for trading decision
# ==============================================================================

def single_symbol_example(symbol: str = "AAPL"):
    """
    Detailed analysis for single symbol before trade execution
    
    Includes:
    - Multi-timeframe confluence
    - Structure analysis (pivots, ChoCH, BOS)
    - Risk management levels
    - Position sizing recommendations
    """
    
    print("\n" + "="*80)
    print(f"🎯 DETAILED ANALYSIS: {symbol}")
    print("="*80)
    
    # Initialize
    mtf_layer = MultiTimeframeLayer()
    scorer = ScoringEngine()
    classifier = SwingClassifier()
    
    # Fetch data
    print(f"\nFetching {symbol} multi-timeframe data...")
    mtf = mtf_layer.fetch_symbol_mtf(symbol)
    
    # Score
    long_score, short_score = scorer.score_mtf_signal(mtf)
    
    # Structure
    structure = classifier.classify_structure(mtf.daily.ohlcv)
    levels = classifier.get_key_levels(mtf.daily.ohlcv, n_levels=3)
    choch, choch_reason = classifier.detect_choch(mtf.daily.ohlcv)
    bos, bos_reason = classifier.detect_bos(mtf.daily.ohlcv)
    
    # Current prices
    current_close = mtf.daily.latest('close')
    current_high = mtf.daily.latest('high')
    current_low = mtf.daily.latest('low')
    
    # ========== LONG ANALYSIS ==========
    print("\n" + "-"*80)
    print("🟢 LONG SETUP ANALYSIS")
    print("-"*80)
    
    print(f"\nSignal Score: {long_score.total_score:.0f}/100")
    print(f"Assessment: ", end="")
    
    if long_score.total_score >= 75:
        print("✓ STRONG - High confidence long setup")
    elif long_score.total_score >= 50:
        print("→ MODERATE - Wait for confirmation")
    else:
        print("✗ WEAK - Skip or limited position")
    
    print(f"\nScore Breakdown:")
    print(f"  • Trend Strength:         {long_score.trend_strength:.0f}/100  (ADX: {long_score.adx_value:.0f})")
    print(f"  • Direction Confluence:   {long_score.direction_confluence:.0f}/100  (Weekly trend: {'UP' if long_score.weekly_trend > 0 else 'DOWN'})")
    print(f"  • Volume Quality:         {long_score.volume_quality:.0f}/100  (VR: {long_score.volume_ratio:.2f})")
    print(f"  • Structure Quality:      {long_score.structure_quality:.0f}/100  (Formation: {structure.formation})")
    print(f"  • Risk Profile:           {long_score.risk_profile:.0f}/100  (ATR%: {long_score.atr_pct:.2f}%)")
    
    print(f"\nStructure Analysis:")
    print(f"  • Formation: {structure.formation}")
    print(f"  • Direction: {'🔺 Bullish' if structure.direction > 0 else '🔻 Bearish' if structure.direction < 0 else '➡️ Choppy'}")
    print(f"  • Context: {structure.context}")
    print(f"  • ChoCH: {'✓ YES - Reversal confirmed' if choch else '✗ NO'}")
    print(f"  • BOS: {'✓ YES - Structure break' if bos else '✗ NO'}")
    
    # Price action setup
    if long_score.total_score >= 50:
        print(f"\nPrice Action Setup:")
        print(f"  • Current Price: {current_close:.2f}")
        print(f"  • Resistance Levels: {[f'{r:.2f}' for r in levels['resistances'][:2]]}")
        print(f"  • Support Levels: {[f'{s:.2f}' for s in levels['supports'][:2]]}")
        
        # Calculate risk/reward
        entry = current_close
        stop = min(levels['supports'])
        target = current_high if current_high > current_close else max(levels['resistances'])
        
        risk = abs(entry - stop)
        reward = abs(target - entry)
        ratio = reward / risk if risk > 0 else 0
        
        print(f"\nRisk Management:")
        print(f"  • Entry: {entry:.2f}")
        print(f"  • Stop Loss: {stop:.2f} (Risk: {risk:.2f})")
        print(f"  • Target 1: {target:.2f}")
        print(f"  • Risk/Reward Ratio: 1:{ratio:.2f}")
        
        # Position sizing
        account_size = 100000  # Example account
        risk_pct_per_trade = 2  # Risk 2% per trade
        
        risk_dollars = account_size * (risk_pct_per_trade / 100)
        shares = int(risk_dollars / risk) if risk > 0 else 0
        position_value = shares * entry
        position_pct = (position_value / account_size) * 100
        
        print(f"\nPosition Sizing (${account_size:,.0f} account, 2% risk):")
        print(f"  • Risk Amount: ${risk_dollars:.0f}")
        print(f"  • Shares: {shares}")
        print(f"  • Position Value: ${position_value:,.0f} ({position_pct:.1f}% of account)")
    
    # Strengths and weaknesses
    if long_score.strengths:
        print(f"\nStrengths:")
        for s in long_score.strengths:
            print(f"  ✓ {s}")
    
    if long_score.weaknesses:
        print(f"\nWeaknesses:")
        for w in long_score.weaknesses:
            print(f"  ⚠️ {w}")
    
    # ========== SHORT ANALYSIS ==========
    print("\n" + "-"*80)
    print("🔴 SHORT SETUP ANALYSIS")
    print("-"*80)
    
    print(f"\nSignal Score: {short_score.total_score:.0f}/100")
    print(f"Assessment: ", end="")
    
    if short_score.total_score >= 75:
        print("✓ STRONG - High confidence short setup")
    elif short_score.total_score >= 50:
        print("→ MODERATE - Wait for confirmation")
    else:
        print("✗ WEAK - Skip or limited position")
    
    print(f"\nScore Breakdown:")
    print(f"  • Trend Strength:         {short_score.trend_strength:.0f}/100")
    print(f"  • Direction Confluence:   {short_score.direction_confluence:.0f}/100")
    print(f"  • Volume Quality:         {short_score.volume_quality:.0f}/100")
    print(f"  • Structure Quality:      {short_score.structure_quality:.0f}/100")
    print(f"  • Risk Profile:           {short_score.risk_profile:.0f}/100")
    
    # Recommendation
    print("\n" + "="*80)
    print("💡 RECOMMENDATION")
    print("="*80)
    
    if long_score.total_score > short_score.total_score:
        direction = "LONG"
        score = long_score.total_score
    else:
        direction = "SHORT"
        score = short_score.total_score
    
    if score >= 75:
        action = f"✓ TRADE {direction} - High confidence setup"
    elif score >= 50:
        action = f"→ MONITOR {direction} - Wait for daily confirmation"
    else:
        action = f"✗ SKIP - Insufficient confluence"
    
    print(f"\n{action}")
    print(f"Score: {score:.0f}/100")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'symbol': symbol,
        'long_score': long_score,
        'short_score': short_score,
        'structure': structure,
        'levels': levels,
    }


# ==============================================================================
# PATTERN 3: AGENT INTEGRATION - Use MTF in agent decision-making
# ==============================================================================

def agent_integration_example():
    """
    Show how to integrate MTF scoring into agent workflows
    
    Example: Market Analyst Agent using MTF data for smarter decisions
    """
    
    print("\n" + "="*80)
    print("🤖 AGENT INTEGRATION - Using MTF Data in Agent Workflows")
    print("="*80)
    
    from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
    from tradingagents.dataflows.scoring_engine import ScoringEngine
    
    symbol = "SPY"
    
    # Initialize layers
    mtf_layer = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    # Fetch data
    mtf = mtf_layer.fetch_symbol_mtf(symbol)
    long_score, short_score = scorer.score_mtf_signal(mtf)
    
    # Create agent state with MTF data
    agent_state = {
        'symbol': symbol,
        'analysis_type': 'multi_timeframe_analysis',
        'timestamp': datetime.now(),
        
        # MTF Data (what the agent can use)
        'mtf_data': {
            'daily': {
                'close': mtf.daily.latest('close'),
                'adx': mtf.daily.latest('adx'),
                'er': mtf.daily.latest('er'),
                'volume_ratio': mtf.daily.latest('volume_ratio'),
                'atr_pct': mtf.daily.latest('atr_pct'),
                'pct_from_200sma': mtf.daily.latest('pct_from_200sma'),
            },
            'weekly': {
                'close': mtf.weekly.latest('close'),
                'close_200_sma': mtf.weekly.latest('close_200_sma'),
                'supertrend': mtf.weekly.latest('supertrend_direction'),
                'adx': mtf.weekly.latest('adx'),
            },
        },
        
        # Signal Scores (numerical confidence)
        'signals': {
            'long': {
                'score': long_score.total_score,
                'trend': long_score.trend_strength,
                'confluence': long_score.direction_confluence,
                'volume': long_score.volume_quality,
            },
            'short': {
                'score': short_score.total_score,
                'trend': short_score.trend_strength,
                'confluence': short_score.direction_confluence,
                'volume': short_score.volume_quality,
            },
        },
        
        # Context for LLM
        'market_context': {
            'primary_direction': 'LONG' if long_score.total_score > short_score.total_score else 'SHORT',
            'trend_strength': 'strong' if long_score.adx_value > 35 else 'moderate' if long_score.adx_value > 25 else 'weak',
            'confidence_level': 'high' if max(long_score.total_score, short_score.total_score) >= 75 else 'moderate' if max(long_score.total_score, short_score.total_score) >= 50 else 'low',
        }
    }
    
    print(f"\n📋 Agent State Created for {symbol}:\n")
    
    print("Daily Data:")
    print(f"  Close: {agent_state['mtf_data']['daily']['close']:.2f}")
    print(f"  ADX: {agent_state['mtf_data']['daily']['adx']:.1f}")
    print(f"  Volume Ratio: {agent_state['mtf_data']['daily']['volume_ratio']:.2f}")
    
    print("\nWeekly Data:")
    print(f"  Close: {agent_state['mtf_data']['weekly']['close']:.2f}")
    print(f"  200 SMA: {agent_state['mtf_data']['weekly']['close_200_sma']:.2f}")
    print(f"  SuperTrend: {'UP' if agent_state['mtf_data']['weekly']['supertrend'] > 0 else 'DOWN'}")
    
    print("\nSignal Scores:")
    print(f"  LONG: {agent_state['signals']['long']['score']:.0f}/100")
    print(f"  SHORT: {agent_state['signals']['short']['score']:.0f}/100")
    
    print("\nMarket Context (for LLM):")
    print(f"  Primary Direction: {agent_state['market_context']['primary_direction']}")
    print(f"  Trend Strength: {agent_state['market_context']['trend_strength']}")
    print(f"  Confidence: {agent_state['market_context']['confidence_level']}")
    
    print("\n✓ Agent can now use this data for:")
    print("  • Smarter prompt generation (avoid weak setups)")
    print("  • Risk management (size based on confidence)")
    print("  • Signal validation (combine with fundamentals)")
    print("  • Alert generation (only high-confidence signals)")
    
    return agent_state


# ==============================================================================
# MAIN - Run all examples
# ==============================================================================

def main():
    """Run all integration examples"""
    
    print("\n" + "═"*80)
    print("FASE 2 INTEGRATION EXAMPLES - Multi-TimeFrame Scoring Workflows")
    print("═"*80)
    
    # Example 1: Screener
    try:
        screener_results = screener_example()
    except Exception as e:
        print(f"\n⚠️ Screener example error: {e}")
        screener_results = None
    
    # Example 2: Single Symbol
    try:
        single_results = single_symbol_example("AAPL")
    except Exception as e:
        print(f"\n⚠️ Single symbol example error: {e}")
        single_results = None
    
    # Example 3: Agent Integration
    try:
        agent_state = agent_integration_example()
    except Exception as e:
        print(f"\n⚠️ Agent integration example error: {e}")
        agent_state = None
    
    print("\n" + "═"*80)
    print("✅ ALL EXAMPLES COMPLETED")
    print("═"*80)
    print("\nNext steps:")
    print("  1. Copy patterns from examples into your trading workflow")
    print("  2. Adjust thresholds based on your risk tolerance")
    print("  3. Test with backtesting framework (FASE 3)")
    print("  4. Deploy to live trading with paper trading first")


if __name__ == "__main__":
    main()
